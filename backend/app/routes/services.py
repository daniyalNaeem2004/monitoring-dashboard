from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import CLASSIFICATION_WINDOW_SECONDS
from app.database import get_db
from app.models import Metric, Service
from app.schemas import ServiceOut
from app.services.classification import MetricPoint, classify_service

router = APIRouter()


@router.get("/services", response_model=list[ServiceOut])
def list_services(db: Session = Depends(get_db)) -> list[ServiceOut]:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=CLASSIFICATION_WINDOW_SECONDS)

    services = db.execute(select(Service).order_by(Service.name)).scalars().all()

    out: list[ServiceOut] = []
    for service in services:
        rows = db.execute(
            select(Metric.timestamp, Metric.latency_ms, Metric.status_code).where(
                Metric.service_id == service.id, Metric.timestamp >= window_start
            )
        ).all()
        events = [MetricPoint(timestamp=r.timestamp, latency_ms=r.latency_ms, status_code=r.status_code) for r in rows]
        result = classify_service(events, last_heartbeat=service.last_heartbeat, now=now)

        out.append(
            ServiceOut(
                name=service.name,
                status=result.status,
                last_heartbeat=service.last_heartbeat,
                error_rate=result.error_rate,
                p95_latency_ms=result.p95_latency_ms,
                seconds_since_heartbeat=result.seconds_since_heartbeat,
            )
        )

    return out
