from datetime import datetime, timedelta, timezone

from app.config import (
    ANOMALY_BASELINE_BUCKET_SECONDS,
    ANOMALY_CURRENT_WINDOW_SECONDS,
    ANOMALY_ZSCORE_THRESHOLD,
    SLOW_P95_LATENCY_MS,
)
from app.services.anomaly import (
    METRIC_ERROR_RATE,
    METRIC_LATENCY_P95,
    OpenAnomaly,
    detect_anomalies,
    reconcile_open_anomalies,
)
from app.services.classification import MetricPoint

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _point(offset_seconds: float, latency_ms: float, status_code: int = 200) -> MetricPoint:
    return MetricPoint(timestamp=NOW - timedelta(seconds=offset_seconds), latency_ms=latency_ms, status_code=status_code)


def _baseline_points(values: list[float], status_code: int = 200) -> list[MetricPoint]:
    """One point per baseline bucket, placed safely inside that bucket."""
    return [
        _point(ANOMALY_CURRENT_WINDOW_SECONDS + i * ANOMALY_BASELINE_BUCKET_SECONDS + 1, v, status_code)
        for i, v in enumerate(values)
    ]


def _current_points(n: int, latency_ms: float, status_code: int = 200) -> list[MetricPoint]:
    return [_point(i + 1, latency_ms, status_code) for i in range(n)]


def by_metric(checks):
    return {c.metric: c for c in checks}


def test_latency_spike_flags():
    events = _baseline_points([100.0] * 20) + _current_points(5, latency_ms=500.0)
    checks = by_metric(detect_anomalies(events, NOW))

    assert checks[METRIC_LATENCY_P95].is_anomalous is True
    assert checks[METRIC_ERROR_RATE].is_anomalous is False


def test_error_burst_flags():
    baseline = _baseline_points([100.0] * 20, status_code=200)
    current = _current_points(5, latency_ms=100.0, status_code=200) + _current_points(5, latency_ms=100.0, status_code=500)
    checks = by_metric(detect_anomalies(baseline + current, NOW))

    assert checks[METRIC_ERROR_RATE].is_anomalous is True
    assert checks[METRIC_LATENCY_P95].is_anomalous is False


def test_normal_flags_nothing():
    baseline_values = [95.0, 100.0, 105.0, 100.0] * 5  # 20 buckets, mild natural variance
    events = _baseline_points(baseline_values) + _current_points(10, latency_ms=100.0)
    checks = detect_anomalies(events, NOW)

    assert all(not c.is_anomalous for c in checks)


def test_sustained_spike_is_one_anomaly():
    events = _baseline_points([100.0] * 20) + _current_points(5, latency_ms=500.0)
    tick1_checks = detect_anomalies(events, NOW)

    open_anomalies = reconcile_open_anomalies({}, tick1_checks, NOW)
    assert list(open_anomalies) == [METRIC_LATENCY_P95]
    first_incident = open_anomalies[METRIC_LATENCY_P95]
    assert first_incident.started_at == NOW
    assert first_incident.resolved_at is None

    # Second detection tick, 30s later, same ongoing spike (slightly different reading).
    now2 = NOW + timedelta(seconds=ANOMALY_CURRENT_WINDOW_SECONDS)
    events2 = [MetricPoint(e.timestamp + timedelta(seconds=ANOMALY_CURRENT_WINDOW_SECONDS), e.latency_ms, e.status_code) for e in events]
    tick2_checks = detect_anomalies(events2, now2)

    updated = reconcile_open_anomalies(open_anomalies, tick2_checks, now2)

    assert list(updated) == [METRIC_LATENCY_P95]  # still exactly one incident, not two
    second_incident = updated[METRIC_LATENCY_P95]
    assert second_incident.started_at == NOW  # unchanged: dedupe kept the original start
    assert second_incident.resolved_at is None


def test_incident_resolves_when_check_returns_to_normal():
    open_anomalies = {
        METRIC_LATENCY_P95: OpenAnomaly(
            metric=METRIC_LATENCY_P95, started_at=NOW, value=500.0, baseline_mean=100.0, z_score=40.0
        )
    }
    events = _baseline_points([100.0] * 20) + _current_points(5, latency_ms=100.0)
    checks = detect_anomalies(events, NOW)

    resolved = reconcile_open_anomalies(open_anomalies, checks, NOW)

    assert resolved[METRIC_LATENCY_P95].resolved_at == NOW


def test_slow_degradation_caught_by_absolute_threshold_not_zscore():
    # Baseline itself has already drifted up (350ms..483ms) and has enough
    # spread that a further creep to 520ms doesn't clear 3 baseline sigma —
    # this is the blind spot rolling z-score has for gradual degradation.
    baseline_values = [350.0 + i * 7.0 for i in range(20)]
    current_latency = SLOW_P95_LATENCY_MS + 20
    events = _baseline_points(baseline_values) + _current_points(5, latency_ms=current_latency)

    checks = by_metric(detect_anomalies(events, NOW))
    latency_check = checks[METRIC_LATENCY_P95]

    assert latency_check.z_score <= ANOMALY_ZSCORE_THRESHOLD  # z-score alone would miss it
    assert latency_check.is_anomalous is True  # absolute SLOW_P95_LATENCY_MS fallback catches it anyway


def test_insufficient_baseline_flags_nothing():
    events = _baseline_points([100.0] * 2) + _current_points(5, latency_ms=900.0)
    checks = detect_anomalies(events, NOW)

    assert checks == []
