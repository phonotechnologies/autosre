# AutoSRE: Do's and Don'ts

Strategic guardrails for building AutoSRE. Violating these has sunk similar projects.

---

## DO's

### Product Strategy

**DO start with a CLI, not a dashboard.**
The fastest path to adoption is `pip install autosre && autosre detect`. Dashboards come later. Prometheus started as a binary. Terraform started as a CLI. Every successful infra tool earns its UI after proving CLI value.

**DO ship the anomaly detection engine first.**
Module 1 (DETECT) is the entire MVP. Cooldown-aware detection + OTel-native ingestion + streaming detection. If this does not work, nothing else matters. Resist the urge to build the dashboard, the IDP, the FinOps module, or the chaos integration before the core detection is proven.

**DO keep the open-source core genuinely useful.**
Apache-2.0 for the detection engine, CLI, and OTel integration. The OSS version must solve a real problem on its own, not be a crippled teaser. Grafana model: OSS core is production-grade; managed service adds convenience, scale, and enterprise features.

**DO dogfood from day one.**
AutoSRE should monitor itself using AutoSRE. The OTel Collector exports AutoSRE's own telemetry into its own detection pipeline. Nothing builds credibility like "we run this on ourselves."

**DO publish benchmarks publicly.**
Paper 5 and Paper 7 provide peer-reviewed benchmarks. Ship them as reproducible scripts in the repo. Let people verify the claims. No other AIOps tool does this.

**DO build for the on-call engineer, not the VP.**
The buyer may be a VP of Engineering, but the user is the person getting paged at 3 AM. Every feature must reduce their pain. If it does not help the on-call engineer, it does not ship.

**DO make model selection invisible.**
The user should never have to choose between "Isolation Forest" and "Transformer Autoencoder." AutoSRE runs all models, selects the best per signal, and exposes a single anomaly score. Advanced users can override.

### Technical

**DO use OpenTelemetry as the only ingestion path.**
No proprietary agents. No Datadog/New Relic adapters. OTLP in, anomalies out. This is the moat. If a user already has OTel instrumented (81% of K8s users do), AutoSRE works immediately.

**DO implement cooldown exclusion in the core, not as a plugin.**
This is the primary differentiator. It must be woven into training, inference, and alerting from the start. Bolting it on later creates architectural debt.

**DO separate the streaming pipeline from the agent layer.**
Kafka/Flink handles data; LangGraph handles decisions. They communicate through well-defined interfaces (Kafka topics, gRPC). This allows scaling them independently and testing them independently.

**DO version ML models as artifacts.**
Every trained model gets a version, a training window timestamp, and a performance snapshot (AUC, F1). Model registry in S3 or MLflow. No "mystery model running in production."

**DO write integration tests against a real OTel Collector.**
Unit tests for ML models. Integration tests for the full pipeline: OTel SDK, Collector, Kafka, Flink, detection, alert. Paper 5's testbed setup is the template.

**DO design for air-gapped deployment from the start.**
Enterprise customers in regulated industries (finance, healthcare, government) cannot send telemetry to a cloud service. Helm chart + self-hosted LLM (Llama 3) must work.

### Community and Business

**DO contribute back to CNCF/OTel.**
If AutoSRE discovers issues or improvements in the OTel Collector, contribute upstream. This builds credibility and creates a natural funnel from the OTel community to AutoSRE. Target CNCF Sandbox status within 12 months.

**DO publish the streaming benchmark dataset (Paper 7) on Zenodo with a DOI.**
This becomes a community resource that cites your paper and promotes AutoSRE. Every researcher who uses the dataset becomes an ambassador.

**DO price the managed service per monitored service, not per seat.**
Per-seat pricing penalizes collaboration. Per-service pricing aligns with value delivered. Free tier: up to 5 services. Growth tier: up to 50. Enterprise: unlimited.

---

## DON'Ts

### Product Strategy

**DON'T build a dashboard before the detection engine works.**
The temptation to show something visual is strong. Resist it. A beautiful dashboard over broken detection is worse than a CLI that catches real anomalies.

**DON'T try to replace Datadog, Grafana, or PagerDuty.**
AutoSRE is not an observability platform. It is an intelligence layer that sits on top of existing observability. Users keep their Grafana dashboards and PagerDuty alerts. AutoSRE makes them smarter.

