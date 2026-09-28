import datetime as dt

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Service(Base):
    """One row per known microservice. `status` is a cached snapshot of the
    latest classification (step 3 computes it); this table is the source of
    truth for GET /services."""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="healthy")
    last_heartbeat: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    metrics: Mapped[list["Metric"]] = relationship(back_populates="service", cascade="all, delete-orphan")
    logs: Mapped[list["LogEntry"]] = relationship(back_populates="service", cascade="all, delete-orphan")
    anomalies: Mapped[list["Anomaly"]] = relationship(back_populates="service", cascade="all, delete-orphan")


class Metric(Base):
    """A single latency/status-code data point from an ingested event."""

    __tablename__ = "metrics"
    __table_args__ = (Index("ix_metrics_service_timestamp", "service_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[float] = mapped_column(Float)
    status_code: Mapped[int] = mapped_column(Integer)

    service: Mapped["Service"] = relationship(back_populates="metrics")


class LogEntry(Base):
    """A single log line from an ingested event."""

    __tablename__ = "log_entries"
    __table_args__ = (Index("ix_log_entries_service_timestamp", "service_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    timestamp: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    level: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(2000))

    service: Mapped["Service"] = relationship(back_populates="logs")


class Anomaly(Base):
    """One row per ongoing incident, not per detection tick: while a
    (service, metric) pair keeps failing its z-score check, later ticks
    update this same row's value/z_score instead of inserting a new one.
    `resolved_at` is set the first tick the check comes back clean."""

    __tablename__ = "anomalies"
    __table_args__ = (Index("ix_anomalies_service_metric_open", "service_id", "metric", "resolved_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    metric: Mapped[str] = mapped_column(String(50))  # e.g. "latency_p95", "error_rate"
    value: Mapped[float] = mapped_column(Float)
    baseline_mean: Mapped[float] = mapped_column(Float)
    z_score: Mapped[float] = mapped_column(Float)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    service: Mapped["Service"] = relationship(back_populates="anomalies")
