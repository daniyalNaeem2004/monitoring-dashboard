from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import CLASSIFICATION_WINDOW_SECONDS, DEFAULT_METRICS_RANGE_SECONDS
from app.database import get_db
from app.models import Metric, Service
from app.schemas import MetricPointOut, ServiceOut
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


@router.get("/services/{name}/metrics", response_model=list[MetricPointOut])
def get_service_metrics(
    name: str,
    range_seconds: int = Query(DEFAULT_METRICS_RANGE_SECONDS, alias="range", gt=0),
    db: Session = Depends(get_db),
) -> list[MetricPointOut]:
    service = db.execute(select(Service).where(Service.name == name)).scalar_one_or_none()
    if service is None:
        raise HTTPException(status_code=404, detail=f"Unknown service: {name}")

    window_start = datetime.now(timezone.utc) - timedelta(seconds=range_seconds)
    rows = db.execute(
        select(Metric.timestamp, Metric.latency_ms, Metric.status_code)
        .where(Metric.service_id == service.id, Metric.timestamp >= window_start)
        .order_by(Metric.timestamp)
    ).all()

    return [MetricPointOut(timestamp=r.timestamp, latency_ms=r.latency_ms, status_code=r.status_code) for r in rows]
