# AutoSRE

Research-backed, OTel-native anomaly detection for SRE teams.

AutoSRE detects anomalies in your OpenTelemetry telemetry (traces, metrics, logs) using 6 peer-reviewed ML models with cooldown-aware detection that eliminates false positives during recovery periods.

## What makes AutoSRE different

| Feature | AutoSRE | Traditional AIOps |
|---------|---------|-------------------|
| **Cooldown-aware detection** | Automatically excludes recovery periods from baselines | Floods you with false alerts after every incident |
| **OTel-native** | Built on OpenTelemetry from the ground up (OTLP in, anomalies out) | Proprietary agents or bolted-on adapters |
| **6 ML models** | IF, OC-SVM, LSTM-AE, Transformer-AE, CNN-AE, LSTM-VAE | Single model, often rule-based |
| **Self-hosted LLM** | vLLM + Qwen/DeepSeek (no API dependency, no per-token costs) | Requires cloud API keys |
| **Research-backed** | Every model validated in peer-reviewed publications | "Trust us, it's AI" |
| **Feature ablation** | Tells you which telemetry signals actually matter (mean-only metrics: AUC=0.964) | Collects everything, hopes for the best |

## Quick Start

```bash
pip install autosre

# Generate config
autosre init

# Train on your telemetry data
autosre train ./telemetry.parquet --signal metrics

# Detect anomalies
autosre detect ./new_data.parquet --model-dir ./models

# List available models
autosre models
```

## Models

All models are semi-supervised: trained on normal data only, no labels required.

| Model | Type | Best For | Paper 5 AUC |
|-------|------|----------|-------------|
| Isolation Forest | Point-in-time | Quick baseline, log anomalies | 0.640 |
| One-Class SVM | Point-in-time | Low-dimensional features | -- |
| LSTM Autoencoder | Sequence | Temporal patterns, gradual degradation | -- |
| **Transformer Autoencoder** | Sequence | **Complex temporal dependencies, traces** | **0.800** |
| 1D-CNN Autoencoder | Sequence | Periodic patterns | -- |
| LSTM VAE | Sequence | Uncertainty quantification | -- |

## Cooldown-Aware Detection

Traditional anomaly detectors produce cascading false positives after incidents. During recovery, latencies are elevated, error rates are decaying, throughput is ramping up. Every tool flags this as anomalous.

AutoSRE's cooldown exclusion automatically identifies and excludes post-incident recovery windows:

```
Normal --> Incident --> Recovery (COOLDOWN) --> Normal
                           ^
                    Other tools alert here (false positive)
                    AutoSRE excludes this window
```

## Architecture

```
Services (OTel SDK)
    |
    v
OTel Collector (OTLP)
    |
    v
Kafka (autosre.traces, autosre.metrics, autosre.logs)
    |
    v
AutoSRE Detection Engine (PyOD + PyTorch)
    |
    v
Alerts (Slack, webhook, PagerDuty)
```

## Local Development

```bash
# Start infrastructure
docker compose up -d

# Install in dev mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/
```

## Research Basis

AutoSRE bundles research from 7 peer-reviewed papers:

- **Paper 5**: OTel-native multi-signal anomaly detection (IEEE Access)
- **Paper 7**: Streaming anomaly detection on Kafka/Flink (Cluster Computing)
- **Paper 1**: Self-healing cloud infrastructure taxonomy (J. Cloud Computing)
- **Paper 4**: AI chaos engineering benchmark (Software: Practice & Experience)
- **Paper 2**: FinOps + ML cost optimization (PeerJ CS)
- **Paper 3**: Platform engineering taxonomy (Frontiers in CS)
- **Paper 6**: LLM for Infrastructure-as-Code (Information & Software Technology)

## License

Apache-2.0

## Links

- Website: https://autosre.dev
- GitHub: https://github.com/phonotechnologies/autosre
- PyPI: https://pypi.org/project/autosre/
