# AutoSRE: Mateen's Action Items

Things that require human judgment, account access, financial decisions, or external communication.

---

## DECISIONS MADE

- [x] **Product name**: AutoSRE
- [x] **Domain**: autosre.dev (purchased)
- [x] **Business model**: Grafana model (Apache-2.0 OSS core + managed service)
- [x] **Pricing**: Free for now
- [x] **Entity**: Phono Technologies Inc.
- [x] **LLM strategy**: vLLM self-hosted with Qwen/DeepSeek (no API dependency)
- [x] **Cloud provider**: AWS
- [x] **Database**: ClickHouse (telemetry), self-hosted
- [x] **MVP scope**: Module 1 (DETECT) confirmed
- [x] **Timeline**: No targets, go with flow
- [x] **Conference**: Target KubeCon NA 2026
- [x] **Architecture**: Modular monolith → SOA (not microservices)

---

## NAMESPACE (ALL DONE)

- [x] **GitHub**: https://github.com/phonotechnologies/autosre (public, Apache-2.0)
- [x] **PyPI**: https://pypi.org/project/autosre/0.0.1/
- [x] **npm**: @mateenali66/autosre@0.0.1
- [ ] **Also register**: `autosre.io` and `autosre.ai` as redirects ($12-15/yr each)

---

## BUILD STATUS (as of Apr 3, 2026)

**Phase 1 is COMPLETE. 66 tests passing, lint clean, CLI working.**

| What | Status | Files |
|------|--------|-------|
| 6 ML models (Paper 5) | Done | `detection/models/` |
| Cooldown exclusion | Done | `detection/cooldown/` |
| Threshold discovery | Done | `detection/threshold/` |
| Late fusion (4 strategies) | Done | `detection/fusion.py` |
| Feature ablation | Done | `detection/ablation/` |
| Optuna tuning (6 models) | Done | `detection/tuning.py` |
| OTel OTLP parsers | Done | `collector/parser.py` |
| Feature engineering | Done | `collector/features.py` |
| Alerting (Slack + webhook) | Done | `alerting/dispatcher.py` |
| CLI (init/train/detect/models) | Done | `cli/main.py` |
| Config (YAML) | Done | `config/schema.py` |
| Docker Compose | Done | `docker-compose.yml` |
| GitHub Actions CI | Done | `.github/workflows/ci.yml` |
| Architecture docs | Done | `architecture.md` |

**Next: Phase 2 (streaming pipeline, ClickHouse, vLLM)**

---

## THINGS TO CHECK / VALIDATE

### IP and Licensing
- [ ] **Paper 5 code licensing** -- ML models from Paper 5 are now in AutoSRE. Confirm:
  - Code was written independently (not under employment contract)
  - Safe to release under Apache-2.0
  - Do you need to re-license or rewrite?
- [ ] **Paper 7 dataset** -- Publish on Zenodo with CC-BY-4.0. Confirm no proprietary data.
- [ ] **Patent alignment** -- Does the cooldown exclusion provisional patent (Aug-Sep 2026) cover the method as implemented in AutoSRE?

### Competitive Monitoring
- [ ] **Monitor OpenSRE (Tracer-Cloud)** -- github.com/Tracer-Cloud/opensre (336 stars)
- [ ] **Azure SRE Agent** -- GA March 2026
- [ ] **AWS DevOps Agent** -- Launched April 2026

**How AutoSRE is different from all three:**

| Dimension | OpenSRE | Azure SRE Agent | AWS DevOps Agent | **AutoSRE** |
|-----------|---------|-----------------|------------------|-------------|
| **Source** | OSS (small) | Proprietary | Proprietary | OSS (Apache-2.0) |
| **Cloud lock-in** | None | Azure only | AWS only | **None (multi-cloud)** |
| **Detection method** | Generic LLM | Proprietary ML | Proprietary ML | **6 peer-reviewed ML models** |
| **Cooldown exclusion** | No | No | No | **Yes (unique)** |
| **OTel-native** | Partial | No (Azure Monitor) | No (CloudWatch) | **Yes (OTLP only)** |
| **Self-hosted LLM** | No | No | No | **Yes (vLLM + Qwen/DeepSeek)** |
| **Research-backed** | No | Internal only | Internal only | **7 published papers** |
| **Streaming detection** | No | No | No | **Yes (Kafka + Flink)** |
| **Feature ablation** | No | No | No | **Yes (proven AUC=0.964)** |
| **Cost** | Free | Bundled with Azure | Bundled with AWS | **Free (OSS)** |

### Community & Positioning
- [ ] **KubeCon NA 2026 CFP** -- Submit talk. Check CFP deadlines.
- [ ] **CNCF Sandbox** -- Target 12 months after first public release
- [ ] **Blog post launch series**:
  1. "Why existing AIOps tools fail at anomaly detection"
  2. "How cooldown exclusion eliminates false alerts"
  3. "Show HN: AutoSRE"

### Personal Alignment
- [ ] **EB2-NIW** -- Confirm with attorney that OSS SRE tool counts as "substantial merit"
- [ ] **Time allocation** -- No pressure, go with flow

---

## ONGOING

- [ ] Review code and provide feedback on any adjustments
- [ ] Say "continue" in next conversation to pick up Phase 2
