-- V005: Unified ML feature store
-- Source: Materialized views (auto) + Flink jobs (direct INSERT) + batch jobs
-- Query patterns: autosre train (read features), autosre detect (read for scoring)
-- Design: Wide table with fixed trace/log columns + dynamic metric Map + Paper 7 streaming columns

CREATE TABLE IF NOT EXISTS autosre.features
(
    -- Composite key
    timestamp            DateTime64(3, 'UTC')               CODEC(DoubleDelta, ZSTD(1)),
    service              LowCardinality(String)             CODEC(ZSTD(1)),
    signal               LowCardinality(String)             CODEC(ZSTD(1)),
    window_seconds       UInt16           DEFAULT 60         CODEC(T64, ZSTD(1)),

    -- Trace features (13 columns matching features.py engineer_trace_features)
    span_count           UInt64           DEFAULT 0          CODEC(T64, ZSTD(1)),
    trace_count          UInt64           DEFAULT 0          CODEC(T64, ZSTD(1)),
    p50_duration         Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),
    p95_duration         Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),
    p99_duration         Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),
    mean_duration        Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),
    std_duration         Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),
    max_duration         Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),
    error_span_count     UInt64           DEFAULT 0          CODEC(T64, ZSTD(1)),
    error_span_rate      Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),
    duration_cv          Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),

    -- Log features (7 columns matching features.py engineer_log_features)
    log_count            UInt64           DEFAULT 0          CODEC(T64, ZSTD(1)),
    error_count          UInt64           DEFAULT 0          CODEC(T64, ZSTD(1)),
    warn_count           UInt64           DEFAULT 0          CODEC(T64, ZSTD(1)),
    error_rate           Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),
    log_rate_change      Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),

    -- Metric features (dynamic per deployment: {metric_name}_{agg} -> value)
    metric_features      Map(LowCardinality(String), Float32) CODEC(ZSTD(1)),

    -- Paper 7 streaming-specific derived features (8 columns)
    lag_velocity                Float32 DEFAULT 0.0  CODEC(Gorilla, ZSTD(1)),
    lag_acceleration            Float32 DEFAULT 0.0  CODEC(Gorilla, ZSTD(1)),
    throughput_ratio            Float32 DEFAULT 0.0  CODEC(Gorilla, ZSTD(1)),
    checkpoint_overhead_ratio   Float32 DEFAULT 0.0  CODEC(Gorilla, ZSTD(1)),
    isr_stability               Float32 DEFAULT 0.0  CODEC(Gorilla, ZSTD(1)),
    rebalance_frequency         Float32 DEFAULT 0.0  CODEC(Gorilla, ZSTD(1)),
    backpressure_ratio          Float32 DEFAULT 0.0  CODEC(Gorilla, ZSTD(1)),
    watermark_lag               Float32 DEFAULT 0.0  CODEC(Gorilla, ZSTD(1)),

    -- Metadata
    source               LowCardinality(String) DEFAULT 'mv' CODEC(ZSTD(1)),
    inserted_at          DateTime DEFAULT now()              CODEC(DoubleDelta, ZSTD(1))
)
ENGINE = ReplacingMergeTree(inserted_at)
PARTITION BY toDate(timestamp)
ORDER BY (service, signal, window_seconds, timestamp)
TTL toDate(timestamp) + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;
