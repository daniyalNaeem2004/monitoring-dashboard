from datetime import datetime, timedelta, timezone

from app.config import (
    CLASSIFICATION_WINDOW_SECONDS,
    FAILING_ERROR_RATE_THRESHOLD,
    FAILING_HEARTBEAT_TIMEOUT_SECONDS,
    SLOW_P95_LATENCY_MS,
)
from app.services.classification import MetricPoint, classify_service

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
FRESH_HEARTBEAT = NOW


def make_events(n: int, latency_ms: float, status_code: int, start_offset: float = 0) -> list[MetricPoint]:
    return [
        MetricPoint(
            timestamp=NOW - timedelta(seconds=start_offset + i),
            latency_ms=latency_ms,
            status_code=status_code,
        )
        for i in range(n)
    ]


def test_healthy_service():
    events = make_events(20, latency_ms=100, status_code=200)
    result = classify_service(events, last_heartbeat=FRESH_HEARTBEAT, now=NOW)

    assert result.status == "healthy"
    assert result.error_rate == 0.0
    assert result.p95_latency_ms == 100


def test_slow_service_p95_above_threshold():
    # 18 fast requests + 2 slow ones (10%) so the 95th percentile lands on
    # the slow group rather than being averaged away.
    events = make_events(18, latency_ms=100, status_code=200) + make_events(2, latency_ms=900, status_code=200)
    result = classify_service(events, last_heartbeat=FRESH_HEARTBEAT, now=NOW)

    assert result.status == "slow"
    assert result.p95_latency_ms == 900


def test_failing_service_error_rate_above_threshold():
    events = make_events(7, latency_ms=100, status_code=200) + make_events(3, latency_ms=100, status_code=500)
    result = classify_service(events, last_heartbeat=FRESH_HEARTBEAT, now=NOW)

    assert result.status == "failing"
    assert result.error_rate == 0.3


def test_failing_service_stale_heartbeat():
    stale_heartbeat = NOW - timedelta(seconds=FAILING_HEARTBEAT_TIMEOUT_SECONDS + 1)
    events = make_events(10, latency_ms=100, status_code=200)
    result = classify_service(events, last_heartbeat=stale_heartbeat, now=NOW)

    assert result.status == "failing"


def test_no_events_and_no_heartbeat_is_failing():
    result = classify_service([], last_heartbeat=None, now=NOW)

    assert result.status == "failing"
    assert result.error_rate == 0.0
    assert result.p95_latency_ms is None


def test_error_rate_exactly_at_threshold_is_not_failing():
    # 1/5 = exactly 20%, and the rule is ">20%", so this must not fail.
    events = make_events(4, latency_ms=100, status_code=200) + make_events(1, latency_ms=100, status_code=500)
    result = classify_service(events, last_heartbeat=FRESH_HEARTBEAT, now=NOW)

    assert result.error_rate == FAILING_ERROR_RATE_THRESHOLD == 0.2
    assert result.status != "failing"


def test_p95_exactly_at_threshold_is_not_slow():
    events = make_events(10, latency_ms=SLOW_P95_LATENCY_MS, status_code=200)
    result = classify_service(events, last_heartbeat=FRESH_HEARTBEAT, now=NOW)

    assert result.p95_latency_ms == SLOW_P95_LATENCY_MS
    assert result.status == "healthy"


def test_failing_takes_priority_over_slow():
    # High latency (would be "slow" alone) AND high error rate (would be
    # "failing" alone) on the same service -> failing wins.
    events = make_events(7, latency_ms=900, status_code=200) + make_events(3, latency_ms=900, status_code=500)
    result = classify_service(events, last_heartbeat=FRESH_HEARTBEAT, now=NOW)

    assert result.p95_latency_ms == 900
    assert result.error_rate == 0.3
    assert result.status == "failing"


def test_events_outside_window_are_ignored():
    old_events = make_events(5, latency_ms=999, status_code=500, start_offset=CLASSIFICATION_WINDOW_SECONDS + 10)
    result = classify_service(old_events, last_heartbeat=FRESH_HEARTBEAT, now=NOW)

    assert result.error_rate == 0.0
    assert result.p95_latency_ms is None
    assert result.status == "healthy"
