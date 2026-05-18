import math
from datetime import datetime, timezone
from typing import Any, Dict, List

from tester.client import ApiClient
from tester.tests import TESTS, TestResult

API_NAME = "Frankfurter"
BASE_URL = "https://api.frankfurter.dev/v2"


def _percentile(values: List[float], percentile: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = max(0, math.ceil((percentile / 100) * len(values)) - 1)
    return round(values[index], 2)


def run_all_tests() -> Dict[str, Any]:
    client = ApiClient(BASE_URL, timeout=3.0, max_retries=1)
    results: List[TestResult] = []

    for test in TESTS:
        try:
            results.append(test(client))
        except Exception as exc:  # protection pour que le run ne casse pas complètement
            results.append(TestResult(
                name=getattr(test, "__name__", "test inconnu"),
                status="FAIL",
                latency_ms=None,
                details=f"Exception non gérée: {exc}",
                status_code=None,
            ))

    tests = [result.to_dict() for result in results]
    passed = sum(1 for result in results if result.passed)
    total = len(results)
    failed = total - passed
    latencies = [result.latency_ms for result in results if result.latency_ms is not None]

    summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "error_rate": round(failed / total, 3) if total else 0,
        "availability": round(passed / total, 3) if total else 0,
        "latency_ms_avg": round(sum(latencies) / len(latencies), 2) if latencies else 0,
        "latency_ms_p95": _percentile(latencies, 95),
    }

    return {
        "api": API_NAME,
        "base_url": BASE_URL,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if failed == 0 else "FAIL",
        "summary": summary,
        "tests": tests,
    }
