from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Env-driven app settings. Load once as a module-level singleton (see `settings` below)."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://monitor:monitor@localhost:5432/monitoring"


settings = Settings()


# --- Classification & anomaly thresholds ---
# Single source of truth per CLAUDE.md: nothing below should be hard-coded
# elsewhere. Values are used starting in step 3 (classification logic) and
# step 4 (anomaly detection), but live here now so future code just imports
# them instead of inventing numbers inline.

CLASSIFICATION_WINDOW_SECONDS = 60
FAILING_ERROR_RATE_THRESHOLD = 0.20  # >20% error rate in window => failing
FAILING_HEARTBEAT_TIMEOUT_SECONDS = 30  # no events for 30s => failing
SLOW_P95_LATENCY_MS = 500  # p95 latency above this => slow
ERROR_STATUS_CODE_MIN = 500  # only 5xx counts as an "error" for error-rate purposes (a 404 is a client mistake, not a service failure)

ANOMALY_ZSCORE_THRESHOLD = 3.0  # flag when metric exceeds baseline mean + 3 * stddev
