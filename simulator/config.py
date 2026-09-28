import os

from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TICK_SECONDS = float(os.getenv("TICK_SECONDS", "1.5"))

SERVICES = ["auth", "payments", "orders", "search", "inventory"]

# Valid values: normal, latency_spike, error_burst, silent, slow_degradation
VALID_SCENARIOS = {"normal", "latency_spike", "error_burst", "silent", "slow_degradation"}


def scenario_for(service: str) -> str:
    value = os.getenv(f"SCENARIO_{service.upper()}", "normal").strip().lower()
    return value if value in VALID_SCENARIOS else "normal"
