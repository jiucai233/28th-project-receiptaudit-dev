from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from core.audit_agent.reasoning import AuditReasoning

from server.services import DBService, OCRService, StorageService

import logging

router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/bmp", "image/webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

ocr_service = OCRService()
storage_service = StorageService()
db_service = DBService()


class ReceiptItem(BaseModel):
    id: int
    name: str
    unit_price: int = Field(ge=0)
    count: int = Field(ge=1)
    price: int = Field(ge=0)


class OCRExtractResponse(BaseModel):
    receipt_id: str
    store_name: str
    date: str
    items: list[ReceiptItem]
    total_price: int = Field(ge=0)
    image_url: str | None = None


@router.get("/extract")
async def extract_debug():
    return {"message": "OCR extract endpoint is active. Please use POST with an image file."}


@router.post("/extract", response_model=OCRExtractResponse)
async def extract(file: UploadFile = File(...)) -> OCRExtractResponse:
    logger.info(f"Received OCR extraction request for file: {file.filename}")
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        logger.error(f"Unsupported image type: {file.content_type}")
        raise HTTPException(status_code=400, detail="Unsupported image type")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        logger.error(f"File too large: {len(content)} bytes")
        raise HTTPException(status_code=413, detail="File too large")

    try:
        await file.seek(0)
        receipt_id = storage_service.new_receipt_id()
        logger.info(f"Assigned receipt_id: {receipt_id}")
        image_path = await storage_service.save_upload(file, receipt_id)
        suffix = Path(file.filename or "receipt.jpg").suffix or ".jpg"
        s3_result = storage_service.upload_image_to_s3(
            receipt_id=receipt_id,
            image_bytes=content,
            suffix=suffix,
            content_type=file.content_type,
        )
        image_s3_key = s3_result[0] if s3_result else None
        image_s3_url = s3_result[1] if s3_result else None

        # Call OCR service
        receipt = ocr_service.extract(image_path, receipt_id)

        # Proofread OCR results using LLM
        agent = AuditReasoning()
        receipt = agent.correct_receipt(receipt)
        
        # Add image_url for frontend preview
        receipt["image_url"] = image_s3_url or f"/data/raw/{image_path.name}"
        
        storage_service.save_json(receipt, f"{receipt_id}_ocr.json")
        db_service.upsert_receipt(
            receipt_id,
            receipt,
            str(image_path),
            image_blob=content,
            image_s3_key=image_s3_key,
            image_s3_url=image_s3_url,
        )

        logger.info(f"OCR extraction successful for {receipt_id}")
        return OCRExtractResponse(**receipt)
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        logger.error(f"FATAL ERROR in /extract: \n{error_msg}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
