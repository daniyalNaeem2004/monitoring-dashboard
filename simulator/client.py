import requests

from config import BACKEND_URL


def send_batch(events: list[dict]) -> None:
    try:
        resp = requests.post(f"{BACKEND_URL}/ingest", json={"events": events}, timeout=5)
        resp.raise_for_status()
        print(f"sent {len(events)} events -> {resp.json()}")
    except requests.RequestException as exc:
        print(f"failed to send batch of {len(events)} events: {exc}")
