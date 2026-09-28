from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LogEntry, Metric, Service
from app.schemas import IngestRequest, IngestResponse

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
def ingest_events(payload: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:
    # Cache Service lookups within this batch so repeated names don't hit the DB twice.
    services_by_name: dict[str, Service] = {}

    for event in payload.events:
        service = services_by_name.get(event.service)
        if service is None:
            service = db.query(Service).filter(Service.name == event.service).one_or_none()
            if service is None:
                service = Service(name=event.service, last_heartbeat=event.timestamp)
                db.add(service)
                db.flush()  # assign service.id before it's used as a FK below
            services_by_name[event.service] = service

        if event.timestamp > service.last_heartbeat:
            service.last_heartbeat = event.timestamp

        db.add(
            Metric(
                service_id=service.id,
                timestamp=event.timestamp,
                latency_ms=event.latency_ms,
                status_code=event.status_code,
            )
        )
        db.add(
            LogEntry(
                service_id=service.id,
                timestamp=event.timestamp,
                level=event.level,
                message=event.message,
            )
        )

    db.commit()
    return IngestResponse(ingested=len(payload.events))
