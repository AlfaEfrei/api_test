import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(os.environ.get("RUNS_DB_PATH", Path(__file__).with_name("runs.sqlite3")))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                passed INTEGER NOT NULL,
                failed INTEGER NOT NULL,
                error_rate REAL NOT NULL,
                latency_ms_avg REAL,
                latency_ms_p95 REAL,
                availability REAL NOT NULL,
                summary_json TEXT NOT NULL,
                tests_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_run(result: Dict[str, Any]) -> int:
    summary = result["summary"]
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO runs (
                api, timestamp, status, passed, failed, error_rate,
                latency_ms_avg, latency_ms_p95, availability, summary_json, tests_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result["api"],
                result["timestamp"],
                result["status"],
                summary["passed"],
                summary["failed"],
                summary["error_rate"],
                summary["latency_ms_avg"],
                summary["latency_ms_p95"],
                summary["availability"],
                json.dumps(summary, ensure_ascii=False),
                json.dumps(result["tests"], ensure_ascii=False),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "api": row["api"],
        "timestamp": row["timestamp"],
        "status": row["status"],
        "summary": json.loads(row["summary_json"]),
        "tests": json.loads(row["tests_json"]),
    }


def list_runs(limit: int = 20) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_last_run() -> Optional[Dict[str, Any]]:
    runs = list_runs(limit=1)
    return runs[0] if runs else None
