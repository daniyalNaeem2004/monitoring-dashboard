from fastapi import FastAPI

from app.database import Base, engine
from app.routes import ingest, services

app = FastAPI(title="Monitoring Dashboard API")

# Step 1: create tables directly from models on startup. Swap for Alembic
# migrations once the schema needs to evolve without dropping data.
Base.metadata.create_all(bind=engine)

app.include_router(ingest.router)
app.include_router(services.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
