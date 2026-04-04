-- V010: Materialized view - trace features (1-minute windows)
-- Triggered on every INSERT to spans table
-- Produces 13 trace features matching features.py engineer_trace_features()

CREATE MATERIALIZED VIEW IF NOT EXISTS autosre.mv_trace_features
TO autosre.features
AS
SELECT
    toStartOfMinute(start_time)              AS timestamp,
    service                                   AS service,
    'traces'                                  AS signal,
    toUInt16(60)                              AS window_seconds,

    -- Span/trace counts
    count()                                   AS span_count,
    uniqExact(trace_id)                       AS trace_count,

    -- Latency percentiles
    toFloat32(quantile(0.50)(duration_us))    AS p50_duration,
    toFloat32(quantile(0.95)(duration_us))    AS p95_duration,
    toFloat32(quantile(0.99)(duration_us))    AS p99_duration,
    toFloat32(avg(duration_us))               AS mean_duration,
    toFloat32(stddevPop(duration_us))         AS std_duration,
    toFloat32(max(duration_us))               AS max_duration,

    -- Error metrics
    countIf(
        status_code IN ('2', 'ERROR', '500', '502', '503', '504')
        OR startsWith(status_code, '5')
    )                                         AS error_span_count,
    toFloat32(
        countIf(
            status_code IN ('2', 'ERROR', '500', '502', '503', '504')
            OR startsWith(status_code, '5')
        ) / greatest(count(), 1)
    )                                         AS error_span_rate,

    -- Coefficient of variation
    toFloat32(
        if(avg(duration_us) > 0,
           stddevPop(duration_us) / avg(duration_us),
           0.0)
    )                                         AS duration_cv,

    'mv'                                      AS source

FROM autosre.spans
GROUP BY
    toStartOfMinute(start_time),
    service;
