from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ALLOW_ORIGINS
from app.routes import anomalies, ingest, logs, services

app = FastAPI(title="Monitoring Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def run_migrations() -> None:
    """Bring the schema up to head on startup, so a database that predates a
    newer column/table never gets an app instance running against it (the bug
    that motivated switching off `Base.metadata.create_all`)."""
    backend_dir = Path(__file__).resolve().parent.parent
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(alembic_cfg, "head")


run_migrations()

app.include_router(ingest.router)
app.include_router(services.router)
app.include_router(anomalies.router)
app.include_router(logs.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
