"""FastAPI application for AutoSRE API server.

Provides REST endpoints for:
- Health check and status
- Anomaly detection (score telemetry data)
- LLM-powered anomaly analysis
- Incident management
- Model management
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from autosre import __version__
from autosre.config.schema import AutoSREConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_connected: bool
    clickhouse_connected: bool


class DetectRequest(BaseModel):
    signal: str  # "metrics", "traces", "logs"
    service: str | None = None
    model: str = "auto"
    threshold: float = 0.5


class DetectResponse(BaseModel):
    anomalies: int
    total: int
    rate: float
    scores: list[float] | None = None


class AnalyzeRequest(BaseModel):
    service: str
    signal: str
    model: str = ""
    score: float = 0.0
    threshold: float = 0.5
    timestamp: str = ""
    top_features: str = ""


class AnalyzeResponse(BaseModel):
    analysis: str
    model_used: str


class IncidentCreate(BaseModel):
    service: str
    severity: str = "info"
    signals: list[str] = []
    models: list[str] = []
    max_score: float = 0.0


class IncidentResponse(BaseModel):
    incident_id: str
    status: str


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app(config: AutoSREConfig | None = None) -> FastAPI:
    """Create the FastAPI application with configured dependencies."""
    if config is None:
        config = AutoSREConfig()

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI) -> AsyncGenerator[None, None]:
        # Startup: init LLM and ClickHouse clients
        try:
            from autosre.inference import LLMClient

            app_instance.state.llm_client = LLMClient.from_config(config.llm)
            if app_instance.state.llm_client.ping():
                logger.info("LLM connected: %s (%s)", config.llm.provider, config.llm.model)
            else:
                logger.warning("LLM not reachable at %s", config.llm.endpoint)
        except Exception as e:
            logger.warning("LLM client init failed: %s", e)
            app_instance.state.llm_client = None

        try:
            from autosre.storage import ClickHouseClient

            app_instance.state.ch_client = ClickHouseClient.from_config(config.storage)
            if app_instance.state.ch_client.ping():
                logger.info("ClickHouse connected: %s", config.storage.clickhouse_host)
            else:
                logger.warning("ClickHouse not reachable")
        except Exception as e:
            logger.warning("ClickHouse client init failed: %s", e)
            app_instance.state.ch_client = None

        yield

        # Shutdown
        if app_instance.state.llm_client:
            app_instance.state.llm_client.close()

    app = FastAPI(
        title="AutoSRE",
        description="Research-backed, OTel-native anomaly detection for SRE teams",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Store config for dependency injection
    app.state.config = config
    app.state.llm_client = None
    app.state.ch_client = None

    # ----- Routes -----

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        llm_ok = False
        ch_ok = False
        if app.state.llm_client:
            llm_ok = app.state.llm_client.ping()
        if app.state.ch_client:
            ch_ok = app.state.ch_client.ping()
        return HealthResponse(
            status="ok",
            version=__version__,
            llm_connected=llm_ok,
            clickhouse_connected=ch_ok,
        )

    @app.get("/models")
    async def list_models() -> dict[str, Any]:
        from autosre.detection.models import ModelRegistry

        return {
            "detection_models": ModelRegistry.list_models(),
            "llm_models": (app.state.llm_client.list_models() if app.state.llm_client else []),
        }

    @app.post("/detect", response_model=DetectResponse)
    async def detect(req: DetectRequest) -> DetectResponse:
        if not app.state.ch_client:
            raise HTTPException(503, "ClickHouse not connected")

        df = app.state.ch_client.read_features(
            signal=req.signal,
            service=req.service,
        )
        if df.empty:
            return DetectResponse(anomalies=0, total=0, rate=0.0)

        from autosre.collector.features import get_feature_columns
        from autosre.detection.models import ModelRegistry

        feature_cols = get_feature_columns(df)
        if not feature_cols:
            raise HTTPException(400, f"No numeric features found for signal '{req.signal}'")

        import numpy as np

        X = df[feature_cols].values.astype(np.float32)

        if req.model == "auto":
            model_names = ModelRegistry.list_models()
        else:
            model_names = [req.model]

        total_anomalies = 0
        for name in model_names[:1]:  # Use first model for now
            detector_cls = ModelRegistry.get(name)
            detector = detector_cls(n_features=len(feature_cols))  # type: ignore[call-arg]
            detector.fit(X)
            scores = detector.score(X)
            total_anomalies = int((scores >= req.threshold).sum())

        return DetectResponse(
            anomalies=total_anomalies,
            total=len(X),
            rate=total_anomalies / max(len(X), 1),
        )

    @app.post("/analyze", response_model=AnalyzeResponse)
    async def analyze_anomaly(req: AnalyzeRequest) -> AnalyzeResponse:
        if not app.state.llm_client:
            raise HTTPException(503, "LLM not connected")

        context = {
            "service": req.service,
            "signal": req.signal,
            "model": req.model,
            "score": req.score,
            "threshold": req.threshold,
            "timestamp": req.timestamp or datetime.now().isoformat(),
            "top_features": req.top_features,
        }
        analysis = app.state.llm_client.analyze_anomaly(context)
        return AnalyzeResponse(
            analysis=analysis,
            model_used=app.state.llm_client.model,
        )

    @app.post("/incidents", response_model=IncidentResponse)
    async def create_incident(req: IncidentCreate) -> IncidentResponse:
        if not app.state.ch_client:
            raise HTTPException(503, "ClickHouse not connected")

        incident_id = app.state.ch_client.create_incident(
            {
                "service": req.service,
                "severity": req.severity,
                "signals": req.signals,
                "models": req.models,
                "max_score": req.max_score,
                "status": "open",
            }
        )
        return IncidentResponse(incident_id=incident_id, status="open")

    @app.get("/incidents")
    async def list_incidents(status: str | None = None, limit: int = 50) -> dict[str, Any]:
        if not app.state.ch_client:
            raise HTTPException(503, "ClickHouse not connected")

        df = app.state.ch_client.read_incidents(status=status, limit=limit)
        return {"incidents": df.to_dict(orient="records") if not df.empty else []}

    return app
