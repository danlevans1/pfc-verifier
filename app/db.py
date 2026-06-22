import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Optional

DB_PATH: str = os.environ.get("DATABASE_URL", "receipts.db")


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_id   TEXT PRIMARY KEY,
                receipt_json TEXT NOT NULL,
                created_at   TEXT NOT NULL
            )
        """)


def save_receipt(receipt: Dict[str, Any], created_at: str) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO receipts"
            " (receipt_id, receipt_json, created_at) VALUES (?, ?, ?)",
            (receipt["receiptId"], json.dumps(receipt), created_at),
        )


def fetch_receipt(receipt_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT receipt_json FROM receipts WHERE receipt_id = ?",
            (receipt_id,),
        ).fetchone()
    return json.loads(row["receipt_json"]) if row else None
