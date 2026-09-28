import datetime as dt

from pydantic import BaseModel, Field


class EventIn(BaseModel):
    """One event as emitted by the simulator / any producer."""

    service: str
    timestamp: dt.datetime
    latency_ms: float = Field(ge=0)
    status_code: int = Field(ge=100, le=599)
    level: str
    message: str


class IngestRequest(BaseModel):
    events: list[EventIn]


class IngestResponse(BaseModel):
    ingested: int


class ServiceOut(BaseModel):
    """Current status plus the numbers that produced it, computed live from
    recent events on every request (not read from a stale column)."""

    name: str
    status: str
    last_heartbeat: dt.datetime
    error_rate: float
    p95_latency_ms: float | None
    seconds_since_heartbeat: float


class MetricPointOut(BaseModel):
    """One raw latency/status-code data point, for the per-service latency chart."""

    timestamp: dt.datetime
    latency_ms: float
    status_code: int


class LogEntryOut(BaseModel):
    service: str
    timestamp: dt.datetime
    level: str
    message: str


class AnomalyOut(BaseModel):
    """One ongoing or past incident. `resolved_at` is None while it's still open."""

    service: str
    metric: str
    value: float
    baseline_mean: float
    z_score: float
    started_at: dt.datetime
    resolved_at: dt.datetime | None
