from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
OUTPUT_DIR = DATA_DIR / "output"

for d in (RAW_DIR, INTERMEDIATE_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)


class StorageService:
    def new_receipt_id(self) -> str:
        return f"receipt-{uuid4().hex[:12]}"

    async def save_upload(self, file: UploadFile, receipt_id: str) -> Path:
        suffix = Path(file.filename or "receipt.jpg").suffix or ".jpg"
        dst = RAW_DIR / f"{receipt_id}{suffix.lower()}"
        dst.write_bytes(await file.read())
        return dst

    def save_json(self, payload: dict, filename: str) -> Path:
        dst = INTERMEDIATE_DIR / filename
        dst.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return dst

    def save_pdf(self, receipt_id: str, pdf_bytes: bytes) -> Path:
        dst = OUTPUT_DIR / f"audit_report_{receipt_id}.pdf"
        dst.write_bytes(pdf_bytes)
        return dst
