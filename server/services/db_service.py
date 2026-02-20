from __future__ import annotations

import os
import json
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor


class DBService:
    def __init__(self, dsn: str | None = None):
        # Example:
        # postgresql://username:password@host:5432/dbname
        self.dsn = dsn or os.getenv("DATABASE_URL", "").strip()
        if not self.dsn:
            raise ValueError("DATABASE_URL is required for PostgreSQL DBService")

    def _conn(self):
        return psycopg2.connect(self.dsn, cursor_factory=RealDictCursor)

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def init_db(self) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                """
                CREATE TABLE IF NOT EXISTS receipts (
                    receipt_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    image_path TEXT,
                    image_blob BYTEA,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audits (
                    receipt_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    FOREIGN KEY(receipt_id) REFERENCES receipts(receipt_id)
                );

                CREATE TABLE IF NOT EXISTS reports (
                    receipt_id TEXT PRIMARY KEY,
                    pdf_path TEXT NOT NULL,
                    pdf_blob BYTEA,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    FOREIGN KEY(receipt_id) REFERENCES receipts(receipt_id)
                );
                """
                )
            # Backward-compatible migration for existing PostgreSQL tables.
            self._ensure_column(conn, "receipts", "image_blob", "BYTEA")
            self._ensure_column(conn, "reports", "pdf_blob", "BYTEA")

    def _ensure_column(
        self, conn, table: str, column: str, column_type: str
    ) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
                """,
                (table, column),
            )
            if cur.fetchone() is None:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    def _ensure(self) -> None:
        self.init_db()

    def upsert_receipt(
        self,
        receipt_id: str,
        payload: dict,
        image_path: str,
        image_blob: bytes | None = None,
    ) -> None:
        self._ensure()
        now = self._now()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                """
                INSERT INTO receipts (
                    receipt_id, payload_json, image_path, image_blob, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(receipt_id) DO UPDATE SET
                    payload_json=EXCLUDED.payload_json,
                    image_path=EXCLUDED.image_path,
                    image_blob=EXCLUDED.image_blob,
                    updated_at=EXCLUDED.updated_at
                """,
                (
                    receipt_id,
                    json.dumps(payload, ensure_ascii=False),
                    image_path,
                    image_blob,
                    now,
                    now,
                ),
            )

    def upsert_audit(self, receipt_id: str, payload: dict) -> None:
        self._ensure()
        now = self._now()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                """
                INSERT INTO audits (receipt_id, payload_json, created_at, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT(receipt_id) DO UPDATE SET
                    payload_json=EXCLUDED.payload_json,
                    updated_at=EXCLUDED.updated_at
                """,
                (receipt_id, json.dumps(payload, ensure_ascii=False), now, now),
            )

    def upsert_report(
        self,
        receipt_id: str,
        pdf_path: str,
        payload: dict,
        pdf_blob: bytes | None = None,
    ) -> None:
        self._ensure()
        now = self._now()
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                """
                INSERT INTO reports (
                    receipt_id, pdf_path, pdf_blob, payload_json, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT(receipt_id) DO UPDATE SET
                    pdf_path=EXCLUDED.pdf_path,
                    pdf_blob=EXCLUDED.pdf_blob,
                    payload_json=EXCLUDED.payload_json,
                    updated_at=EXCLUDED.updated_at
                """,
                (
                    receipt_id,
                    pdf_path,
                    pdf_blob,
                    json.dumps(payload, ensure_ascii=False),
                    now,
                    now,
                ),
            )
