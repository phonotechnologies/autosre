# AutoSRE: Claude Action Items

Things that can be researched, built, verified, or automated.

---

## PHASE 0: Foundation (COMPLETE)

### Research
- [x] Deep competitive analysis of AIOps/SRE market
- [x] Agent framework comparison (LangGraph vs CrewAI vs AutoGen vs DeerFlow)
- [x] Tech stack research and recommendations
- [x] Domain/namespace availability check
- [x] PhD paper-to-feature mapping

### Documentation
- [x] features.md -- Feature map tied to all 7 papers
- [x] tech-stack.md -- Full stack with justifications
- [x] technology.md -- Core technology deep dive
- [x] doanddonts.md -- Strategic guardrails
- [x] competitive-analysis.md -- Market research
- [x] RESEARCH.md -- Agent framework and tooling research
- [x] todo-mateen.md -- Human action items
- [x] todo-claude.md -- This file

### Confirmed Decisions
- [x] Name: AutoSRE
- [x] Domain: autosre.dev
- [x] License: Apache-2.0 (Grafana model)
- [x] Entity: Phono Technologies Inc.
- [x] GitHub: phonotechnologies/autosre
- [x] LLM: vLLM + Qwen/DeepSeek (self-hosted, no API dependency)
- [x] Cloud: AWS (EKS)
- [x] Telemetry DB: ClickHouse (self-hosted)
- [x] MVP: Module 1 (DETECT) only
- [x] Timeline: No targets, go with flow
- [x] Conference: KubeCon NA 2026

---

## PHASE 1: MVP Scaffolding (Ready to Start on Mateen's Go)

### Project Setup
- [ ] Initialize Python project with `pyproject.toml` (uv)
- [ ] Set up project structure:
  ```
  autosre/
  ├── cli/              # CLI entry point (Typer)
  ├── collector/        # OTel Collector config generator
  ├── detection/        # Anomaly detection engine
  │   ├── models/       # IF, OCSVM, LSTM-AE, Trans-AE, CNN-AE, LSTM-VAE
  │   ├── cooldown/     # Cooldown exclusion logic
  │   ├── threshold/    # Optuna-based threshold discovery
  │   └── ablation/     # Feature ablation analysis
  ├── streaming/        # Kafka + Flink pipeline
  ├── inference/        # vLLM integration for agent LLM calls
  ├── alerting/         # Slack, webhook, PagerDuty
  └── config/           # YAML config schema
  ```
- [ ] Set up GitHub Actions CI (lint, test, type check)
- [ ] Create `Dockerfile` and `docker-compose.yml`:
  - Kafka (KRaft mode)
  - OTel Collector
  - ClickHouse
  - vLLM (with Qwen model)
- [ ] Write `README.md` with quickstart

### Port Paper 5 Detection Code
- [ ] Extract ML models from `~/mateen/phd/papers/paper5-otel-aiops/`
- [ ] Refactor into reusable detection library:
  - Isolation Forest wrapper (scikit-learn/PyOD)
  - One-Class SVM wrapper (scikit-learn/PyOD)
  - LSTM Autoencoder (PyTorch)
  - Transformer Autoencoder (PyTorch)
  - CNN Autoencoder (PyTorch)
  - LSTM VAE (PyTorch)
- [ ] Implement cooldown exclusion as a core training/inference filter
- [ ] Implement Optuna-based threshold discovery
- [ ] Write unit tests for each model

### OTel Integration
- [ ] Create OTel Collector config template (OTLP receiver, Kafka exporter)
- [ ] Build OTLP ingestion endpoint (gRPC + HTTP)
- [ ] Implement metric/trace/log parsers from OTLP to detection features
- [ ] Feature engineering pipeline (aggregations, derived features)
- [ ] ClickHouse schema for telemetry storage

