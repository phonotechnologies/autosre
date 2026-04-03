# AutoSRE: Core Technology Deep Dive

This document explains the technical foundations that make AutoSRE unique. Each section maps to published research and explains the engineering behind the product.

---

## 1. Cooldown-Aware Anomaly Detection

### The Problem
Traditional anomaly detection systems produce cascading false positives after incidents. When a service recovers from an outage, its behavior is "abnormal" compared to the baseline: latencies are elevated, error rates are decaying, throughput is ramping up. Every existing tool flags this recovery period as anomalous, creating alert storms that fatigue on-call engineers.

### Our Solution
AutoSRE implements temporal cooldown exclusion: a per-signal, campaign-manifest-driven mechanism that automatically identifies and excludes post-incident recovery windows from anomaly baselines.

```
Normal ──→ Incident ──→ Recovery (COOLDOWN) ──→ Normal
                         ↑
                    Traditional tools alert here (false positive)
                    AutoSRE excludes this window automatically
```

### How It Works
1. **Incident detection** triggers a cooldown window per affected signal
2. **Cooldown manifest** defines per-signal recovery characteristics (e.g., "latency recovers in ~8 minutes, error rate in ~3 minutes")
3. **Baseline exclusion** removes the cooldown window from training data for all affected models
4. **Adaptive duration** learns optimal cooldown lengths from historical recovery patterns

### Research Evidence (Paper 5)
- Tested on Sock Shop microservices on EKS with Chaos Mesh fault injection
- Cooldown exclusion eliminated recovery-period false positives across all 6 model types
- No degradation in true positive detection rate

### Competitive Position
- **Dynatrace**: Manual maintenance windows (not automated, not per-signal)
- **Datadog**: Scheduled downtime suppression (time-based, not signal-aware)
- **Everyone else**: Nothing

---

## 2. Multi-Signal OTel-Native Anomaly Detection

### The Problem
Existing AIOps tools were built before OpenTelemetry. They ingest telemetry through proprietary agents or adapters, losing signal correlation. Traces, metrics, and logs are analyzed in separate pipelines with separate models, producing separate alerts that engineers must manually correlate.

### Our Solution
AutoSRE is built on OpenTelemetry from the ground up. All three signal types (traces, metrics, logs) are ingested via OTLP, correlated by trace context, and fed into a unified anomaly detection pipeline.

### Architecture

```
Services (instrumented with OTel SDK)
    │
    ▼
OTel Collector (Agent mode, per-node)
    │
    ▼
OTel Collector (Gateway mode, central)
    │
    ├──→ Kafka topic: autosre.traces
    ├──→ Kafka topic: autosre.metrics
    └──→ Kafka topic: autosre.logs
              │
              ▼
         Flink Jobs
    ┌─────────┼─────────┐
    │         │         │
  Trace     Metric    Log
  Detector  Detector  Detector
    │         │         │
    └─────────┼─────────┘
              │
              ▼
     Cross-Signal Correlator
              │
              ▼
     Unified Anomaly Score
              │
              ▼
     Alert (if above threshold)
```

### Signal-Specific Detection Strategies (Paper 5 Findings)

| Signal | Best Model | Best AUC | Key Features |
|--------|-----------|----------|--------------|
| **Traces** | Transformer-AE | 0.800 | Span duration, error rate, trace depth, service latency |
| **Metrics** | Transformer-AE (mean-only) | 0.964 | CPU, memory, network (mean aggregations only) |
| **Logs** | Isolation Forest | 0.640 | Error frequency, log level distribution, keyword extraction |

### Cross-Signal Severity Scoring
Each signal produces an independent anomaly score (0.0 to 1.0). The cross-signal correlator combines them:

```
severity = w_traces * score_traces + w_metrics * score_metrics + w_logs * score_logs
```

Where weights are learned from historical incidents (or default to equal weighting).

An anomaly flagged by all three signals is more severe than one flagged by metrics alone. This reduces false positives while maintaining recall.

---

## 3. Feature Ablation Intelligence

### The Discovery (Paper 5)
During Paper 5 experiments, a counterintuitive finding emerged: using only mean aggregations of metrics (12 features) produced AUC=0.964, outperforming the full feature set (300+ features including std, min, max, slope, IQR).

