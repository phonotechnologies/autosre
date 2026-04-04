"""Tests for FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from autosre.api.app import create_app
from autosre.config.schema import AutoSREConfig


@pytest.fixture
def app():
    return create_app(AutoSREConfig())


@pytest.fixture
def client(app):
    return TestClient(app)


class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "llm_connected" in data
        assert "clickhouse_connected" in data


class TestModels:
    def test_list_models(self, client):
        resp = client.get("/models")
        assert resp.status_code == 200
        data = resp.json()
        assert "detection_models" in data
        assert "isolation_forest" in data["detection_models"]
        assert "transformer_ae" in data["detection_models"]


class TestDetect:
    def test_detect_no_clickhouse_returns_503(self, client):
        resp = client.post("/detect", json={"signal": "metrics"})
        assert resp.status_code == 503


class TestAnalyze:
    def test_analyze_no_llm_returns_503(self, client):
        resp = client.post(
            "/analyze",
            json={"service": "checkout", "signal": "metrics"},
        )
        assert resp.status_code == 503


class TestIncidents:
    def test_list_incidents_no_clickhouse_returns_503(self, client):
        resp = client.get("/incidents")
        assert resp.status_code == 503

    def test_create_incident_no_clickhouse_returns_503(self, client):
        resp = client.post(
            "/incidents",
            json={"service": "checkout", "severity": "critical"},
        )
        assert resp.status_code == 503


class TestDocs:
    def test_openapi_docs(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_redoc(self, client):
        resp = client.get("/redoc")
        assert resp.status_code == 200
