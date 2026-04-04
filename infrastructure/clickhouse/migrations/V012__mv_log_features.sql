-- V012: Materialized view - log features (1-minute windows)
-- Triggered on every INSERT to logs table
-- Produces 5 of 7 log features (log_rate_change requires cross-window, done by Flink/Python)

CREATE MATERIALIZED VIEW IF NOT EXISTS autosre.mv_log_features
TO autosre.features
AS
SELECT
    toStartOfMinute(timestamp)               AS timestamp,
    service                                   AS service,
    'logs'                                    AS signal,
    toUInt16(60)                              AS window_seconds,

    -- Log counts
    count()                                   AS log_count,
    countIf(is_error = 1)                     AS error_count,
    countIf(is_warn = 1)                      AS warn_count,

    -- Error rate
    toFloat32(
        countIf(is_error = 1) / greatest(count(), 1)
    )                                         AS error_rate,

    -- log_rate_change requires previous window comparison
    -- Set to 0.0 here; computed by Flink job or Python batch
    toFloat32(0.0)                            AS log_rate_change,

    'mv'                                      AS source

FROM autosre.logs
GROUP BY
    toStartOfMinute(timestamp),
    service;