This means most organizations are collecting and paying for telemetry data that adds noise, not signal.

### Product Application
AutoSRE includes a feature ablation analysis module:

1. **Baseline**: Run detection with full feature set
2. **Ablation**: Systematically remove feature categories (statistical aggregations, derived features, signal types)
3. **Comparison**: Measure AUC/F1 impact of each removal
4. **Recommendation**: "Drop these 288 features. Keep these 12. Detection quality improves."

### Business Value
- Reduce observability costs (less data collected, stored, queried)
- Faster model training and inference (fewer features)
- Quantified: "We ran ablation on your environment. Dropping metric IQR, slope, and log features saves $X/month with no detection quality loss."

---

## 4. Streaming Anomaly Detection Pipeline

### Architecture (Paper 7)

```
Kafka Cluster (KRaft)
    │
    ├── topic: telemetry.metrics (10s intervals)
    ├── topic: telemetry.traces (per-request)
    └── topic: telemetry.logs (per-event)
         │
         ▼
    Flink Cluster
    ┌──────────────────────────────────────┐
    │ Job 1: Feature Engineering           │
    │   - Tumbling windows (1 min)         │
    │   - 8 derived streaming features     │
    │   - Aggregation (mean, std, etc.)    │
    ├──────────────────────────────────────┤
    │ Job 2: Anomaly Detection             │
    │   - PySAD streaming models           │
    │   - Half-Space Trees (real-time)     │
    │   - xStream (streaming ensemble)     │
    │   - PyTorch Trans-AE (batch micro)   │
    ├──────────────────────────────────────┤
    │ Job 3: Alert Correlation             │
    │   - Cross-signal fusion              │
    │   - Cooldown window check            │
    │   - Severity scoring                 │
    │   - Deduplication                    │
    └──────────────────────────────────────┘
         │
         ▼
    Alert Pipeline (Slack, PagerDuty, webhook)
```

### Streaming-Specific Derived Features (Paper 7)

| Feature | Formula | Detects |
|---------|---------|---------|
| `lag_velocity` | d(consumer_lag)/dt | Consumer falling behind |
| `lag_acceleration` | d2(consumer_lag)/dt2 | Emerging lag problems |
| `throughput_ratio` | records_out / records_in | Backpressure |
| `checkpoint_overhead_ratio` | checkpoint_duration / checkpoint_interval | Degrading checkpoints |
| `isr_stability` | ISR partition set stability over time | Broker health |
| `rebalance_frequency` | rebalances / time_window | Consumer group instability |
| `backpressure_ratio` | time_in_backpressure / window | Pipeline bottlenecks |
| `watermark_lag` | processing_time - event_time | Event ordering issues |

### Fault Taxonomy (Paper 7)

AutoSRE detects 8 categories of streaming faults:
1. **Broker crash** (node failure)
2. **Network partition** (split-brain)
3. **Consumer lag spike** (processing slower than ingestion)
4. **Checkpoint failure** (state loss risk)
5. **Backpressure cascade** (downstream bottleneck)
6. **Poison pill messages** (bad data causing crashes)
7. **Consumer rebalancing storm** (thrashing group membership)
8. **Out-of-memory** (resource exhaustion)

---

## 5. GNN-Based Root Cause Analysis

### The Problem
When a microservice incident occurs, dozens of services may show degraded metrics. Traditional RCA requires engineers to manually trace the dependency chain to find the root cause.

### Our Approach (Paper 1 Findings)
Graph Neural Networks operate directly on the service dependency graph:

```
Neo4j (service topology)
    │
    ▼
GNN Model (trained on historical incidents)
    │
    ├── Input: per-service anomaly scores + dependency edges
    ├── Propagation: message passing along service dependencies
    └── Output: ranked list of root cause candidates
         │
         ▼
    "Service payment-gateway is the root cause (92% confidence)"
```

### Why GNNs (Not Just Correlation)
- Paper 1 meta-analysis: GNNs achieve 85-93% accuracy on RCA
- Service dependencies are inherently graph-structured
- GNNs learn propagation patterns: "when service A degrades, services B and C follow within 30 seconds"
- Traditional correlation-based RCA misses indirect causation

