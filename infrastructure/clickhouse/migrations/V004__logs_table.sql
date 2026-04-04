-- V004: Raw log records table
-- Source: Kafka topic autosre.logs
-- Query patterns: error investigation, feature MV aggregation

CREATE TABLE IF NOT EXISTS autosre.logs
(
    -- Dimensions
    service              LowCardinality(String)             CODEC(ZSTD(1)),
    severity             LowCardinality(String) DEFAULT 'UNSPECIFIED' CODEC(ZSTD(1)),

    -- Time
    timestamp            DateTime64(9, 'UTC')               CODEC(DoubleDelta, ZSTD(1)),

    -- Content
    body                 String                              CODEC(ZSTD(3)),

    -- OTel attributes
    resource_attrs       Map(LowCardinality(String), String) CODEC(ZSTD(1)),
    log_attrs            Map(LowCardinality(String), String) CODEC(ZSTD(1)),

    -- Trace correlation
    trace_id             FixedString(32)  DEFAULT ''         CODEC(ZSTD(1)),
    span_id              FixedString(16)  DEFAULT ''         CODEC(ZSTD(1)),

    -- Materialized from resource_attrs
    namespace            LowCardinality(String)
                         MATERIALIZED resource_attrs['k8s.namespace.name'] CODEC(ZSTD(1)),
    pod                  LowCardinality(String)
                         MATERIALIZED resource_attrs['k8s.pod.name'] CODEC(ZSTD(1)),
    host_name            LowCardinality(String)
                         MATERIALIZED resource_attrs['host.name'] CODEC(ZSTD(1)),

    -- Precomputed for feature MVs (avoid string matching at aggregation time)
    is_error             UInt8 MATERIALIZED (
                            severity IN ('ERROR', 'FATAL', 'CRITICAL')
                            OR positionCaseInsensitive(body, 'error') > 0
                            OR positionCaseInsensitive(body, 'exception') > 0
                            OR positionCaseInsensitive(body, 'fatal') > 0
                            OR positionCaseInsensitive(body, 'panic') > 0
                            OR positionCaseInsensitive(body, 'traceback') > 0
                         ) CODEC(T64, ZSTD(1)),
    is_warn              UInt8 MATERIALIZED (
                            severity IN ('WARN', 'WARNING')
                            OR positionCaseInsensitive(body, 'warn') > 0
                         ) CODEC(T64, ZSTD(1)),

    inserted_at          DateTime DEFAULT now()              CODEC(DoubleDelta, ZSTD(1))
)
ENGINE = MergeTree()
PARTITION BY toDate(timestamp)
ORDER BY (service, severity, timestamp)
TTL toDate(timestamp) + INTERVAL 30 DAY
SETTINGS index_granularity = 8192;

-- Full-text search on log body for incident investigation
ALTER TABLE autosre.logs ADD INDEX IF NOT EXISTS idx_body body
    TYPE tokenbf_v1(10240, 3, 0) GRANULARITY 4;
