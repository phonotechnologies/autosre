# AutoSRE: Architecture

---

## Architecture Style: Modular Monolith → SOA

AutoSRE follows a deliberate evolution path. Start simple, split only when scale or team size demands it.

```
Phase 1 (v0.1):    Monolith CLI package        ← WE ARE HERE
Phase 2 (v0.2):    Monolith + Kafka/Flink sidecar (Docker Compose)
Phase 3 (v1.0):    SOA (3-4 services, Helm chart)
Phase 4 (if needed): Split further only if team grows to 10+ engineers
```

### Why Not Microservices

Microservices solve team coordination problems, not technical ones. With a solo founder:
- More time on service mesh and deployment pipelines than the actual product
- Every feature touches 3+ repos instead of 1
- Debugging crosses network boundaries unnecessarily
- Microservices are an org scaling pattern, not a tech pattern

### Why Not Pure Monolith Forever

The detection engine is GPU-bound (PyTorch). The streaming pipeline is CPU-bound (Flink). The agent layer needs LLM inference (vLLM). These have fundamentally different scaling profiles. SOA lets them scale independently without the overhead of full microservices.

---

## Phase 1: Monolith CLI (Current)

```
┌─────────────────────────────────────────────┐
│              autosre (Python package)         │
│                                              │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  │
│  │   CLI    │  │ Detection │  │  Config  │  │
│  │ (Typer)  │  │  Engine   │  │  (YAML)  │  │
│  └────┬─────┘  └─────┬─────┘  └──────────┘  │
│       │              │                       │
│       │         ┌────┴────┐                  │
│       │         │         │                  │
│  ┌────▼───┐ ┌───▼──┐ ┌───▼────┐             │
│  │Cooldown│ │Models│ │Threshold│             │
│  │        │ │(6 ML)│ │ Finder  │             │
│  └────────┘ └──────┘ └────────┘              │
│                                              │
│  Input: Parquet/CSV files                    │
│  Output: Anomaly scores, CLI table           │
└──────────────────────────────────────────────┘
```

**Deployment**: `pip install autosre`
**Data flow**: File in → detect → scores out
**Infrastructure**: None (runs on laptop)

### Module Boundaries (designed for future extraction)

```
src/autosre/
├── cli/           → becomes API Gateway (Phase 3)
├── detection/     → becomes Detection Service (Phase 3)
│   ├── models/    → ML model training and inference
│   ├── cooldown/  → cooldown-aware filtering
│   ├── threshold/ → automated threshold discovery
│   └── ablation/  → feature importance analysis
├── streaming/     → becomes Streaming Service (Phase 2)
├── inference/     → becomes Agent Service (Phase 3)
├── alerting/      → shared library used by all services
├── collector/     → OTel Collector config (sidecar)
└── config/        → shared config schema
```

---

## Phase 2: Monolith + Streaming Sidecar

```
┌──────────────────────────────────────────────────────────┐
│                     Docker Compose                        │
│                                                          │
│  ┌──────────────────┐    ┌────────────────────────────┐  │
│  │  autosre (Python) │    │    Streaming Sidecar       │  │
│  │                  │    │                            │  │
│  │  CLI + Detection │    │  ┌──────┐  ┌───────────┐  │  │
│  │  + Alerting      │◄───┤  │Kafka │  │   Flink   │  │  │
│  │                  │    │  │(KRaft)│──│  (PyFlink) │  │  │
│  └────────┬─────────┘    │  └──▲───┘  └───────────┘  │  │
│           │              │     │                      │  │
│           │              └─────┼──────────────────────┘  │
│           │                    │                          │
│  ┌────────▼─────────┐  ┌──────┴──────┐                   │
│  │   ClickHouse     │  │    OTel     │                   │
│  │ (telemetry store)│  │  Collector  │                   │
│  └──────────────────┘  └─────────────┘                   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**What changes from Phase 1**:
- OTel Collector ingests live OTLP (not just files)
- Kafka buffers telemetry into topics (traces, metrics, logs)
- Flink jobs run feature engineering and streaming detection
- ClickHouse stores telemetry for batch training
- The Python monolith still handles training, batch detection, CLI, and alerting

**Data flow**:
```
Services (OTel SDK)
    │
    ▼
OTel Collector (OTLP gRPC/HTTP)
    │
    ▼
Kafka topics: autosre.{traces,metrics,logs}
    │
    ├──▶ Flink: feature engineering (1-min tumbling windows)
    │        │
    │        ▼
    │    Flink: streaming anomaly detection (PySAD)
    │        │
    │        ▼
    │    Kafka topic: autosre.anomalies
    │        │
    │        ▼
    │    autosre alerting (Slack, webhook)
    │
    └──▶ ClickHouse (batch storage for training)
             │
             ▼
         autosre train (batch retraining on schedule)