### Blast Radius Prediction
Using Neo4j Graph Data Science:
- **PageRank**: identifies high-impact services (many downstream dependents)
- **Community detection**: identifies failure domains (services that fail together)
- **Shortest path**: estimates propagation time from root cause to affected services

---

## 6. Agentic Chaos Engineering

### The Closed Loop (Paper 4)

No existing tool connects chaos engineering with anomaly detection. AutoSRE closes this loop:

```
┌─────────────────────────────────────────────┐
│                                             │
│   DETECT anomaly                            │
│       │                                     │
│       ▼                                     │
│   DIAGNOSE root cause (GNN)                 │
│       │                                     │
│       ▼                                     │
│   DECIDE remediation                        │
│       │                                     │
│       ▼                                     │
│   RECOVER (execute fix)                     │
│       │                                     │
│       ▼                                     │
│   VALIDATE via chaos experiment ←───────────┘
│       │
│       ▼
│   "Fix confirmed. Service resilient."
│   OR
│   "Fix failed. Escalating to human."
└─────────────────────────────────────────────┘
```

### Paper 4 Contributions
- Taxonomy of ML/AI techniques across 5 chaos engineering lifecycle phases
- Empirical benchmark: AI-assisted fault selection discovers 30-50% more issues than manual
- Integration with Chaos Mesh and LitmusChaos

### LangGraph Agent Workflow

```python
# Simplified agent graph
triage_agent    → investigator_agent → rca_agent
                                           │
                                           ▼
                                    remediation_agent
                                           │
                                           ▼
                                    chaos_validation_agent
                                           │
                                    ┌──────┴──────┐
                                    │             │
                                 PASS          FAIL
                                    │             │
                                 close        escalate
                                 incident     to human
```

Each agent is a LangGraph node with:
- Defined input/output schemas
- Tool access via MCP (kubectl, prometheus, neo4j, slack)
- Checkpointing (can resume after LLM timeout or failure)
- Human-in-the-loop gates at configurable risk thresholds

---

## 7. Model Selection and Training

### Six-Model Portfolio

| Model | Type | Best For | Paper |
|-------|------|----------|-------|
| Isolation Forest | Point-in-time, unsupervised | Quick baseline, log anomalies | 5 |
| One-Class SVM | Point-in-time, unsupervised | Low-dimensional feature spaces | 5 |
| LSTM Autoencoder | Sequence, semi-supervised | Temporal patterns, gradual degradation | 5 |
| Transformer Autoencoder | Sequence, semi-supervised | Complex temporal dependencies, traces | 5 |
| CNN Autoencoder | Sequence, semi-supervised | Periodic patterns, fixed-length windows | 5 |
| LSTM VAE | Sequence, semi-supervised | Uncertainty quantification | 5 |

### Automated Model Selection
1. User connects OTel data source
2. AutoSRE runs all 6 models on a holdout window
3. Optuna tunes hyperparameters (up to 300 trials per model)
4. Best model per signal type is selected automatically
5. Ensemble option: combine top-3 models for higher confidence

### Training Pipeline
- **No labeled data required** (semi-supervised: train on normal data only)
- **Continuous retraining**: models retrain on rolling windows as baselines shift
- **Cooldown-excluded**: training data automatically excludes cooldown windows

---

## 8. MCP (Model Context Protocol) Integration

AutoSRE agents interact with infrastructure through MCP tools:

| MCP Server | Tools Exposed | Used By |
|------------|---------------|---------|
| **kubernetes-mcp** | kubectl get/describe/logs, pod restart, scale | Triage, Remediation agents |
| **prometheus-mcp** | PromQL queries, alert rules, recording rules | Investigation, Detection agents |
| **neo4j-mcp** | Cypher queries, topology traversal | RCA agent |
| **slack-mcp** | Send messages, thread updates, approval requests | All agents |
| **chaos-mesh-mcp** | Create/delete chaos experiments | Chaos validation agent |
| **runbook-mcp** | Search and execute runbooks via Haystack | Remediation agent |

This means agents can be extended by adding new MCP servers without changing agent code.
