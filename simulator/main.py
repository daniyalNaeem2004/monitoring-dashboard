import random
import time
from datetime import datetime, timezone

from client import send_batch
from config import BACKEND_URL, SERVICES, TICK_SECONDS, scenario_for
from scenarios import generate_event

EVENTS_PER_TICK = (1, 3)  # min, max fake requests per service per tick


def build_batch() -> list[dict]:
    now = datetime.now(timezone.utc)
    events = []
    for service in SERVICES:
        scenario = scenario_for(service)
        for _ in range(random.randint(*EVENTS_PER_TICK)):
            sample = generate_event(service, scenario, now)
            if sample is None:
                continue  # silent scenario: emit no heartbeat this tick
            latency_ms, status_code, level, message = sample
            events.append(
                {
                    "service": service,
                    "timestamp": now.isoformat(),
                    "latency_ms": latency_ms,
                    "status_code": status_code,
                    "level": level,
                    "message": message,
                }
            )
    return events


def main() -> None:
    print(f"Simulator -> {BACKEND_URL} every {TICK_SECONDS}s")
    for service in SERVICES:
        print(f"  {service}: scenario={scenario_for(service)}")

    while True:
        batch = build_batch()
        if batch:
            send_batch(batch)
        time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    main()
