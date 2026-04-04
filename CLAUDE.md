# AutoSRE

Research-backed, OTel-native anomaly detection for SRE teams.

## Status
- **Phase**: 1 + 1.5 COMPLETE. Phase 2 (streaming) BLOCKED on Paper 7.
- **Tests**: 127 passing, lint clean
- **Domain**: autosre.dev
- **GitHub**: https://github.com/phonotechnologies/autosre
- **PyPI**: https://pypi.org/project/autosre/
- **License**: Apache-2.0 (Grafana model)
- **Entity**: Phono Technologies Inc.

## What's Built

```
src/autosre/
├── cli/main.py                        # 7 commands: init, train, detect, models, migrate, llm, serve
├── api/app.py                         # FastAPI: /health, /detect, /analyze, /incidents, /models
├── config/schema.py                   # YAML config (ollama/vLLM, ClickHouse, cooldown, OTel)
├── collector/
│   ├── parser.py                      # OTLP JSON parsers (metrics, traces, logs)
│   └── features.py                    # Feature engineering (mean/std/max, latency p50/p95/p99)
├── detection/
│   ├── models/{base,classical,deep}.py  # 6 ML models + registry
│   ├── cooldown/exclusion.py          # Cooldown-aware detection (CORE DIFFERENTIATOR)
│   ├── threshold/finder.py            # F1-optimal, percentile, statistical
│   ├── fusion.py                      # Late fusion: max, average, weighted, majority vote
│   ├── ablation/analyzer.py           # Feature importance via leave-one-group-out
│   └── tuning.py                      # Optuna HP tuning for all 6 models
├── storage/clickhouse.py              # ClickHouseClient (full CRUD, all 8 tables)
├── inference/client.py                # LLM client (ollama dev, vLLM prod)
├── alerting/dispatcher.py             # Slack + webhook alerts
├── streaming/                         # Placeholder (BLOCKED on Paper 7)
infrastructure/clickhouse/
├── migrations/V001-V012               # 8 tables + 3 MVs + migration tracking
└── migrate.py                         # Sequential migration runner
```

## Key Files
| File | Purpose |
|------|---------|
| `features.md` | Feature map tied to all 7 PhD papers |
| `tech-stack.md` | Full technology stack with justifications |
| `technology.md` | Core technology deep dive |
| `architecture.md` | Monolith → SOA evolution, service boundaries, ClickHouse rationale |
| `doanddonts.md` | Strategic guardrails |
| `competitive-analysis.md` | Market research |
| `RESEARCH.md` | Agent frameworks, tools, domain research |
| `todo-mateen.md` | Human action items + blocker status |
| `todo-claude.md` | Build progress + phase tracking |

## Blocker
**Paper 7** (Streaming Anomaly Detection, Kafka/Flink) is in planning phase.
Flink streaming jobs and 8 derived features depend on Paper 7 completion.
Everything else (detection, CLI, API, storage, LLM) is fully functional.

## Tech Stack
- **Detection**: PyOD + PySAD + PyTorch (6 models from Paper 5)
- **LLM**: ollama (local dev) / vLLM (production) via OpenAI-compatible API
- **Streaming**: Kafka 3.9 (KRaft) + Flink 1.19 (PyFlink) — PENDING Paper 7
- **Telemetry**: OpenTelemetry Collector (OTLP → Kafka)
- **Storage**: ClickHouse (8 tables, 3 MVs, production codecs)
- **Agent**: LangGraph (Phase 3)
- **API**: FastAPI
- **Frontend**: Next.js 16 + Tailwind + shadcn/ui (Phase 4)
- **Cloud**: AWS (EKS)

## PhD Paper Mapping
| Paper | Module | Status in AutoSRE |
|-------|--------|-------------------|
| Paper 1 | DIAGNOSE, DECIDE, RECOVER | Phase 3 (agent layer) |
| Paper 2 | OPTIMIZE | Phase 3 (cost features) |
| Paper 3 | PLATFORM | Phase 4 (dashboard) |
| Paper 4 | RECOVER | Phase 3 (chaos validation) |
| Paper 5 | DETECT | **COMPLETE** (6 models, cooldown, ablation, tuning) |
| Paper 6 | SECURE | Future |
| Paper 7 | DETECT (streaming) | **BLOCKED** (paper in planning) |

## Development
```bash
pip install -e ".[dev,alerting,storage,serve,inference]"
pytest tests/ -v -p no:asyncio      # 127 tests
ruff check src/ tests/               # lint
autosre -v                           # version
autosre models                       # list 6 detection models
autosre init                         # generate config
docker compose up -d                 # Kafka + ClickHouse + OTel Collector
docker compose --profile llm up -d   # + ollama
autosre migrate                      # apply ClickHouse schema
autosre serve                        # start FastAPI on :8080
```

## How to Resume
Say "Continue building AutoSRE" in next conversation.
- If Paper 7 is done: proceed with Flink streaming jobs
- If Paper 7 is not done: can work on integration tests, vLLM prod setup, or Phase 3 (agents)
