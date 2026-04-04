-- V002: Raw trace spans table
-- Source: Kafka topic autosre.traces (via Flink or direct insert)
-- Query patterns: trace waterfall by trace_id, service latency breakdown,
--   materialized view aggregation for trace features

CREATE TABLE IF NOT EXISTS autosre.spans
(
    -- Identity
    trace_id             FixedString(32)                    CODEC(ZSTD(1)),
    span_id              FixedString(16)                    CODEC(ZSTD(1)),
    parent_span_id       String           DEFAULT ''        CODEC(ZSTD(1)),

    -- Dimensions (low cardinality first for ORDER BY efficiency)
    service              LowCardinality(String)             CODEC(ZSTD(1)),
    operation            LowCardinality(String)             CODEC(ZSTD(1)),
    kind                 UInt8            DEFAULT 0          CODEC(T64, ZSTD(1)),
    status_code          LowCardinality(String) DEFAULT ''  CODEC(ZSTD(1)),

    -- Timestamps and durations
    start_time           DateTime64(6, 'UTC')               CODEC(DoubleDelta, ZSTD(1)),
    duration_us          Int64                               CODEC(Gorilla, ZSTD(1)),

    -- OTel attributes (dynamic, schema-flexible)
    resource_attrs       Map(LowCardinality(String), String) CODEC(ZSTD(1)),
    span_attrs           Map(LowCardinality(String), String) CODEC(ZSTD(1)),

    -- Materialized from resource_attrs for fast filtering
    namespace            LowCardinality(String)
                         MATERIALIZED resource_attrs['k8s.namespace.name'] CODEC(ZSTD(1)),
    pod                  LowCardinality(String)
                         MATERIALIZED resource_attrs['k8s.pod.name'] CODEC(ZSTD(1)),
    host_name            LowCardinality(String)
                         MATERIALIZED resource_attrs['host.name'] CODEC(ZSTD(1)),

    -- Ingestion metadata
    inserted_at          DateTime DEFAULT now()              CODEC(DoubleDelta, ZSTD(1))
)
ENGINE = MergeTree()
PARTITION BY toDate(start_time)
ORDER BY (service, operation, start_time, trace_id, span_id)
TTL toDate(start_time) + INTERVAL 14 DAY
SETTINGS index_granularity = 8192;

-- bloom_filter for trace_id point lookups (trace waterfall view)
ALTER TABLE autosre.spans ADD INDEX IF NOT EXISTS idx_trace_id trace_id
    TYPE bloom_filter(0.01) GRANULARITY 4;
