"""Pure classification logic. No DB access and no wall-clock reads inside —
the caller supplies `now`, so a given (events, last_heartbeat, now) triple
always produces the same result. That's what makes this easy to unit test
without spinning up a database."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import NamedTuple

from app.config import (
    CLASSIFICATION_WINDOW_SECONDS,
    ERROR_STATUS_CODE_MIN,
    FAILING_ERROR_RATE_THRESHOLD,
    FAILING_HEARTBEAT_TIMEOUT_SECONDS,
    SLOW_P95_LATENCY_MS,
)
from app.services.stats import percentile

STATUS_HEALTHY = "healthy"
STATUS_SLOW = "slow"
STATUS_FAILING = "failing"


class MetricPoint(NamedTuple):
    timestamp: datetime
    latency_ms: float
    status_code: int


@dataclass(frozen=True)
class ClassificationResult:
    status: str
    error_rate: float
    p95_latency_ms: float | None
    seconds_since_heartbeat: float


def classify_service(
    events: Sequence[MetricPoint],
    last_heartbeat: datetime | None,
    now: datetime,
) -> ClassificationResult:
    window_start = now - timedelta(seconds=CLASSIFICATION_WINDOW_SECONDS)
    windowed = [e for e in events if e.timestamp >= window_start]

    error_count = sum(1 for e in windowed if e.status_code >= ERROR_STATUS_CODE_MIN)
    error_rate = (error_count / len(windowed)) if windowed else 0.0
    p95_latency_ms = percentile([e.latency_ms for e in windowed], 0.95) if windowed else None

    # No heartbeat ever recorded is treated as infinitely stale, so it always
    # trips the timeout check below rather than needing a separate branch.
    seconds_since_heartbeat = math.inf if last_heartbeat is None else (now - last_heartbeat).total_seconds()

    is_failing = (
        error_rate > FAILING_ERROR_RATE_THRESHOLD
        or seconds_since_heartbeat > FAILING_HEARTBEAT_TIMEOUT_SECONDS
    )

    if is_failing:
        status = STATUS_FAILING
    elif p95_latency_ms is not None and p95_latency_ms > SLOW_P95_LATENCY_MS:
        status = STATUS_SLOW
    else:
        status = STATUS_HEALTHY

    return ClassificationResult(
        status=status,
        error_rate=error_rate,
        p95_latency_ms=p95_latency_ms,
        seconds_since_heartbeat=seconds_since_heartbeat,
    )
