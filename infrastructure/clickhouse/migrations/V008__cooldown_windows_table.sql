-- V008: Cooldown exclusion windows
-- Maps to CooldownWindow dataclass in detection/cooldown/exclusion.py
-- Source: Detection pipeline (after incident detection)
-- Query patterns: training data exclusion, cooldown audit trail

CREATE TABLE IF NOT EXISTS autosre.cooldown_windows
(
    cooldown_id          String                              CODEC(ZSTD(1)),
    service              LowCardinality(String)             CODEC(ZSTD(1)),
    signal               LowCardinality(String)             CODEC(ZSTD(1)),
    incident_id          String           DEFAULT ''         CODEC(ZSTD(1)),

    -- Time bounds (maps to CooldownWindow.start / .end)
    start_time           DateTime64(3, 'UTC')               CODEC(DoubleDelta, ZSTD(1)),
    end_time             DateTime64(3, 'UTC')               CODEC(DoubleDelta, ZSTD(1)),

    -- Config that produced this window
    duration_minutes     UInt16           DEFAULT 10         CODEC(T64, ZSTD(1)),

    created_at           DateTime DEFAULT now()              CODEC(DoubleDelta, ZSTD(1))
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(start_time)
ORDER BY (service, signal, start_time)
TTL toDate(start_time) + INTERVAL 365 DAY
SETTINGS index_granularity = 8192;
