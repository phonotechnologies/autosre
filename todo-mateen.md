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

---

## URGENT (Do This Week)

### Namespace Claims (ALL DONE)
- [x] **GitHub repo**: https://github.com/phonotechnologies/autosre (public, Apache-2.0)
- [x] **PyPI**: https://pypi.org/project/autosre/0.0.1/
- [x] **npm**: @mateenali66/autosre@0.0.1 (scoped; unscoped `autosre` blocked by npm due to similarity with `autosize`)
- [ ] **Also register**: `autosre.io` and `autosre.ai` as redirects to `autosre.dev` ($12-15/yr each, prevents squatting)

---

## THINGS TO CHECK / VALIDATE

### IP and Licensing
- [ ] **Paper 5 code licensing** -- ML models and training scripts from Paper 5 are the core detection engine. Confirm:
  - Code was written independently (not under employment contract)
  - Safe to release under Apache-2.0
  - Do you need to re-license or rewrite?
- [ ] **Paper 7 dataset** -- Publish on Zenodo with CC-BY-4.0. Confirm no proprietary data embedded.
- [ ] **Patent alignment** -- Does the cooldown exclusion provisional patent (Aug-Sep 2026) cover the method as implemented in AutoSRE?

### Competitive Monitoring
- [ ] **Monitor OpenSRE (Tracer-Cloud)** -- github.com/Tracer-Cloud/opensre (336 stars). Watch for feature overlap.
- [ ] **Azure SRE Agent** -- GA March 2026. Understand what they offer vs our differentiation (multi-cloud, OSS, research-backed, self-hosted LLM).
- [ ] **AWS DevOps Agent** -- Launched April 2026. Same: understand overlap and our edge.

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
- [ ] **KubeCon NA 2026 CFP** -- Submit talk: "Research-Backed Anomaly Detection: Building AutoSRE with Peer-Reviewed ML Models". Check CFP deadlines.
- [ ] **CNCF Sandbox** -- Target 12 months after first public release. Need:
  - 2 maintainers from different orgs (you + who?)
  - Governance document
  - Evidence of community adoption
- [ ] **Blog post launch series**:
  1. "Why existing AIOps tools fail at anomaly detection" (problem)
  2. "How cooldown exclusion eliminates false alerts" (solution)
  3. "Show HN: AutoSRE" (launch)

### Personal Alignment
- [ ] **EB2-NIW** -- Confirm with attorney that an OSS SRE tool with CNCF adoption counts as "substantial merit and national importance"
- [ ] **Time allocation** -- AutoSRE competes with Paper 7, patent, PhD, contracting. No pressure, but be aware.

---

## ONGOING

- [ ] Review all files in `saas/AutoSRE/` and provide feedback on any adjustments
- [ ] Decide when to start Phase 1 (scaffolding)
