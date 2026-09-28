"""Tiny shared stats helpers used by both classification and anomaly detection."""

import math


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    idx = math.ceil(pct * len(ordered)) - 1
    idx = max(0, min(idx, len(ordered) - 1))
    return ordered[idx]
