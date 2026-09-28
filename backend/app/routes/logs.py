from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DEFAULT_LOGS_LIMIT, MAX_LOGS_LIMIT
from app.database import get_db
from app.models import LogEntry, Service
from app.schemas import LogEntryOut

router = APIRouter()


@router.get("/logs", response_model=list[LogEntryOut])
def list_logs(
    service: str | None = None,
    level: str | None = None,
    limit: int = Query(DEFAULT_LOGS_LIMIT, gt=0, le=MAX_LOGS_LIMIT),
    db: Session = Depends(get_db),
) -> list[LogEntryOut]:
    query = select(LogEntry, Service.name).join(Service, LogEntry.service_id == Service.id)

    if service is not None:
        query = query.where(Service.name == service)
    if level is not None:
        query = query.where(LogEntry.level == level.upper())

    rows = db.execute(query.order_by(LogEntry.timestamp.desc()).limit(limit)).all()

    return [
        LogEntryOut(service=service_name, timestamp=entry.timestamp, level=entry.level, message=entry.message)
        for entry, service_name in rows
    ]
