-- V011: Materialized view - metric features (1-minute windows)
-- Triggered on every INSERT to metrics table
-- Produces dynamic metric features as Map({metric}_{agg} -> value)
-- Note: For full fidelity (mean+std+max per metric), Flink is recommended.
-- This MV handles mean aggregation; Flink or batch adds std/max.

CREATE MATERIALIZED VIEW IF NOT EXISTS autosre.mv_metric_features
TO autosre.features
AS
SELECT
    toStartOfMinute(timestamp)               AS timestamp,
    service                                   AS service,
    'metrics'                                 AS signal,
    toUInt16(60)                              AS window_seconds,

    -- Pack all metric means into the Map column
    -- Each metric_name becomes a key: "{metric_name}_mean" -> avg(value)
    CAST(
        mapFromArrays(
            groupArray(concat(metric_name, '_mean')),
            groupArray(toFloat32(avg_val))
        ),
        'Map(LowCardinality(String), Float32)'
    )                                         AS metric_features,

    'mv'                                      AS source

FROM (
    SELECT
        toStartOfMinute(timestamp) AS ts,
        service,
        metric_name,
        avg(value) AS avg_val
    FROM autosre.metrics
    GROUP BY ts, service, metric_name
)
GROUP BY timestamp, service;
