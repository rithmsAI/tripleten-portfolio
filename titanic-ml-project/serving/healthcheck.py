"""Docker readiness probe using only the Python standard library."""

import json
import sys
from urllib.error import URLError
from urllib.request import urlopen


def is_healthy(url="http://127.0.0.1:8000/health"):
    """Require a successful response and a loaded model within two seconds."""
    try:
        with urlopen(url, timeout=2) as response:
            payload = json.load(response)
            return (
                response.status == 200
                and isinstance(payload, dict)
                and payload.get("status") == "healthy"
                and payload.get("model_loaded") is True
            )
    except (URLError, OSError, ValueError):
        return False


if __name__ == "__main__":
    if is_healthy():
        sys.exit(0)
    print("API is unavailable or its model is not ready.", file=sys.stderr)
    sys.exit(1)
