-- V003: Raw metric data points table
-- Source: Kafka topic autosre.metrics
-- Query patterns: metric charts per service, feature MV aggregation

CREATE TABLE IF NOT EXISTS autosre.metrics
(
    -- Dimensions
    service              LowCardinality(String)             CODEC(ZSTD(1)),
    metric_name          LowCardinality(String)             CODEC(ZSTD(1)),

    -- Time + value
    timestamp            DateTime64(9, 'UTC')               CODEC(DoubleDelta, ZSTD(1)),
    value                Float64                             CODEC(Gorilla, ZSTD(1)),

    -- OTel attributes
    resource_attrs       Map(LowCardinality(String), String) CODEC(ZSTD(1)),
    point_attrs          Map(LowCardinality(String), String) CODEC(ZSTD(1)),

    -- Materialized common labels
    namespace            LowCardinality(String)
                         MATERIALIZED resource_attrs['k8s.namespace.name'] CODEC(ZSTD(1)),
    pod                  LowCardinality(String)
                         MATERIALIZED resource_attrs['k8s.pod.name'] CODEC(ZSTD(1)),
    container            LowCardinality(String)
                         MATERIALIZED point_attrs['container'] CODEC(ZSTD(1)),
    host_name            LowCardinality(String)
                         MATERIALIZED resource_attrs['host.name'] CODEC(ZSTD(1)),

    inserted_at          DateTime DEFAULT now()              CODEC(DoubleDelta, ZSTD(1))
)
ENGINE = MergeTree()
PARTITION BY toDate(timestamp)
ORDER BY (service, metric_name, timestamp)
TTL toDate(timestamp) + INTERVAL 14 DAY
SETTINGS index_granularity = 8192;
