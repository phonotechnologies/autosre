# AutoSRE: Feature Map

**Tagline**: Research-backed, OTel-native, agentic SRE platform.

Every feature below traces back to peer-reviewed research from 7 PhD papers. This is not a feature wishlist; it is a product roadmap grounded in published empirical evidence.

---

## Feature Architecture Overview

```
+------------------------------------------------------------------+
|                        AutoSRE Platform                          |
+------------------------------------------------------------------+
|                                                                  |
|  [1] DETECT        [2] DIAGNOSE      [3] DECIDE    [4] RECOVER  |
|  Papers 5,7        Papers 1,4        Papers 1,2    Papers 1,4   |
|                                                                  |
|  [5] PLATFORM      [6] OPTIMIZE      [7] SECURE                 |
|  Paper 3           Paper 2           Paper 6                     |
|                                                                  |
+------------------------------------------------------------------+
```

---

## Module 1: DETECT (Anomaly Detection Engine)

**Research basis**: Paper 5 (OpenTelemetry AIOps) + Paper 7 (Streaming Anomaly Detection)

### 1.1 OTel-Native Multi-Signal Anomaly Detection
- Ingests traces, metrics, and logs via OTLP (not bolted-on adapters)
- Fuses all three signal types for cross-signal anomaly scoring
- Paper 5 finding: Transformer-AE on traces achieves AUC=0.800; mean-only metrics achieve AUC=0.964
- **Novelty**: No existing tool does native OTel multi-signal fusion for anomaly detection

### 1.2 Cooldown-Aware Detection
- Automatically excludes post-incident recovery periods from anomaly baselines
- Prevents cascading false positives during known-good recovery windows
- Per-signal, campaign-manifest-driven cooldown windows
- **Novelty**: Zero competitors implement this. Dynatrace has manual maintenance windows, which is fundamentally different from automated per-signal cooldown

### 1.3 Streaming Anomaly Detection (Real-Time)
- Kafka + Flink pipeline for sub-second anomaly detection
- Semi-supervised models: no labeled data required
- 8 streaming-specific derived features (lag_velocity, throughput_ratio, checkpoint_overhead_ratio, isr_stability, etc.)
- Paper 7 fault taxonomy: 8 streaming-specific faults (broker crash, consumer lag, checkpoint failure, backpressure, etc.)
- **Novelty**: First open benchmark for streaming anomaly detection on Kafka/Flink

### 1.4 Adaptive Threshold Discovery
- Automated threshold tuning via Optuna (1,800 trials proven in Paper 5)
- F1-optimal threshold selection from validation data
- No manual tuning required; adapts to each environment
- Per-service, per-signal threshold profiles

### 1.5 Feature Ablation Intelligence
- Paper 5 discovery: mean-only metrics (AUC=0.964) outperform full feature sets
- Recommends optimal telemetry collection: "you only need these 12 metrics, not 300"
- Reduces observability costs by eliminating redundant signals
- **Novelty**: No tool recommends which signals to drop based on empirical evidence

### 1.6 Six-Model Ensemble
- Isolation Forest, One-Class SVM, LSTM-AE, Transformer-AE, CNN-AE, LSTM-VAE
- Automatic model selection based on signal type and environment
- Supervised Random Forest as calibration upper bound
- PyOD (40+ algorithms) for batch; PySAD (17+ streaming algorithms) for real-time

---

## Module 2: DIAGNOSE (Root Cause Analysis)

**Research basis**: Paper 1 (Self-Healing Cloud Infrastructure) + Paper 4 (AI Chaos Engineering)

### 2.1 GNN-Based Root Cause Analysis
- Graph Neural Networks for microservice dependency-aware RCA
- Paper 1 finding: GNNs achieve 85-93% accuracy on RCA tasks
- Service dependency graph maintained in Neo4j with real-time topology updates
- Blast radius prediction using Graph Data Science (PageRank, community detection)

### 2.2 Causal Inference Engine
- Goes beyond correlation: identifies causal chains in failure propagation
- Integrates with chaos engineering results (Paper 4) to build causal models
- Cross-references historical incidents for pattern matching

### 2.3 Natural Language Incident Summaries
- LLM-powered plain-English explanations of what broke and why
- Contextual: pulls relevant runbooks, past incidents, service ownership
- Haystack RAG layer for knowledge retrieval

---

## Module 3: DECIDE (Automated Decision-Making)

**Research basis**: Paper 1 (Self-Healing, DECIDE phase) + Paper 2 (FinOps ML)

### 3.1 Human-in-the-Loop Approval Workflows
- Paper 1 finding: only 8% of self-healing systems implement human oversight
- Configurable approval gates: auto-approve low-risk, require approval for high-risk
- Slack/Teams integration for on-call approval flows
- Full audit trail of every automated decision

### 3.2 Risk-Scored Action Recommendations
- Each remediation action scored by blast radius (Neo4j graph), historical success rate, and reversibility
- "Safe to auto-execute" vs "needs human approval" classification
- Reinforcement learning for improving recommendations over time (Paper 1: RL for auto-scaling shows 44% cost reduction)

### 3.3 Cost-Aware Decision Making
- Paper 2: integrates FinOps considerations into remediation decisions
- "Scaling up fixes the issue but costs $X/hour; here is a cheaper alternative"
- Prevents cost-blind auto-remediation

---

## Module 4: RECOVER (Self-Healing & Remediation)

**Research basis**: Paper 1 (RECOVER phase) + Paper 4 (AI Chaos Engineering)

### 4.1 Automated Remediation Execution
- Runbook execution engine: converts documented playbooks into executable workflows
- LangGraph-orchestrated multi-step remediation (restart, scale, rollback, failover)
- Dry-run mode: shows what would happen without executing

