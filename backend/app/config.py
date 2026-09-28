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
ANOMALY_CURRENT_WINDOW_SECONDS = 30  # "now" window compared against the baseline
ANOMALY_BASELINE_WINDOW_SECONDS = 600  # 10 minutes of history feeds the baseline
ANOMALY_BASELINE_BUCKET_SECONDS = 30  # baseline is sliced into windows this wide (same size as the current window) so mean/stddev describe per-window values, not raw events
ANOMALY_MIN_BASELINE_BUCKETS = 5  # require at least this many non-empty baseline buckets before trusting mean/stddev
ANOMALY_LATENCY_SIGMA_FLOOR_MS = 10.0  # stddev floor so a near-zero-variance baseline doesn't trip on tiny latency noise
ANOMALY_ERROR_RATE_SIGMA_FLOOR = 0.01  # stddev floor so an all-zero error-rate baseline doesn't trip on a single error

# --- Read API defaults ---
DEFAULT_METRICS_RANGE_SECONDS = 300  # GET /services/{name}/metrics default lookback
DEFAULT_LOGS_LIMIT = 50  # GET /logs default row count
MAX_LOGS_LIMIT = 500

# --- CORS ---
# Portfolio project, no auth/cookies in play, so a wide-open dev origin list is fine.
CORS_ALLOW_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
