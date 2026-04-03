# AutoSRE: Technology Stack

---

## Stack Overview

```
+-----------------------------------------------------------------+
|                         FRONTEND                                |
|  Next.js 16 + Tailwind CSS + shadcn/ui + Motion                |
+-----------------------------------------------------------------+
|                         API LAYER                               |
|  FastAPI (Python 3.12+) + WebSocket (real-time alerts)          |
+-----------------------------------------------------------------+
|                      AGENT ORCHESTRATION                        |
|  LangGraph (graph-based workflows, checkpointing)              |
|  Haystack (RAG/knowledge retrieval, runbook search)             |
+-----------------------------------------------------------------+
|                      ML / DETECTION                             |
|  PyOD (batch, 40+ algos) + PySAD (streaming, 17+ algos)        |
|  PyTorch (custom Transformer-AE, LSTM-AE from Paper 5)         |
|  Optuna (hyperparameter tuning, 1800 trials proven)             |
|  scikit-learn (feature engineering pipelines)                   |
+-----------------------------------------------------------------+
|                      STREAMING PIPELINE                         |
|  Apache Kafka 3.9 (KRaft mode, no ZooKeeper)                   |
|  Apache Flink 1.19 (PyFlink for ML model serving)              |
+-----------------------------------------------------------------+
|                      TELEMETRY INGESTION                        |
|  OpenTelemetry Collector (Agent + Gateway pattern)              |
|  OTLP (gRPC + HTTP) ingestion                                  |
+-----------------------------------------------------------------+
|                      LLM INFERENCE                              |
|  vLLM (self-hosted, OpenAI-compatible API)                      |
|  Qwen-2.5-Coder / DeepSeek-V3 (no API dependency)              |
+-----------------------------------------------------------------+
|                      DATA STORES                                |
|  ClickHouse -- telemetry storage, time-series analytics         |
|  Neo4j -- service dependency graphs, blast radius               |
|  Redis -- caching, rate limiting, feature store                 |
|  S3 -- raw telemetry archive, model artifacts                   |
+-----------------------------------------------------------------+
|                      INFRASTRUCTURE                             |
|  Kubernetes (EKS) + Terraform + GitHub Actions CI/CD            |
+-----------------------------------------------------------------+
```

---

## Detailed Stack Decisions

### 1. Agent Orchestration: LangGraph

| Attribute | Detail |
|-----------|--------|
| **Why** | Graph-based workflows map 1:1 to SRE incident flows (triage, investigate, diagnose, remediate) |
| **Key feature** | Built-in checkpointing for long-running incident investigations |
| **Alternative considered** | CrewAI (faster prototyping but no checkpointing; teams migrate to LangGraph for production) |
| **Alternative rejected** | AutoGen (conversational pattern wrong for deterministic SRE workflows) |
| **Alternative rejected** | DeerFlow (too new, not SRE-focused) |
| **License** | MIT |

### 2. Knowledge/RAG Layer: Haystack

| Attribute | Detail |
|-----------|--------|
| **Why** | Production-ready from day one (enterprise NLP heritage), serves pipelines as REST APIs or MCP servers |
| **Use case** | Runbook search, incident history retrieval, documentation lookup |
| **Integration** | Haystack feeds context to LangGraph agents via MCP |
| **License** | Apache-2.0 |

### 3. Anomaly Detection: PyOD + PySAD + PyTorch

| Library | Use Case | Rationale |
|---------|----------|-----------|
| **PyOD** | Batch anomaly detection | 40+ algorithms, LLM-powered model selection in v2, industry standard |
| **PySAD** | Streaming anomaly detection | 17+ streaming algorithms, compatible with PyOD/sklearn APIs |
| **PyTorch** | Custom deep learning models | Paper 5 Transformer-AE (AUC=0.800), LSTM-AE, CNN-AE, LSTM-VAE |
| **Optuna** | Hyperparameter tuning | 1,800 trials proven in Paper 5, Bayesian optimization |
| **scikit-learn** | Feature engineering | Pipelines, preprocessing, Isolation Forest, One-Class SVM |

### 4. Streaming: Kafka + Flink

| Attribute | Detail |
|-----------|--------|
| **Kafka** | 3.9 with KRaft mode (no ZooKeeper dependency) |
| **Flink** | 1.19 with PyFlink for ML model integration |
| **Why not Kafka Streams** | Flink provides advanced windowing, checkpointing, and exactly-once guarantees needed for anomaly detection windows |
| **Why not Apache Beam** | Adds abstraction layer without benefit when Flink is the target runner |
| **Paper 7 proven** | Entire streaming anomaly detection benchmark built on this stack |

### 5. Telemetry: OpenTelemetry Collector

| Pattern | Description |
|---------|-------------|
| **Agent mode** | Runs on each node, collects local traces/metrics/logs via OTLP |
| **Gateway mode** | Central aggregation, batching, tail sampling, attribute enrichment |
| **Export target** | Gateway exports to Kafka topics for streaming pipeline |
| **Key config** | Batch exporter + gzip compression, pre-aggregate metrics to reduce cardinality |

