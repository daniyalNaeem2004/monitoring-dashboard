import random
import time
from datetime import datetime

EventSample = tuple[float, int, str, str]  # latency_ms, status_code, level, message

NORMAL_STATUS_WEIGHTS = {200: 0.94, 400: 0.02, 404: 0.02, 500: 0.01, 503: 0.01}
ERROR_BURST_STATUS_WEIGHTS = {200: 0.25, 500: 0.45, 503: 0.30}
SPIKE_STATUS_WEIGHTS = {200: 0.85, 504: 0.10, 500: 0.05}

SLOW_DEGRADATION_RAMP_SECONDS = 45.0
SLOW_DEGRADATION_PEAK_MS = 650.0

MESSAGES = {
    "INFO": ["request completed", "cache hit", "processed successfully", "handled request"],
    "WARN": ["slow downstream call", "retrying request", "deprecated endpoint used", "elevated latency observed"],
    "ERROR": ["internal server error", "downstream timeout", "unhandled exception", "dependency unavailable"],
}

# (service, scenario) -> monotonic start time, so a ramp resets whenever the
# scenario for a service changes (including switching back to "normal").
_scenario_state: dict[str, tuple[str, float]] = {}


def _weighted_status(weights: dict[int, float]) -> int:
    return random.choices(list(weights.keys()), weights=list(weights.values()))[0]


def _level_for_status(status: int) -> str:
    if status < 400:
        return random.choices(["INFO", "WARN"], weights=[0.9, 0.1])[0]
    if status < 500:
        return random.choices(["WARN", "ERROR"], weights=[0.8, 0.2])[0]
    return "ERROR"


def _message_for(service: str, level: str) -> str:
    return f"{service}: {random.choice(MESSAGES[level])}"


def _normal_latency() -> float:
    base = random.uniform(50, 200)
    if random.random() < 0.05:  # occasional realistic tail
        base += random.uniform(100, 300)
    return round(base, 1)


def _spike_latency() -> float:
    return round(random.uniform(800, 3000), 1)


def _elapsed_seconds(service: str, scenario: str) -> float:
    now = time.monotonic()
    state = _scenario_state.get(service)
    if state is None or state[0] != scenario:
        _scenario_state[service] = (scenario, now)
        return 0.0
    return now - state[1]


def _degraded_latency(elapsed: float) -> float:
    base = random.uniform(50, 200)
    ramp_fraction = min(elapsed / SLOW_DEGRADATION_RAMP_SECONDS, 1.0)
    extra = ramp_fraction * (SLOW_DEGRADATION_PEAK_MS - 125)
    return round(base + extra, 1)


def generate_event(service: str, scenario: str, now: datetime) -> EventSample | None:
    """Return (latency_ms, status_code, level, message) for one fake request,
    or None if the service should emit nothing this tick (silent scenario)."""

    # Track elapsed time in the *current* scenario regardless of which one it
    # is, so a ramp correctly restarts from 0 if slow_degradation is toggled
    # off and back on later (rather than resuming from a stale start time).
    elapsed = _elapsed_seconds(service, scenario)

    if scenario == "silent":
        return None

    if scenario == "latency_spike":
        latency = _spike_latency()
        status = _weighted_status(SPIKE_STATUS_WEIGHTS)
    elif scenario == "error_burst":
        latency = _normal_latency()
        status = _weighted_status(ERROR_BURST_STATUS_WEIGHTS)
    elif scenario == "slow_degradation":
        latency = _degraded_latency(elapsed)
        status = _weighted_status(NORMAL_STATUS_WEIGHTS)
    else:  # normal
        latency = _normal_latency()
        status = _weighted_status(NORMAL_STATUS_WEIGHTS)

    level = _level_for_status(status)
    message = _message_for(service, level)
    return latency, status, level, message
