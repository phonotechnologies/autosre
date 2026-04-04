# AutoSRE: Mateen's Action Items

---

## DECISIONS MADE

- [x] Product name: AutoSRE
- [x] Domain: autosre.dev (purchased)
- [x] Business model: Grafana model (Apache-2.0 OSS core + managed service)
- [x] Pricing: Free for now
- [x] Entity: Phono Technologies Inc.
- [x] LLM strategy: ollama (local dev) + vLLM (production on AWS)
- [x] Cloud provider: AWS
- [x] Database: ClickHouse (telemetry), self-hosted
- [x] MVP scope: Module 1 (DETECT) confirmed
- [x] Timeline: No targets, go with flow
- [x] Conference: Target KubeCon NA 2026
- [x] Architecture: Modular monolith → SOA

---

## NAMESPACE (ALL DONE)

- [x] GitHub: https://github.com/phonotechnologies/autosre
- [x] PyPI: https://pypi.org/project/autosre/0.0.1/
- [x] npm: @mateenali66/autosre@0.0.1
- [ ] Register `autosre.io` and `autosre.ai` as redirects ($12-15/yr each)

---

## BUILD STATUS (Apr 3, 2026)

**Phase 1 + 1.5 COMPLETE. 127 tests, 7 CLI commands, 5 API endpoints.**
**Phase 2 partially BLOCKED on Paper 7 completion.**

| Module | Status | Key Files |
|--------|--------|-----------|
| 6 ML models (Paper 5) | Done | `detection/models/` |
| Cooldown exclusion | Done | `detection/cooldown/` |
| Threshold discovery | Done | `detection/threshold/` |
| Late fusion (4 strategies) | Done | `detection/fusion.py` |
| Feature ablation | Done | `detection/ablation/` |
| Optuna tuning | Done | `detection/tuning.py` |
| OTel OTLP parsers | Done | `collector/parser.py` |
| Feature engineering | Done | `collector/features.py` |
| Alerting (Slack + webhook) | Done | `alerting/dispatcher.py` |
| CLI (7 commands) | Done | `cli/main.py` |
| FastAPI server (5 endpoints) | Done | `api/app.py` |
| ClickHouse schema (8 tables) | Done | `infrastructure/clickhouse/` |
| ClickHouseClient | Done | `storage/clickhouse.py` |
| Migration runner | Done | `infrastructure/clickhouse/migrate.py` |
| LLM client (ollama/vLLM) | Done | `inference/client.py` |
| Docker Compose | Done | `docker-compose.yml` |
| GitHub Actions CI | Done | `.github/workflows/ci.yml` |
| Streaming pipeline (Flink) | **BLOCKED** | Needs Paper 7 |

---

## BLOCKER: Paper 7

Paper 7 (Streaming Anomaly Detection on Kafka/Flink) is in planning phase.
The Flink streaming jobs and 8 derived features depend on Paper 7's experimental design.

**What's blocked**: Flink streaming detection, 30-sec windows, streaming-specific fault taxonomy
**What's NOT blocked**: Everything else (detection engine, CLI, API, ClickHouse, LLM)

**Resolution**: Complete Paper 7 experimental design, then resume AutoSRE Phase 2.

---

## THINGS TO CHECK / VALIDATE

### IP and Licensing
- [ ] Paper 5 code licensing: confirm code was written independently, safe for Apache-2.0
- [ ] Paper 7 dataset: publish on Zenodo with CC-BY-4.0
- [ ] Patent alignment: cooldown exclusion provisional patent (Aug-Sep 2026) covers AutoSRE method?

### Competitive Monitoring
- [ ] OpenSRE (Tracer-Cloud): github.com/Tracer-Cloud/opensre (336 stars)
- [ ] Azure SRE Agent: GA March 2026
- [ ] AWS DevOps Agent: Launched April 2026

**AutoSRE differentiators**:

| Dimension | Competitors | **AutoSRE** |
|-----------|------------|-------------|
| Source | Proprietary or small OSS | **Apache-2.0, full-featured** |
| Cloud lock-in | Azure/AWS only | **Multi-cloud** |
| Detection | Generic LLM or proprietary ML | **6 peer-reviewed ML models** |
| Cooldown exclusion | None | **Unique (patentable)** |
| OTel-native | Partial or none | **OTLP-only ingestion** |
| Self-hosted LLM | None | **ollama/vLLM** |
| Research-backed | No | **7 published papers** |

### Community & Positioning
- [ ] KubeCon NA 2026 CFP: check deadlines
- [ ] CNCF Sandbox: target 12 months after first public release
- [ ] Blog launch series (3 posts)

---

## NEXT ACTIONS (when resuming)

1. Complete Paper 7 experimental design → unblocks Flink streaming jobs
2. Run `docker compose up` integration test (Kafka + ClickHouse + OTel)
3. Test `autosre llm` with local ollama (`ollama serve && ollama pull qwen2.5-coder:7b`)
4. Review and provide feedback on architecture decisions
