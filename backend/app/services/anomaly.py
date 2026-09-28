"""Pure anomaly-detection logic: rolling z-score of per-window p95 latency and
error rate against a bucketed baseline. Like classification.py, no DB access
and no wall-clock reads inside, so (events, now) always produces the same
result and this is unit-testable without a database.

Rolling z-score has a known blind spot for `slow_degradation`: if latency
creeps up gradually, the trailing baseline drifts upward right along with the
current window, so the gap between them never crosses the z-score threshold.
The simplest fix — applied below for latency only — is to also flag the
absolute SLOW_P95_LATENCY_MS threshold regardless of z-score, since a slow
drift eventually crosses that fixed line even though it never spikes fast
enough to beat its own moving baseline.
"""

import statistics
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from app.config import (
    ANOMALY_BASELINE_BUCKET_SECONDS,
    ANOMALY_BASELINE_WINDOW_SECONDS,
    ANOMALY_CURRENT_WINDOW_SECONDS,
    ANOMALY_ERROR_RATE_SIGMA_FLOOR,
    ANOMALY_LATENCY_SIGMA_FLOOR_MS,
    ANOMALY_MIN_BASELINE_BUCKETS,
    ANOMALY_ZSCORE_THRESHOLD,
    ERROR_STATUS_CODE_MIN,
    SLOW_P95_LATENCY_MS,
)
from app.services.classification import MetricPoint
from app.services.stats import percentile

METRIC_LATENCY_P95 = "latency_p95"
METRIC_ERROR_RATE = "error_rate"


@dataclass(frozen=True)
class AnomalyCheck:
    metric: str
    value: float
    baseline_mean: float
    z_score: float
    is_anomalous: bool


@dataclass(frozen=True)
class OpenAnomaly:
    """In-memory mirror of one unresolved `Anomaly` row for a (service, metric)."""

    metric: str
    started_at: datetime
    value: float
    baseline_mean: float
    z_score: float
    resolved_at: datetime | None = None


def _error_rate(points: Sequence[MetricPoint]) -> float:
    if not points:
        return 0.0
    errors = sum(1 for p in points if p.status_code >= ERROR_STATUS_CODE_MIN)
    return errors / len(points)


def _bucket_baseline(points: Sequence[MetricPoint], current_start: datetime) -> list[list[MetricPoint]]:
    """Split baseline-window points into fixed-width buckets, oldest last,
    so each bucket's aggregate (p95 / error rate) becomes one baseline sample."""
    num_buckets = ANOMALY_BASELINE_WINDOW_SECONDS // ANOMALY_BASELINE_BUCKET_SECONDS
    buckets: list[list[MetricPoint]] = [[] for _ in range(num_buckets)]
    for p in points:
        age = (current_start - p.timestamp).total_seconds()
        idx = int(age // ANOMALY_BASELINE_BUCKET_SECONDS)
        if 0 <= idx < num_buckets:
            buckets[idx].append(p)
    return buckets


def _check_metric(
    metric: str,
    current_value: float,
    baseline_values: list[float],
    sigma_floor: float,
    absolute_threshold: float | None = None,
) -> AnomalyCheck:
    mean = statistics.mean(baseline_values)
    stddev = statistics.pstdev(baseline_values) if len(baseline_values) > 1 else 0.0
    stddev = max(stddev, sigma_floor)
    z_score = (current_value - mean) / stddev

    is_anomalous = z_score > ANOMALY_ZSCORE_THRESHOLD
    if absolute_threshold is not None:
        is_anomalous = is_anomalous or current_value > absolute_threshold

    return AnomalyCheck(metric=metric, value=current_value, baseline_mean=mean, z_score=z_score, is_anomalous=is_anomalous)


def detect_anomalies(events: Sequence[MetricPoint], now: datetime) -> list[AnomalyCheck]:
    """One check per metric, or none at all if there isn't enough data to
    trust a comparison: an empty current window, or fewer non-empty baseline
    buckets than ANOMALY_MIN_BASELINE_BUCKETS requires."""
    current_start = now - timedelta(seconds=ANOMALY_CURRENT_WINDOW_SECONDS)
    baseline_start = current_start - timedelta(seconds=ANOMALY_BASELINE_WINDOW_SECONDS)

    current = [e for e in events if e.timestamp >= current_start]
    baseline = [e for e in events if baseline_start <= e.timestamp < current_start]

    buckets = [b for b in _bucket_baseline(baseline, current_start) if b]
    if not current or len(buckets) < ANOMALY_MIN_BASELINE_BUCKETS:
        return []

    latency_baseline = [percentile([p.latency_ms for p in b], 0.95) for b in buckets]
    current_latency = percentile([e.latency_ms for e in current], 0.95)
    latency_check = _check_metric(
        METRIC_LATENCY_P95,
        current_latency,
        latency_baseline,
        ANOMALY_LATENCY_SIGMA_FLOOR_MS,
        absolute_threshold=SLOW_P95_LATENCY_MS,
    )

    error_baseline = [_error_rate(b) for b in buckets]
    current_error = _error_rate(current)
    error_check = _check_metric(METRIC_ERROR_RATE, current_error, error_baseline, ANOMALY_ERROR_RATE_SIGMA_FLOOR)

    return [latency_check, error_check]


def reconcile_open_anomalies(
    open_by_metric: dict[str, OpenAnomaly],
    checks: Sequence[AnomalyCheck],
    now: datetime,
) -> dict[str, OpenAnomaly]:
    """Dedupe rule: one ongoing incident per metric is one record. A new
    anomalous check with no open (or an already-resolved) incident starts
    one; an anomalous check with an open incident just refreshes its latest
    value/z-score in place; a non-anomalous check resolves an open incident."""
    result = dict(open_by_metric)

    for check in checks:
        existing = result.get(check.metric)
        if check.is_anomalous:
            if existing is None or existing.resolved_at is not None:
                result[check.metric] = OpenAnomaly(
                    metric=check.metric,
                    started_at=now,
                    value=check.value,
                    baseline_mean=check.baseline_mean,
                    z_score=check.z_score,
                )
            else:
                result[check.metric] = replace(
                    existing, value=check.value, baseline_mean=check.baseline_mean, z_score=check.z_score
                )
        elif existing is not None and existing.resolved_at is None:
            result[check.metric] = replace(existing, resolved_at=now)

    return result