### 6. Service Dependency Graph: Neo4j

| Attribute | Detail |
|-----------|--------|
| **Why** | Richest graph ecosystem, Cypher query language, Graph Data Science library |
| **Use case** | Service topology, blast radius prediction (PageRank), failure domain detection (community detection) |
| **Alternative** | Amazon Neptune (only if going AWS-exclusive) |
| **Deployment** | Self-hosted on K8s or AuraDB managed |

### 7. Frontend: Next.js 16 + Tailwind + shadcn/ui

| Attribute | Detail |
|-----------|--------|
| **Why** | Matches existing tech stack preferences, App Router, RSC for dashboard performance |
| **Real-time** | WebSocket connection for live anomaly alerts and incident updates |
| **Charts** | Recharts or Tremor for time-series visualization |
| **Design system** | shadcn/ui components, consistent with other Phono projects |

### 8. API: FastAPI

| Attribute | Detail |
|-----------|--------|
| **Why** | Python (same as ML stack), async, automatic OpenAPI docs, type hints |
| **WebSocket** | Native support for real-time alert streaming |
| **Auth** | JWT tokens, GitHub OAuth (consistent with other SaaS projects) |

### 9. Data Stores

| Store | Purpose | Rationale |
|-------|---------|-----------|
| **ClickHouse** | Telemetry storage (traces, metrics, logs), time-series analytics | Columnar, blazing-fast aggregations, used by Grafana (Loki/Mimir), Cloudflare, Uber. Self-hosted on K8s. |
| **Neo4j** | Service dependency graphs | Graph queries for RCA and blast radius |
| **Redis** | Caching, rate limiting, real-time feature store | Low-latency access for streaming pipeline |
| **S3** | Raw telemetry archive, trained model artifacts | Cost-effective bulk storage |

**Why ClickHouse over PostgreSQL for telemetry:**
- 100-1000x faster on analytical queries over time-series data
- Native support for time-series functions (moving averages, quantiles)
- Compression: 10-20x smaller storage than PostgreSQL for same data
- MergeTree engine designed for append-heavy telemetry workloads
- Materialized views for real-time pre-aggregation
- Self-hosted on K8s via ClickHouse Operator (no managed service cost)

### 10. Infrastructure & CI/CD

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Container orchestration** | Kubernetes (EKS) | Production standard, Paper 5 testbed already on EKS |
| **IaC** | Terraform | Paper 6 research, existing expertise |
| **CI/CD** | GitHub Actions | Existing CICosts integration, familiar |
| **Container registry** | ECR or GitHub Container Registry | AWS-native or GitHub-native |
| **Monitoring (self)** | OpenTelemetry (dogfooding) | AutoSRE monitors itself with AutoSRE |

### 11. LLM Inference: vLLM + Open Models

| Attribute | Detail |
|-----------|--------|
| **Runtime** | vLLM (self-hosted, OpenAI-compatible API) |
| **Primary models** | Qwen-2.5-Coder-7B (triage, fast tasks), DeepSeek-V3 (complex RCA, incident analysis) |
| **Why not Claude/GPT API** | No API dependency, no per-token costs, fully self-hostable, air-gap compatible |
| **Integration** | vLLM serves OpenAI-compatible `/v1/chat/completions` endpoint; LangGraph connects via standard OpenAI client |
| **GPU requirements** | Min: 1x A10G (24GB) for 7B models. Recommended: 1x A100 (80GB) for 72B models |
| **Model routing** | Small model for triage/classification, large model for RCA/incident summaries |
| **Cost** | GPU instance cost only (~$0.75/hr for A10G on AWS). No per-token API fees. |
| **Fallback** | Claude/GPT APIs supported via same OpenAI-compatible interface (user's choice) |

---

## Language Breakdown

| Language | Where | Why |
|----------|-------|-----|
| **Python 3.12+** | Backend, ML, agents, streaming (PyFlink) | ML ecosystem, LangGraph, FastAPI, PyOD |
| **TypeScript** | Frontend (Next.js) | Type safety, React ecosystem |
| **Cypher** | Neo4j queries | Graph query language |
| **SQL** | Supabase/PostgreSQL | Standard data queries |
| **HCL** | Terraform IaC | Infrastructure provisioning |

---

## Deployment Models

### Open Source (Community Edition)
- Single-node Docker Compose for evaluation
- CLI tool (`autosre`) for local anomaly detection
- Apache-2.0 license

### Managed Service (AutoSRE Cloud)
- Multi-tenant SaaS on AWS
- Hosted Kafka, Flink, ClickHouse, vLLM
- Free for now (Grafana model: monetize later via enterprise features)

### Enterprise Self-Hosted
- Helm chart for Kubernetes deployment
- Bring your own Kafka/Flink/Neo4j
- Air-gapped support
