import time
from typing import Any, Dict, Optional

import requests


class ApiClient:
    """Client HTTP minimal avec timeout, mesure de latence et retry simple."""

    def __init__(self, base_url: str, timeout: float = 3.0, max_retries: int = 1):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_error = None

        for attempt in range(self.max_retries + 1):
            started = time.perf_counter()
            try:
                response = requests.get(url, params=params, timeout=self.timeout)
                latency_ms = round((time.perf_counter() - started) * 1000, 2)

                content_type = response.headers.get("Content-Type", "")
                data = None
                if "json" in content_type.lower():
                    try:
                        data = response.json()
                    except ValueError:
                        data = None

                result = {
                    "url": response.url,
                    "status_code": response.status_code,
                    "content_type": content_type,
                    "json": data,
                    "latency_ms": latency_ms,
                    "attempt": attempt + 1,
                    "error": None,
                }

                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < self.max_retries:
                        time.sleep(0.5 * (attempt + 1))
                        continue

                return result

            except requests.RequestException as exc:
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                last_error = str(exc)
                if attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                return {
                    "url": url,
                    "status_code": None,
                    "content_type": "",
                    "json": None,
                    "latency_ms": latency_ms,
                    "attempt": attempt + 1,
                    "error": last_error,
                }

        return {
            "url": url,
            "status_code": None,
            "content_type": "",
            "json": None,
            "latency_ms": None,
            "attempt": self.max_retries + 1,
            "error": last_error or "Erreur inconnue",
        }