**DON'T call it an "AIOps platform."**
AIOps is a poisoned term. Gartner hype cycles, failed Moogsoft/BigPanda deployments, and "AI-powered" stickers on legacy tools have made practitioners skeptical. Position as: "research-backed anomaly detection for SRE teams." Let the AI be invisible.

**DON'T launch with all 7 modules.**
Ship DETECT (Module 1) as v0.1. Add DIAGNOSE (Module 2) in v0.2. Iterate. The full platform vision is a 2-year roadmap, not a launch feature set.

**DON'T chase enterprise deals before PMF.**
Get 10 teams using the OSS version and loving it. Then build the enterprise features they ask for. Not the other way around.

**DON'T fork OpenClaw or DeerFlow.**
Neither is SRE-focused. Forking means maintaining their codebase plus your additions. Use LangGraph as a dependency; build SRE-specific workflows from scratch. Less maintenance debt, more control.

### Technical

**DON'T build a proprietary telemetry agent.**
This is the mistake every observability vendor made before OTel. Proprietary agents create vendor lock-in and user resentment. OTel is the standard. Use it.

**DON'T store raw telemetry in PostgreSQL.**
PostgreSQL is for structured application data (incidents, users, configs). Raw traces, metrics, and logs go through Kafka and are archived to S3. Hot queries go through Flink. Mixing OLTP and telemetry in the same store will break at scale.

**DON'T train ML models on customer data without explicit consent.**
Each customer's models are trained on their data only. No shared models across tenants. No "we use aggregated data to improve models" without opt-in. This is table stakes for enterprise trust.

**DON'T hardcode alert thresholds.**
The whole point is automated threshold discovery via Optuna. No config file with `threshold: 0.85`. The system learns the right threshold per signal, per service, per environment.

**DON'T use LLMs for anomaly detection.**
LLMs are for incident summaries, runbook generation, and natural language queries. They are terrible at numerical anomaly detection (slow, expensive, non-deterministic). Use proper ML models (PyOD, PySAD, PyTorch) for detection. Use LLMs for interpretation.

**DON'T build a custom streaming framework.**
Kafka + Flink is battle-tested at every scale. Building a custom streaming engine is a 2-year detour that produces something worse than Flink. Use PyFlink for ML integration.

**DON'T ignore model drift.**
Models trained on last month's data may not work this month. Implement automatic drift detection and retraining triggers. Paper 5's rolling window approach is the template.

**DON'T make the agent autonomous by default.**
Default mode: agents recommend, humans approve. Autonomy is opt-in, per action type, with blast radius limits. Paper 1 finding: only 8% of self-healing systems implement human oversight, and the ones that do not get turned off after the first bad auto-remediation.

### Community and Business

**DON'T use a restrictive license.**
Apache-2.0 or MIT for the core. Not SSPL (MongoDB), not BSL (HashiCorp), not AGPL (Grafana). The SRE community is allergic to license bait-and-switch. Build trust first.

**DON'T spam Hacker News / Reddit with marketing.**
Show the research. Show the benchmarks. Show the code. Let practitioners discover and validate. One genuine "Show HN: I built an OTel-native anomaly detector backed by peer-reviewed research" post beats 100 marketing launches.

**DON'T compete on price with cloud provider built-ins.**
Azure SRE Agent and AWS DevOps Agent are free/cheap for their respective clouds. AutoSRE's value is: multi-cloud, open-source, research-backed, no vendor lock-in. Competing on price against Azure/AWS is losing.

**DON'T promise "AI that replaces SREs."**
This messaging alienates the exact people who would adopt the tool. Position as: "AI that makes SREs faster and reduces alert fatigue." The human stays in the loop. Always.

---

## Decision Framework

When in doubt about a feature or technical decision, ask:

1. **Does this help the on-call engineer at 3 AM?** If no, deprioritize.
2. **Is this backed by our research?** If no, is it backed by someone else's? If neither, reconsider.
3. **Does this require a proprietary agent or format?** If yes, find an OTel-native way.
4. **Can this be tested with our existing Paper 5/7 datasets?** If yes, test it before shipping.
5. **Would this survive a Hacker News comment section?** If the first comment would be "so it is just $EXISTING_TOOL with a wrapper," rethink the differentiation.
