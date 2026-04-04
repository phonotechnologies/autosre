-- V006: Anomaly detection scores
-- Source: Detection engine (batch autosre detect) + Flink streaming detection
-- Query patterns: anomaly timeline per service, severity filtering, fusion scores

CREATE TABLE IF NOT EXISTS autosre.anomaly_scores
(
    -- Key
    timestamp            DateTime64(3, 'UTC')               CODEC(DoubleDelta, ZSTD(1)),
    service              LowCardinality(String)             CODEC(ZSTD(1)),
    signal               LowCardinality(String)             CODEC(ZSTD(1)),
    model                LowCardinality(String)             CODEC(ZSTD(1)),

    -- Per-model score
    score                Float32                             CODEC(Gorilla, ZSTD(1)),
    threshold            Float32                             CODEC(Gorilla, ZSTD(1)),
    is_anomaly           UInt8                               CODEC(T64, ZSTD(1)),

    -- Fusion scores (denormalized: avoids JOIN at dashboard query time)
    fusion_max           Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),
    fusion_avg           Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),
    fusion_weighted      Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),
    fusion_vote          UInt8            DEFAULT 0           CODEC(T64, ZSTD(1)),

    -- Context
    model_version        LowCardinality(String) DEFAULT ''  CODEC(ZSTD(1)),
    window_seconds       UInt16           DEFAULT 60         CODEC(T64, ZSTD(1)),
    severity             LowCardinality(String) DEFAULT 'info' CODEC(ZSTD(1)),
    details              String           DEFAULT '{}'       CODEC(ZSTD(3)),

    inserted_at          DateTime DEFAULT now()              CODEC(DoubleDelta, ZSTD(1))
)
ENGINE = ReplacingMergeTree(inserted_at)
PARTITION BY toDate(timestamp)
ORDER BY (service, signal, model, timestamp)
TTL toDate(timestamp) + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- Fast lookup for anomalous-only queries
ALTER TABLE autosre.anomaly_scores ADD INDEX IF NOT EXISTS idx_anomaly is_anomaly
    TYPE set(2) GRANULARITY 4;
