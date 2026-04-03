# AutoSRE: Claude Action Items

Things that can be researched, built, verified, or automated.

---

## PHASE 0: Foundation (COMPLETE)

- [x] Deep competitive analysis, agent framework comparison, tech stack research
- [x] All documentation: features.md, tech-stack.md, technology.md, doanddonts.md, architecture.md
- [x] competitive-analysis.md, RESEARCH.md
- [x] All decisions confirmed (name, domain, license, entity, LLM, cloud, DB, scope)

---

## PHASE 1: MVP Scaffolding (COMPLETE)

### Project Setup (DONE)
- [x] Python project with `pyproject.toml` (hatchling)
- [x] Full project structure under `src/autosre/`
- [x] GitHub Actions CI (lint, test, type check on Python 3.12/3.13)
- [x] Docker Compose: Kafka (KRaft) + ClickHouse + OTel Collector
- [x] OTel Collector config: OTLP receiver → Kafka exporter (3 topics)
- [x] README.md with quickstart

### Detection Engine (DONE)
- [x] 6 ML models ported from Paper 5:
  - Isolation Forest (scikit-learn) — `detection/models/classical.py`
  - One-Class SVM (scikit-learn) — `detection/models/classical.py`
  - LSTM Autoencoder (PyTorch) — `detection/models/deep.py`
  - Transformer Autoencoder (PyTorch) — `detection/models/deep.py`
  - 1D-CNN Autoencoder (PyTorch) — `detection/models/deep.py`
  - LSTM VAE (PyTorch) — `detection/models/deep.py`
- [x] BaseDetector interface + ModelRegistry — `detection/models/base.py`
- [x] Cooldown-aware detection (core differentiator) — `detection/cooldown/exclusion.py`
  - CooldownManager with per-signal windows
  - Paper 5 compatible `mark_cooldown_windows_paper5()`
  - Training data filtering, mask application
- [x] Automated threshold discovery — `detection/threshold/finder.py`
  - F1-optimal, percentile, statistical, auto
- [x] Late fusion (4 strategies from Paper 5) — `detection/fusion.py`
  - max, average, weighted, majority vote
- [x] Feature ablation analyzer — `detection/ablation/analyzer.py`
  - Leave-one-group-out, AUC delta, drop recommendations
- [x] Optuna hyperparameter tuning — `detection/tuning.py`
  - All 6 models with Paper 5 search spaces
  - TPE sampler, configurable trials

### OTel Ingestion (DONE)
- [x] OTLP JSON parsers (metrics, traces, logs) — `collector/parser.py`
- [x] Feature engineering pipeline — `collector/features.py`
  - Metrics: mean/std/max per service per window
  - Traces: span_count, trace_count, latency p50/p95/p99, error_rate
  - Logs: log_count, error_count, warn_count, error_rate, rate_change
- [x] `get_feature_columns()` utility for metadata exclusion

### Alerting (DONE)
- [x] Slack webhook dispatcher (Block Kit rich messages) — `alerting/dispatcher.py`
- [x] Generic webhook dispatcher — `alerting/dispatcher.py`
- [x] AnomalyAlert dataclass with severity derivation

### CLI (DONE)
- [x] `autosre init` — generate config YAML
- [x] `autosre train` — train models from Parquet/CSV
- [x] `autosre detect` — score data and display anomaly table
- [x] `autosre models` / `autosre status` — list registered models
- [x] `autosre -v` — version

### Config (DONE)
- [x] YAML config schema with vLLM, ClickHouse, cooldown, OTel — `config/schema.py`

### Tests (DONE - 66 passing)
- [x] 16 model tests (all 6 models + registry)
- [x] 7 cooldown tests
- [x] 6 threshold tests
- [x] 18 fusion tests
- [x] 26 collector tests (parsers + feature engineering)
- [x] Alerting tests (dispatcher)

---

## PHASE 2: Streaming Pipeline (NEXT)

### ClickHouse Schema
- [ ] Create telemetry tables (metrics, traces, logs)
- [ ] Create anomaly_scores table
- [ ] Create incidents table
- [ ] Materialized views for real-time aggregations
- [ ] ClickHouse init SQL in `infrastructure/clickhouse/`

### Kafka + Flink Setup
- [ ] Create Flink job: feature engineering (tumbling windows, aggregations)
- [ ] Create Flink job: streaming anomaly detection (PySAD models)
- [ ] Create Flink job: alert correlation (cross-signal fusion, dedup)
- [ ] Port Paper 7 streaming features (lag_velocity, throughput_ratio, etc.)
- [ ] Docker Compose update: add Flink JobManager + TaskManager

### Streaming Detection
- [ ] Integrate PySAD streaming algorithms (Half-Space Trees, xStream)
- [ ] Implement micro-batch inference for PyTorch models on Flink
- [ ] Implement cooldown exclusion in streaming context

### vLLM Integration
- [ ] Docker setup for vLLM with Qwen-2.5-Coder or DeepSeek-V3
- [ ] OpenAI-compatible API wrapper (vLLM serves this natively)
- [ ] LangGraph integration via OpenAI-compatible client
- [ ] Model routing config (small for triage, large for RCA)
- [ ] GPU requirements documentation

---

## PHASE 3: Agent Layer

### LangGraph Agents (powered by vLLM)
- [ ] Design agent graph (triage → investigation → RCA → remediation → chaos validation)
- [ ] Implement triage agent (anomaly classification, severity scoring)
- [ ] Implement investigation agent (log search, metric correlation)
- [ ] Implement RCA agent (graph traversal, GNN inference)
- [ ] Implement remediation agent (runbook execution, kubectl actions)
- [ ] Human-in-the-loop gates

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
- [x] autosre.dev purchased
- [x] GitHub: https://github.com/phonotechnologies/autosre (public, Apache-2.0)
- [x] PyPI: https://pypi.org/project/autosre/0.0.1/
- [x] npm: @mateenali66/autosre@0.0.1
- [x] No existing tool has cooldown-aware detection
- [x] No patent exists for cooldown-aware anomaly detection
- [x] AIOps market: $2.67B-$30.7B (2026)
- [x] 81% of K8s users deploy OTel Collectors (CNCF survey Jan 2026)
- [x] LangGraph recommended for agent orchestration
- [x] GNNs achieve 85-93% on RCA (Paper 1)
- [x] ClickHouse used by Grafana internally (Loki/Mimir)
- [x] vLLM serves OpenAI-compatible API natively

---

## HOW TO RESUME

Next conversation: "Continue building AutoSRE, pick up from Phase 2."

Key context:
- Repo: `~/mateen/saas/AutoSRE/` (also at github.com/phonotechnologies/autosre)
- 66 tests passing, lint clean, CLI working
- Phase 1 is complete. Phase 2 (streaming pipeline) is next.
- Start with ClickHouse schema, then Flink jobs, then vLLM integration.
- Read `architecture.md` for the service boundary plan.
- Read Paper 7 CLAUDE.md at `~/mateen/phd/papers/paper7-streaming-anomaly-detection/CLAUDE.md` for streaming features to port.
