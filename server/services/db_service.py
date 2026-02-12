from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "intermediate" / "transparent_audit.db"


class DBService:
    def __init__(self, db_path: Path | None = None):
        self.db_path = str(db_path or DB_PATH)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _now(self) -> str:
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"

    def init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS receipts (
                    receipt_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    image_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audits (
                    receipt_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(receipt_id) REFERENCES receipts(receipt_id)
                );

                CREATE TABLE IF NOT EXISTS reports (
                    receipt_id TEXT PRIMARY KEY,
                    pdf_path TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(receipt_id) REFERENCES receipts(receipt_id)
                );
                """
            )

    def _ensure(self) -> None:
        self.init_db()

    def upsert_receipt(self, receipt_id: str, payload: dict, image_path: str) -> None:
        self._ensure()
        now = self._now()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO receipts (receipt_id, payload_json, image_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(receipt_id) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    image_path=excluded.image_path,
                    updated_at=excluded.updated_at
                """,
                (receipt_id, json.dumps(payload, ensure_ascii=False), image_path, now, now),
            )

    def upsert_audit(self, receipt_id: str, payload: dict) -> None:
        self._ensure()
        now = self._now()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO audits (receipt_id, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(receipt_id) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (receipt_id, json.dumps(payload, ensure_ascii=False), now, now),
            )

    def upsert_report(self, receipt_id: str, pdf_path: str, payload: dict) -> None:
        self._ensure()
        now = self._now()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO reports (receipt_id, pdf_path, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(receipt_id) DO UPDATE SET
                    pdf_path=excluded.pdf_path,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (receipt_id, pdf_path, json.dumps(payload, ensure_ascii=False), now, now),
            )
