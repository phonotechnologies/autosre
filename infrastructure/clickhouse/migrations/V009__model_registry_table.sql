-- V009: Trained model registry
-- Stores metadata for every trained model version
-- Maps to BaseDetector.get_params() + ThresholdFinder + evaluation metrics

CREATE TABLE IF NOT EXISTS autosre.model_registry
(
    -- Identity
    model_id             String                              CODEC(ZSTD(1)),
    model_name           LowCardinality(String)             CODEC(ZSTD(1)),
    signal               LowCardinality(String)             CODEC(ZSTD(1)),

    -- Version
    version              UInt32                              CODEC(T64, ZSTD(1)),
    is_active            UInt8            DEFAULT 1          CODEC(T64, ZSTD(1)),

    -- Training metadata
    trained_at           DateTime64(3, 'UTC')               CODEC(DoubleDelta, ZSTD(1)),
    training_samples     UInt64           DEFAULT 0          CODEC(T64, ZSTD(1)),
    n_features           UInt16           DEFAULT 0          CODEC(T64, ZSTD(1)),
    seq_length           UInt16           DEFAULT 30         CODEC(T64, ZSTD(1)),
    window_seconds       UInt16           DEFAULT 60         CODEC(T64, ZSTD(1)),

    -- Hyperparameters (JSON from BaseDetector.get_params())
    hyperparameters      String           DEFAULT '{}'       CODEC(ZSTD(3)),

    -- Performance metrics
    threshold            Float32          DEFAULT 0.5        CODEC(Gorilla, ZSTD(1)),
    threshold_method     LowCardinality(String) DEFAULT 'percentile' CODEC(ZSTD(1)),
    auc_roc              Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),
    f1_score             Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),
    precision_score      Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),
    recall_score         Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),

    -- Artifact location
    artifact_path        String           DEFAULT ''         CODEC(ZSTD(1)),

    -- Feature columns used (ordered list for reproducibility)
    feature_columns      Array(String)                       CODEC(ZSTD(1)),

    created_at           DateTime DEFAULT now()              CODEC(DoubleDelta, ZSTD(1)),
    updated_at           DateTime DEFAULT now()              CODEC(DoubleDelta, ZSTD(1))
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(trained_at)
ORDER BY (model_name, signal, version)
TTL toDate(trained_at) + INTERVAL 365 DAY
SETTINGS index_granularity = 8192;
