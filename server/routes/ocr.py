from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from server.services import DBService, OCRService, StorageService

router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])

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


@router.post("/extract", response_model=OCRExtractResponse)
async def extract(file: UploadFile = File(...)) -> OCRExtractResponse:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large")

    await file.seek(0)
    receipt_id = storage_service.new_receipt_id()
    image_path = await storage_service.save_upload(file, receipt_id)

    receipt = ocr_service.extract(image_path, receipt_id)
    storage_service.save_json(receipt, f"{receipt_id}_ocr.json")
    db_service.upsert_receipt(receipt_id, receipt, str(image_path))

    return OCRExtractResponse(**receipt)
