# AutoSRE

Research-backed, OTel-native anomaly detection for SRE teams.

## Status
- **Phase**: Phase 1 (MVP scaffolding) complete. Building Phase 1.5 (ingestion, alerting, tuning).
- **Domain**: autosre.dev (purchased)
- **GitHub**: https://github.com/phonotechnologies/autosre
- **License**: Apache-2.0 (Grafana model: OSS core + managed service)
- **Entity**: Phono Technologies Inc.

## Key Files
| File | Purpose |
|------|---------|
| `features.md` | Feature map tied to all 7 PhD papers, MVP scope |
| `tech-stack.md` | Full technology stack with justifications |
| `technology.md` | Core technology deep dive |
| `doanddonts.md` | Strategic guardrails |
| `competitive-analysis.md` | Market research and competitor analysis |
| `RESEARCH.md` | Agent frameworks, tools, domain research |
| `architecture.md` | Architecture evolution: monolith → SOA, service boundaries |
| `todo-mateen.md` | Human action items (namespace claims, IP validation) |
| `todo-claude.md` | Build phases 1-4 |

## Core Differentiators vs OpenSRE / Azure SRE Agent / AWS DevOps Agent
1. **Cooldown-aware detection** (zero competitors, Paper 5)
2. **Feature ablation intelligence** (mean-only AUC=0.964, Paper 5)
3. **OTel-native multi-signal fusion** (not adapted, built on OTel)
4. **Self-hosted LLM** (vLLM + Qwen/DeepSeek, no API dependency)
5. **Streaming detection** (Kafka/Flink, Paper 7)
6. **Multi-cloud, fully OSS** (vs Azure-only / AWS-only proprietary agents)
7. **Research-backed** (7 peer-reviewed papers, published benchmarks)

## Tech Stack
- **Agent Orchestration**: LangGraph
- **LLM Inference**: vLLM + Qwen-2.5-Coder / DeepSeek-V3 (self-hosted)
- **Streaming**: Kafka 3.9 (KRaft) + Flink 1.19 (PyFlink)
- **Anomaly Detection**: PyOD + PySAD + PyTorch (6 models from Paper 5)
- **Telemetry**: OpenTelemetry Collector (Agent + Gateway)
- **Telemetry DB**: ClickHouse (self-hosted)
- **Knowledge/RAG**: Haystack
- **Graph DB**: Neo4j (service dependency, blast radius)
- **API**: FastAPI
- **Frontend**: Next.js 16 + Tailwind + shadcn/ui
- **Cloud**: AWS (EKS)
- **IaC**: Terraform

## PhD Paper Mapping
| Paper | Module | Contribution |
|-------|--------|-------------|
| Paper 1 | DIAGNOSE, DECIDE, RECOVER | Self-healing taxonomy, GNN RCA, human-in-the-loop |
| Paper 2 | OPTIMIZE | FinOps ML, cost anomaly detection |
| Paper 3 | PLATFORM | IDP taxonomy, developer scorecards |
| Paper 4 | RECOVER | AI chaos engineering, chaos-validated recovery |
| Paper 5 | DETECT | OTel anomaly detection, cooldown exclusion, feature ablation |
| Paper 6 | SECURE | LLM for IaC, security scanning |
| Paper 7 | DETECT | Streaming anomaly detection, Kafka/Flink |

## Development Guidelines
- Follow all conventions from parent `saas/CLAUDE.md`
- Python 3.12+, type hints, snake_case
- Never mention AI/Claude in commits or public content
- Test detection code against Paper 5 benchmarks before claiming it works
- Target conference: KubeCon NA 2026
