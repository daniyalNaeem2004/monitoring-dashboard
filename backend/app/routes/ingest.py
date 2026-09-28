from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import ANOMALY_BASELINE_WINDOW_SECONDS, ANOMALY_CURRENT_WINDOW_SECONDS
from app.database import get_db
from app.models import Anomaly, LogEntry, Metric, Service
from app.schemas import IngestRequest, IngestResponse
from app.services.anomaly import OpenAnomaly, detect_anomalies, reconcile_open_anomalies
from app.services.classification import MetricPoint

router = APIRouter()


def _update_anomalies_for_service(db: Session, service: Service, now: datetime) -> None:
    lookback_start = now - timedelta(seconds=ANOMALY_CURRENT_WINDOW_SECONDS + ANOMALY_BASELINE_WINDOW_SECONDS)
    rows = db.execute(
        select(Metric.timestamp, Metric.latency_ms, Metric.status_code).where(
            Metric.service_id == service.id, Metric.timestamp >= lookback_start
        )
    ).all()
    events = [MetricPoint(timestamp=r.timestamp, latency_ms=r.latency_ms, status_code=r.status_code) for r in rows]

    checks = detect_anomalies(events, now)
    if not checks:
        return

    existing_rows = (
        db.execute(select(Anomaly).where(Anomaly.service_id == service.id, Anomaly.resolved_at.is_(None)))
        .scalars()
        .all()
    )
    existing_row_by_metric = {row.metric: row for row in existing_rows}
    open_by_metric = {
        metric: OpenAnomaly(
            metric=metric, started_at=row.started_at, value=row.value, baseline_mean=row.baseline_mean, z_score=row.z_score
        )
        for metric, row in existing_row_by_metric.items()
    }

    updated = reconcile_open_anomalies(open_by_metric, checks, now)

    for metric, open_anomaly in updated.items():
        row = existing_row_by_metric.get(metric)
        if row is None:
            db.add(
                Anomaly(
                    service_id=service.id,
                    metric=metric,
                    value=open_anomaly.value,
                    baseline_mean=open_anomaly.baseline_mean,
                    z_score=open_anomaly.z_score,
                    started_at=open_anomaly.started_at,
                    resolved_at=open_anomaly.resolved_at,
                )
            )
        else:
            row.value = open_anomaly.value
            row.baseline_mean = open_anomaly.baseline_mean
            row.z_score = open_anomaly.z_score
            row.resolved_at = open_anomaly.resolved_at


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

    db.flush()

    now = datetime.now(timezone.utc)
    for service in services_by_name.values():
        _update_anomalies_for_service(db, service, now)

    db.commit()
    return IngestResponse(ingested=len(payload.events))
