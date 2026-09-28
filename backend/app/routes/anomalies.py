from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Anomaly, Service
from app.schemas import AnomalyOut

router = APIRouter()


@router.get("/anomalies", response_model=list[AnomalyOut])
def list_anomalies(db: Session = Depends(get_db)) -> list[AnomalyOut]:
    rows = db.execute(
        select(Anomaly, Service.name)
        .join(Service, Anomaly.service_id == Service.id)
        .order_by(Anomaly.started_at.desc())
    ).all()

    return [
        AnomalyOut(
            service=service_name,
            metric=anomaly.metric,
            value=anomaly.value,
            baseline_mean=anomaly.baseline_mean,
            z_score=anomaly.z_score,
            started_at=anomaly.started_at,
            resolved_at=anomaly.resolved_at,
        )
        for anomaly, service_name in rows
    ]