### vLLM Integration
- [ ] Docker setup for vLLM with Qwen-2.5-Coder or DeepSeek-V3
- [ ] OpenAI-compatible API wrapper (vLLM serves this natively)
- [ ] LangGraph integration via OpenAI-compatible client
- [ ] Model selection config (small model for triage, larger for RCA)
- [ ] GPU requirements documentation (min: 1x A10G or RTX 4090)

### CLI
- [ ] Build CLI with Typer:
  - `autosre init` -- generate config file
  - `autosre detect --config config.yaml` -- run detection
  - `autosre train --data ./telemetry/` -- train models
  - `autosre status` -- show detection status
  - `autosre ablation --config config.yaml` -- run feature ablation
- [ ] Config file schema (YAML):
  ```yaml
  telemetry:
    endpoint: "localhost:4317"  # OTLP gRPC
    signals: [metrics, traces, logs]
  storage:
    clickhouse:
      host: "localhost"
      port: 8123
  detection:
    models: [auto]
    cooldown:
      enabled: true
      default_duration: "10m"
    threshold:
      method: optuna
      trials: 300
  llm:
    provider: vllm
    endpoint: "http://localhost:8000/v1"
    model: "Qwen/Qwen2.5-Coder-7B-Instruct"
  alerting:
    slack:
      webhook_url: "${SLACK_WEBHOOK_URL}"
  ```

---

## PHASE 2: Streaming Pipeline

### Kafka + Flink Setup
- [ ] Create Flink job: feature engineering (tumbling windows, aggregations)
- [ ] Create Flink job: streaming anomaly detection (PySAD models)
- [ ] Create Flink job: alert correlation (cross-signal fusion, dedup)
- [ ] Port Paper 7 streaming features (lag_velocity, throughput_ratio, etc.)
- [ ] ClickHouse materialized views for real-time aggregations

### Streaming Detection
- [ ] Integrate PySAD streaming algorithms (Half-Space Trees, xStream)
- [ ] Implement micro-batch inference for PyTorch models on Flink
- [ ] Implement cooldown exclusion in streaming context

---

## PHASE 3: Agent Layer

### LangGraph Agents (powered by vLLM)
- [ ] Design agent graph (triage, investigation, RCA, remediation, chaos validation)
- [ ] Implement triage agent (anomaly classification, severity scoring)
- [ ] Implement investigation agent (log search, metric correlation)
- [ ] Implement RCA agent (graph traversal, GNN inference)
- [ ] Implement remediation agent (runbook execution, kubectl actions)
- [ ] Human-in-the-loop gates
- [ ] Model routing: small model (Qwen-7B) for triage, larger (Qwen-72B or DeepSeek) for complex RCA

### MCP Integration
- [ ] Create MCP server: kubernetes (kubectl wrapper)
- [ ] Create MCP server: prometheus (PromQL queries)
- [ ] Create MCP server: clickhouse (telemetry queries)
- [ ] Create MCP server: slack (messaging, approvals)

---

## PHASE 4: Frontend Dashboard

### Next.js Dashboard
- [ ] Service topology view
- [ ] Real-time anomaly feed (WebSocket)
- [ ] Incident timeline
- [ ] Model performance metrics
- [ ] Feature ablation report

---

## VERIFIED CLAIMS

- [x] "AutoSRE" name available (no major project, no trademark)
- [x] autosre.dev purchased by Mateen
- [x] No existing tool has cooldown-aware detection
- [x] No patent exists for cooldown-aware anomaly detection
- [x] AIOps market: $2.67B-$30.7B (2026)
- [x] 81% of K8s users deploy OTel Collectors (CNCF survey Jan 2026)
- [x] LangGraph recommended for agent orchestration
- [x] GNNs achieve 85-93% on RCA (Paper 1)
- [x] ClickHouse is used by Grafana internally for telemetry (Loki/Mimir)
- [x] vLLM serves OpenAI-compatible API natively (drop-in for LangGraph)

---

## NEXT STEP

Ready to start Phase 1 on Mateen's "go."