### 4.2 Chaos-Validated Recovery
- Paper 4: validates that remediation actually works by running targeted chaos experiments
- "AutoSRE fixed the issue. Running chaos validation to confirm the fix holds."
- Continuous resilience scoring: how well does each service recover?

### 4.3 Intelligent Rollback
- Deployment-aware: correlates anomalies with recent deploys
- Auto-rollback with configurable blast radius thresholds
- Canary-aware: detects issues in canary deployments before full rollout

---

## Module 5: PLATFORM (Developer Experience)

**Research basis**: Paper 3 (Platform Engineering & IDPs)

### 5.1 Service Catalog & Dependency Map
- Real-time service ownership, dependencies, and health
- Paper 3 finding: developers spend 3-4 hours daily on non-core work without platform tools
- Auto-discovered from OTel traces (no manual registration)

### 5.2 Golden Paths for SRE
- Pre-built templates for common infrastructure patterns
- Paper 3: golden paths reduce onboarding time by 50% (Spotify case study)
- SRE-specific: alerting rules, SLO definitions, runbook templates

### 5.3 Developer Scorecards
- Paper 3 finding: only 2.3% of sources address scorecard automation
- Reliability scores per service (SLO adherence, incident frequency, MTTR)
- DORA metrics integration (deployment frequency, lead time, change failure rate, MTTR)

### 5.4 Self-Service SRE Actions
- Developers can trigger chaos experiments, view anomaly reports, check SLOs
- No need to page SRE team for routine operational queries
- Workflow automation for Day-1 (provisioning) and Day-2 (operations)

---

## Module 6: OPTIMIZE (FinOps Intelligence)

**Research basis**: Paper 2 (FinOps + Machine Learning)

### 6.1 Cost Anomaly Detection
- ML-driven detection of unexpected cost spikes
- Isolation Forest + Autoencoders for cost time-series
- Paper 2: 30-35% of cloud spend is waste

### 6.2 Intelligent Rightsizing
- Clustering + collaborative filtering for resource recommendations
- "Service X is over-provisioned by 40%; here is the optimal configuration"
- Considers performance SLOs, not just cost

### 6.3 Natural Language Cost Queries
- "What is driving our AWS bill this month?" answered in plain English
- LLM-powered cost analysis with FinOps Framework mapping
- Paper 2: maps to FinOps Foundation's Inform/Optimize/Operate phases

### 6.4 Observability Cost Optimization
- Paper 5 feature ablation finding: mean-only metrics match full feature performance
- "You are collecting 300 metrics but only 12 matter for anomaly detection"
- Quantified savings: reduce telemetry volume without losing detection quality

---

## Module 7: SECURE (IaC Intelligence)

**Research basis**: Paper 6 (LLM for Infrastructure-as-Code)

### 7.1 IaC Security Scanner
- Pre-deployment scanning of Terraform, CloudFormation, Pulumi, Kubernetes YAML
- Integrates Checkov + tfsec + OPA for comprehensive policy coverage
- Paper 6: LLMs achieve only 19% accuracy on IaC generation, so validation is critical

### 7.2 LLM-Assisted IaC Generation with Guardrails
- Generate infrastructure code with built-in security scanning
- RAG-augmented: pulls latest provider docs to avoid hallucinated resources
- Chain-of-thought prompting for complex multi-resource configurations

### 7.3 Compliance Policy Engine
- LLM-driven policy generation for security, cost, and compliance
- Maps to CIS benchmarks, SOC 2, HIPAA, PCI-DSS
- Continuous drift detection: alerts when infrastructure deviates from policy

---

## Feature Priority Matrix

| Priority | Feature | Module | Paper | Novelty | Effort |
|----------|---------|--------|-------|---------|--------|
| **P0** | OTel-native anomaly detection | DETECT | 5 | HIGH | Large |
| **P0** | Cooldown-aware detection | DETECT | 5 | UNIQUE | Medium |
| **P0** | Streaming anomaly detection | DETECT | 7 | HIGH | Large |
| **P1** | GNN-based RCA | DIAGNOSE | 1 | Medium | Large |
| **P1** | Human-in-the-loop workflows | DECIDE | 1 | Medium | Medium |
| **P1** | Feature ablation / signal optimization | DETECT | 5 | UNIQUE | Small |
| **P2** | Chaos-validated recovery | RECOVER | 4 | HIGH | Large |
| **P2** | Cost anomaly detection | OPTIMIZE | 2 | Low | Medium |
| **P2** | Service catalog + dependency map | PLATFORM | 3 | Low | Medium |
| **P3** | IaC security scanner | SECURE | 6 | Low | Medium |
| **P3** | Developer scorecards | PLATFORM | 3 | Medium | Small |
| **P3** | Natural language cost queries | OPTIMIZE | 2 | Low | Medium |

---

## Competitive Moats (Features No One Else Has)

1. **Cooldown-aware detection** -- zero competitors, peer-reviewed, potentially patentable
2. **Feature ablation intelligence** -- empirically proven signal optimization (mean-only AUC=0.964)
3. **OTel-native multi-signal fusion** -- built on OTel, not adapted to it
4. **Chaos-to-detection closed loop** -- chaos tools and detection tools exist separately; nobody connects them
5. **Research-backed model selection** -- 6 models, 1,800 Optuna trials, published benchmarks

---

## MVP Scope (v0.1)

The minimum viable product focuses on Module 1 (DETECT) only:

1. OTel Collector integration (ingest OTLP)
2. Cooldown-aware anomaly detection on metrics
3. Streaming detection via Kafka
4. CLI interface (`autosre detect --config config.yaml`)
5. Slack/webhook alerting

Everything else is Phase 2+.