```

**Deployment**: `docker compose up`

---

## Phase 3: SOA (Target Architecture)

```
                        ┌───────────────────┐
                        │   Load Balancer    │
                        └────────┬──────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      API Gateway        │
                    │   (FastAPI + WebSocket)  │
                    └──┬──────┬──────┬────────┘
                       │      │      │
          ┌────────────▼┐ ┌───▼────┐ ┌▼──────────────┐
          │  Detection  │ │ Agent  │ │   Dashboard    │
          │  Service    │ │Service │ │   (Next.js)    │
          │             │ │        │ │                │
          │ - 6 ML      │ │-Lang   │ │ - Topology     │
          │   models    │ │ Graph  │ │ - Anomaly feed │
          │ - Cooldown  │ │-vLLM   │ │ - Incidents    │
          │ - Threshold │ │-MCP    │ │ - SLOs         │
          │ - Ablation  │ │ tools  │ │ - Ablation     │
          │ - Optuna    │ │-Human  │ │   report       │
          │             │ │ in the │ │                │
          │ GPU: train  │ │ loop   │ │                │
          │ + inference │ │        │ │                │
          └──────┬──────┘ └───┬────┘ └────────────────┘
                 │            │
          ┌──────▼────────────▼──────────────────┐
          │           Kafka (Message Bus)          │
          │                                       │
          │  autosre.traces    autosre.anomalies  │
          │  autosre.metrics   autosre.actions    │
          │  autosre.logs      autosre.incidents  │
          └──┬──────────┬─────────────┬───────────┘
             │          │             │
       ┌─────▼───┐ ┌────▼────┐ ┌─────▼─────┐
       │  Flink  │ │  vLLM   │ │ ClickHouse │
       │ (3 jobs)│ │(Qwen/DS)│ │            │
       └─────────┘ └─────────┘ └────────────┘
                                      │
                               ┌──────▼──────┐
                               │    Neo4j    │
                               │  (service   │
                               │   graph)    │
                               └─────────────┘
```

### The 4 Services

| Service | Language | Scales On | Communication |
|---------|----------|-----------|---------------|
| **Detection Service** | Python (PyOD + PyTorch) | GPU (training + inference) | Kafka (in: features, out: anomalies) |
| **Streaming Service** | Flink (PyFlink) | CPU + Kafka partitions | Kafka (in: raw telemetry, out: features) |
| **Agent Service** | Python (LangGraph + vLLM) | GPU (LLM inference) | Kafka (in: anomalies, out: actions) + MCP |
| **API + Dashboard** | FastAPI + Next.js | CPU (stateless) | REST/WebSocket to clients, gRPC to services |

### Service Communication

```
                Synchronous (gRPC)
API Gateway ──────────────────────▶ Detection Service
API Gateway ──────────────────────▶ Agent Service

                Asynchronous (Kafka)
OTel Collector ──▶ Kafka ──▶ Flink ──▶ Kafka ──▶ Detection ──▶ Kafka ──▶ Agent
                                                                           │
                                                                     Kafka ▼
                                                                     Alerting
```

**When to use sync vs async**:
- **Sync (gRPC)**: User requests a score, asks for model status, triggers training
- **Async (Kafka)**: Telemetry ingestion, anomaly detection, incident creation, alert dispatch

### Data Stores

```
┌───────────────────────────────────────────────────────┐
│                    Data Layer                          │
│                                                       │
│  ┌─────────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ ClickHouse  │  │  Neo4j   │  │      Redis       │ │
│  │             │  │          │  │                  │ │
│  │ - Raw       │  │ - Service│  │ - Feature cache  │ │
│  │   telemetry │  │   graph  │  │ - Rate limiting  │ │
│  │ - Features  │  │ - Blast  │  │ - Session state  │ │
│  │ - Anomaly   │  │   radius │  │ - Model metadata │ │
│  │   scores    │  │ - RCA    │  │                  │ │
│  │ - Incidents │  │   paths  │  │                  │ │
│  └─────────────┘  └──────────┘  └──────────────────┘ │
│                                                       │
│  ┌─────────────┐                                      │
│  │     S3      │                                      │
│  │             │                                      │
│  │ - Model     │                                      │
│  │   artifacts │                                      │
│  │ - Raw       │                                      │
│  │   archive   │                                      │
│  └─────────────┘                                      │
└───────────────────────────────────────────────────────┘
```

| Store | Owns | Accessed By |
|-------|------|-------------|
| **ClickHouse** | Telemetry, features, scores, incidents | Detection, Streaming, API |
| **Neo4j** | Service graph, dependencies | Agent (RCA), API (topology view) |
| **Redis** | Caches, rate limits, session | API, Detection (feature store) |
| **S3** | Model artifacts, raw archive | Detection (model registry) |

---

## Key Architecture Decisions

### 1. Kafka as the backbone (not HTTP)

Every telemetry signal flows through Kafka. This provides:
- **Decoupling**: producers and consumers evolve independently
- **Replay**: reprocess historical data when models improve
- **Backpressure**: Kafka buffers bursts without dropping data
- **Ordering**: per-partition ordering for time-series integrity

### 2. ClickHouse over PostgreSQL for telemetry

| Aspect | ClickHouse | PostgreSQL |
|--------|-----------|------------|
| Write throughput | Millions of rows/sec | Thousands of rows/sec |
| Analytical queries | 100-1000x faster | Standard |
| Compression | 10-20x | 2-3x |
| Time-series functions | Native | Extension (TimescaleDB) |
| OLTP transactions | Not designed for | Excellent |

ClickHouse handles telemetry. If we need OLTP later (user accounts, billing), add PostgreSQL only for that.

### 3. vLLM as a sidecar, not embedded

The LLM runs as a separate process (vLLM server) exposing an OpenAI-compatible API. This means:
- Detection service does not need GPU if not training
- Agent service points at vLLM endpoint (swappable)
- Can run vLLM on a different machine with more VRAM
- Can swap models without restarting the agent service

### 4. MCP for agent-tool communication

Agents interact with infrastructure through MCP servers:
```
Agent Service
    │
    ├── MCP: kubernetes (kubectl)
    ├── MCP: prometheus (PromQL)
    ├── MCP: clickhouse (SQL)
    ├── MCP: slack (alerts)
    └── MCP: chaos-mesh (validation)
