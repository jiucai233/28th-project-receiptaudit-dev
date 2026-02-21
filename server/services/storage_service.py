from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
OUTPUT_DIR = DATA_DIR / "output"

for d in (RAW_DIR, INTERMEDIATE_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)


class StorageService:
    def __init__(self):
        self.aws_region = os.getenv("AWS_REGION", "").strip()
        self.bucket_name = os.getenv("AWS_S3_BUCKET_NAME", "").strip()
        self._s3_client = None

        if self.aws_region and self.bucket_name:
            self._s3_client = boto3.client("s3", region_name=self.aws_region)

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

    def upload_image_to_s3(
        self,
        receipt_id: str,
        image_bytes: bytes,
        suffix: str,
        content_type: str | None = None,
    ) -> tuple[str, str] | None:
        if not self._s3_client:
            return None

        suffix = suffix if suffix.startswith(".") else f".{suffix}"
        key = f"receipts/{receipt_id}{suffix.lower()}"
        return self._upload_bytes(key, image_bytes, content_type or "application/octet-stream")

    def upload_pdf_to_s3(self, receipt_id: str, pdf_bytes: bytes) -> tuple[str, str] | None:
        if not self._s3_client:
            return None

        key = f"reports/audit_report_{receipt_id}.pdf"
        return self._upload_bytes(key, pdf_bytes, "application/pdf")

    def _upload_bytes(
        self, key: str, data: bytes, content_type: str
    ) -> tuple[str, str] | None:
        if not self._s3_client or not self.bucket_name:
            return None

        try:
            self._s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            url = f"https://{self.bucket_name}.s3.{self.aws_region}.amazonaws.com/{key}"
            return key, url
        except (ClientError, BotoCoreError):
            return None
