-- V007: Correlated incident groups
-- Source: Detection pipeline (anomaly correlation) + agent layer + human input
-- Query patterns: open incidents, incident timeline, RCA lookup

CREATE TABLE IF NOT EXISTS autosre.incidents
(
    -- Identity
    incident_id          String                              CODEC(ZSTD(1)),

    -- Time bounds
    started_at           DateTime64(3, 'UTC')               CODEC(DoubleDelta, ZSTD(1)),
    ended_at             DateTime64(3, 'UTC')
                         DEFAULT toDateTime64('2099-01-01', 3, 'UTC')
                                                             CODEC(DoubleDelta, ZSTD(1)),

    -- Scope
    service              LowCardinality(String)             CODEC(ZSTD(1)),
    signals              Array(LowCardinality(String))      CODEC(ZSTD(1)),
    models               Array(LowCardinality(String))      CODEC(ZSTD(1)),

    -- Severity and stats
    severity             LowCardinality(String) DEFAULT 'info' CODEC(ZSTD(1)),
    max_score            Float32          DEFAULT 0.0        CODEC(Gorilla, ZSTD(1)),
    anomaly_count        UInt32           DEFAULT 0          CODEC(T64, ZSTD(1)),

    -- Status tracking
    status               LowCardinality(String) DEFAULT 'open' CODEC(ZSTD(1)),

    -- RCA context (populated by agent or human)
    root_cause           String           DEFAULT ''         CODEC(ZSTD(3)),
    resolution           String           DEFAULT ''         CODEC(ZSTD(3)),

    -- Feedback loop (model improvement)
    user_feedback        LowCardinality(String) DEFAULT ''  CODEC(ZSTD(1)),

    -- Metadata
    created_at           DateTime DEFAULT now()              CODEC(DoubleDelta, ZSTD(1)),
    updated_at           DateTime DEFAULT now()              CODEC(DoubleDelta, ZSTD(1))
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(started_at)
ORDER BY (service, started_at, incident_id)
TTL toDate(started_at) + INTERVAL 365 DAY
SETTINGS index_granularity = 8192;
