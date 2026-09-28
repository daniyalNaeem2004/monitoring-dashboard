import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


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
    model_config = ConfigDict(from_attributes=True)

    name: str
    status: str
    last_heartbeat: dt.datetime
