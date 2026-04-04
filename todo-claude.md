# AutoSRE: Claude Action Items

---

## PHASE 0: Foundation (COMPLETE)

- [x] Deep competitive analysis, agent framework comparison, tech stack research
- [x] All documentation: features.md, tech-stack.md, technology.md, doanddonts.md, architecture.md
- [x] competitive-analysis.md, RESEARCH.md
- [x] All decisions confirmed (name, domain, license, entity, LLM, cloud, DB, scope)

---

## PHASE 1: MVP Scaffolding (COMPLETE)

- [x] Project setup: pyproject.toml, structure, GitHub Actions CI, Docker Compose, README
- [x] 6 ML models ported from Paper 5 (IF, OCSVM, LSTM-AE, Trans-AE, CNN-AE, LSTM-VAE)
- [x] Cooldown-aware detection, threshold discovery, late fusion (4 strategies)
- [x] Feature ablation analyzer, Optuna HP tuning (all 6 models)
- [x] OTel OTLP parsers + feature engineering pipeline
- [x] Alerting (Slack + webhook), config (YAML)
- [x] CLI: init, train, detect, models, status

---

## PHASE 1.5: Storage + Inference (COMPLETE)

### ClickHouse Schema (DONE)
- [x] 8 tables: spans, metrics, logs, features, anomaly_scores, incidents, cooldown_windows, model_registry
- [x] 3 materialized views: trace/metric/log features auto-computed on INSERT
- [x] Production codecs: DoubleDelta+ZSTD, Gorilla+ZSTD, T64+ZSTD, ZSTD(3)
- [x] LowCardinality, Map columns, MATERIALIZED columns, bloom_filter, tokenbf_v1
- [x] TTL policies: 14d raw, 30d logs, 90d features/scores, 365d incidents
- [x] Migration runner (sequential, version-tracked)
- [x] ClickHouseClient with full CRUD for all tables
- [x] `autosre migrate` CLI command

### LLM Inference (DONE)
- [x] OpenAI-compatible client (works with ollama and vLLM)
- [x] Built-in prompts: analyze_anomaly, summarize_incident, suggest_runbook
- [x] LLMConfig with ollama_default() and vllm_default()
- [x] `autosre llm` CLI command (check connection, list models)

### FastAPI Server (DONE)
- [x] /health, /detect, /analyze, /incidents, /models endpoints
- [x] `autosre serve` CLI command
- [x] Lifespan-managed LLM + ClickHouse clients

### Docker Compose (DONE)
- [x] Kafka (KRaft) + ClickHouse + OTel Collector + ollama (opt-in)

---

## PHASE 2: Streaming Pipeline (BLOCKED on Paper 7)

### Blocker
Paper 7 (Streaming Anomaly Detection on Kafka/Flink) is in planning phase.
The 8 streaming-specific derived features (lag_velocity, throughput_ratio, etc.)
are designed but not experimentally validated. Flink jobs depend on these features.

### What can be done WITHOUT Paper 7
- [ ] ClickHouse Kafka engine for raw telemetry ingestion (no Flink needed)
- [ ] Basic Flink job: 1-min window aggregation for microservice features (no streaming-specific features)
- [ ] End-to-end integration test: docker compose up → send OTLP → see features in ClickHouse

### What REQUIRES Paper 7 completion
- [ ] Flink streaming detection job with PySAD models
- [ ] Paper 7 streaming features (lag_velocity, lag_acceleration, throughput_ratio, checkpoint_overhead_ratio, isr_stability, rebalance_frequency, backpressure_ratio, watermark_lag)
- [ ] 30-second window aggregation for streaming workloads
- [ ] Streaming-specific fault detection (broker crash, consumer lag, checkpoint failure, etc.)

### vLLM Integration (can do independently)
- [ ] Docker setup for vLLM with Qwen-2.5-Coder on GPU (production)
- [ ] Model routing config (small for triage, large for RCA)
- [ ] GPU requirements documentation

---

## PHASE 3: Agent Layer (Future)

- [ ] LangGraph agent graph (triage → investigation → RCA → remediation → chaos validation)
- [ ] MCP servers: kubernetes, prometheus, clickhouse, slack
- [ ] Human-in-the-loop gates

---

## PHASE 4: Frontend Dashboard (Future)

- [ ] Next.js dashboard: topology, anomaly feed, incidents, ablation report

---

## PROJECT STATS (as of Apr 3, 2026)

| Metric | Value |
|--------|-------|
| Commits | 6 |
| Lines of code | ~15,000 |
| Tests | 127 passing |
| CLI commands | 7 (init, train, detect, models, migrate, llm, serve) |
| API endpoints | 5 (/health, /detect, /analyze, /incidents, /models) |
| ML models | 6 |
| ClickHouse tables | 8 + 3 MVs |
| Lint | Clean (ruff) |

## VERIFIED CLAIMS

- [x] autosre.dev purchased
- [x] GitHub: https://github.com/phonotechnologies/autosre
- [x] PyPI: https://pypi.org/project/autosre/0.0.1/
- [x] npm: @mateenali66/autosre@0.0.1
- [x] No existing tool has cooldown-aware detection
- [x] No patent exists for cooldown-aware anomaly detection
- [x] LangGraph recommended for agent orchestration
- [x] ClickHouse used by Grafana internally (Loki/Mimir)
- [x] vLLM serves OpenAI-compatible API natively
- [x] ollama serves OpenAI-compatible API natively (confirmed working)

---

## HOW TO RESUME

**Next conversation**: "Continue building AutoSRE"

**Key context**:
- Repo: `~/mateen/saas/AutoSRE/` (also github.com/phonotechnologies/autosre)
- 127 tests passing, lint clean, 7 CLI commands working
- Phase 1 + 1.5 complete. Phase 2 partially blocked on Paper 7.
- Can proceed with: non-streaming Flink jobs, integration tests, vLLM production setup
- Read `architecture.md` for service boundary plan
- Read `todo-mateen.md` for human action items
- Paper 7 status: `~/mateen/phd/papers/paper7-streaming-anomaly-detection/CLAUDE.md`
