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
