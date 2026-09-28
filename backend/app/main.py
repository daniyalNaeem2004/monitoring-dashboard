from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ALLOW_ORIGINS
from app.database import Base, engine
from app.routes import anomalies, ingest, logs, services

app = FastAPI(title="Monitoring Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Step 1: create tables directly from models on startup. Swap for Alembic
# migrations once the schema needs to evolve without dropping data.
Base.metadata.create_all(bind=engine)

app.include_router(ingest.router)
app.include_router(services.router)
app.include_router(anomalies.router)
app.include_router(logs.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
