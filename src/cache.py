import json
import time
from pathlib import Path


class Cache:
    def __init__(self, directory="data/cache"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def path(self, name):
        return self.directory / f"{name}.json"

    def save(self, name, data):
        payload = {
            "timestamp": time.time(),
            "data": data
        }

        with open(self.path(name), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def load(self, name, max_age_seconds=None):
        path = self.path(name)

        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            timestamp = payload.get("timestamp", 0)

            if (
                max_age_seconds is not None
                and time.time() - timestamp > max_age_seconds
            ):
                return None

            return payload.get("data")

        except (OSError, json.JSONDecodeError):
            return None