```

New tools are added by deploying new MCP servers. No agent code changes needed.

### 5. Feature engineering in Flink, not in Python

Real-time feature engineering (windowed aggregations, derived features) runs in Flink, not in the Python detection service. This means:
- Feature computation scales with Kafka partitions
- Exactly-once guarantees (Flink checkpointing)
- Detection service receives pre-computed features (lower latency)
- Batch training can read the same features from ClickHouse

---

## Deployment Topology

### Local Development

```bash
docker compose up   # Kafka + ClickHouse + OTel Collector
autosre train ...   # Run detection locally
autosre detect ...  # Score locally
```

### Production (Kubernetes)

```
┌─────────────────────────────────────────┐
│              EKS Cluster                 │
│                                         │
│  Namespace: autosre                     │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │Detection│ │  Agent  │ │   API    │  │
│  │ Deploy  │ │ Deploy  │ │ Deploy   │  │
│  │ (GPU)   │ │ (GPU)   │ │ (CPU)    │  │
│  └─────────┘ └─────────┘ └──────────┘  │
│                                         │
│  Namespace: data                        │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │  Kafka  │ │  Flink  │ │ClickHouse│  │
│  │ (KRaft) │ │ Cluster │ │ Operator │  │
│  └─────────┘ └─────────┘ └──────────┘  │
│                                         │
│  Namespace: inference                   │
│  ┌─────────┐ ┌─────────┐               │
│  │  vLLM   │ │  Neo4j  │               │
│  │ (GPU)   │ │         │               │
│  └─────────┘ └─────────┘               │
│                                         │
│  Namespace: monitoring                  │
│  ┌─────────────────────────────────┐    │
│  │ OTel Collector (DaemonSet)      │    │
│  │ AutoSRE monitors AutoSRE       │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

**GPU allocation**:
- Detection Service: 1x A10G (24GB) for training + inference
- Agent Service: shares vLLM GPU
- vLLM: 1x A10G for 7B model, or 1x A100 for 72B model

---

## Module Extraction Guide

When Phase 3 arrives, each module extracts cleanly:

| Module | Becomes | Extraction Steps |
|--------|---------|-----------------|
| `src/autosre/detection/` | Detection Service | Add FastAPI + gRPC wrapper. Own Dockerfile. Kafka consumer for features, producer for anomalies. |
| `src/autosre/streaming/` | Flink Jobs | Already separate. Package as Flink job JARs (PyFlink). |
| `src/autosre/inference/` | Agent Service | Add LangGraph graph definition. Connect to vLLM. MCP tool servers. |
| `src/autosre/cli/` | API Gateway | Replace Typer with FastAPI. Add WebSocket for real-time. |
| `src/autosre/config/` | Shared library | Published as internal package or copied into each service. |
| `src/autosre/alerting/` | Shared library | Same: used by Detection + Agent services. |

The key insight: **the Python module boundaries ARE the future service boundaries**. No refactoring needed at extraction time.

---

## Anti-Patterns We Avoid

| Anti-Pattern | What We Do Instead |
|-------------|-------------------|
| Premature microservices | Monolith first, split at service boundary lines already drawn |
| Shared database across services | Each service writes to specific ClickHouse tables; reads via materialized views |
| Synchronous chains (A calls B calls C) | Async via Kafka; sync only for user-facing requests |
| Fat gateway | API Gateway is thin: auth, routing, WebSocket. No business logic. |
| Distributed monolith | Services communicate through Kafka topics, not direct calls |
| Over-engineering for scale | Docker Compose until Docker Compose breaks, then Helm |
