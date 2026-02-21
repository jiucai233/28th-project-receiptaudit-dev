from __future__ import annotations

import base64
import os
import shutil
from typing import Optional

from fastapi import APIRouter, File, UploadFile, Form
from pydantic import BaseModel, Field

from server.services import AuditService, DBService, ReportService, StorageService
from core.rag_engine.embedder import RegulationEmbedder
from core.rag_engine.vector_db import VectorDBManager

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])

audit_service = AuditService()
report_service = ReportService()
storage_service = StorageService()
db_service = DBService()


class ReceiptItem(BaseModel):
    id: int
    name: str
    unit_price: int = Field(ge=0)
    count: int = Field(ge=1)
    price: int = Field(ge=0)


class ReceiptData(BaseModel):
    receipt_id: str
    store_name: str
    date: str
    items: list[ReceiptItem]
    total_price: int = Field(ge=0)


class Violation(BaseModel):
    item_id: int
    reason: str
    policy_reference: str


class AuditCheckResponse(BaseModel):
    audit_decision: str
    violation_score: float = Field(ge=0.0, le=1.0)
    violations: list[Violation]
    reasoning: str


class AuditConfirmRequest(BaseModel):
    receipt_data: ReceiptData
    audit_result: AuditCheckResponse


class AuditConfirmResponse(BaseModel):
    status: str
    pdf_url: str


class AuditBatchConfirmRequest(BaseModel):
    receipts: list[AuditConfirmRequest]


class AuditBatchConfirmResponse(BaseModel):
    status: str
    pdf_url: str


@router.post("/check", response_model=AuditCheckResponse)
def check(payload: ReceiptData) -> AuditCheckResponse:
    receipt = payload.model_dump()
    result = audit_service.check(receipt)
    storage_service.save_json(result, f"{payload.receipt_id}_audit.json")
    db_service.upsert_audit(payload.receipt_id, result)
    return AuditCheckResponse(**result)


@router.post("/confirm")
def confirm(payload: AuditConfirmRequest) -> dict:
    receipt_data = payload.receipt_data.model_dump()
    audit_result = payload.audit_result.model_dump()

    pdf_bytes = report_service.build_pdf(receipt_data, audit_result)
    pdf_path = storage_service.save_pdf(receipt_data["receipt_id"], pdf_bytes)
    s3_result = storage_service.upload_pdf_to_s3(receipt_data["receipt_id"], pdf_bytes)
    pdf_s3_key = s3_result[0] if s3_result else None
    pdf_s3_url = s3_result[1] if s3_result else None

    response_data = AuditConfirmResponse(
        status="success", pdf_url=pdf_s3_url or str(pdf_path)
    ).model_dump()
    response_data["pdf_data"] = base64.b64encode(pdf_bytes).decode("ascii")

    db_service.upsert_report(
        receipt_data["receipt_id"],
        str(pdf_path),
        response_data,
        pdf_blob=pdf_bytes,
        pdf_s3_key=pdf_s3_key,
        pdf_s3_url=pdf_s3_url,
    )
    return response_data


@router.post("/batch-confirm")
def batch_confirm(payload: AuditBatchConfirmRequest) -> dict:
    if not payload.receipts:
        return {"status": "error", "message": "No receipts provided for batch confirmation."}

    # Aggregate batch data
    batch_data = []
    receipt_ids = []
    for req in payload.receipts:
        receipt_data = req.receipt_data.model_dump()
        audit_result = req.audit_result.model_dump()
        batch_data.append((receipt_data, audit_result))
        receipt_ids.append(receipt_data["receipt_id"])

    pdf_bytes = report_service.build_batch_pdf(batch_data)
    
    # Generate a unique ID for this batch to save it
    import uuid
    batch_id = f"batch-{uuid.uuid4().hex[:8]}"
    
    # Save PDF
    pdf_path = storage_service.save_pdf(batch_id, pdf_bytes)
    s3_result = storage_service.upload_pdf_to_s3(batch_id, pdf_bytes)
    pdf_s3_key = s3_result[0] if s3_result else None
    pdf_s3_url = s3_result[1] if s3_result else None

    response_data = AuditBatchConfirmResponse(
        status="success", pdf_url=pdf_s3_url or str(pdf_path)
    ).model_dump()
    response_data["pdf_data"] = base64.b64encode(pdf_bytes).decode("ascii")

    # Update database for all receipts in this batch to point to this single PDF
    for receipt_id in receipt_ids:
        # We need the original payload for the DB, so we get it from the request
        req_match = next(r for r in payload.receipts if r.receipt_data.receipt_id == receipt_id)
        db_payload = {
            "status": "success",
            "pdf_url": response_data["pdf_url"],
            "batch_id": batch_id, # useful for grouping later
            "receipt_data": req_match.receipt_data.model_dump(),
            "audit_result": req_match.audit_result.model_dump()
        }
        
        db_service.upsert_report(
            receipt_id,
            str(pdf_path),
            db_payload,
            pdf_blob=pdf_bytes,   # In a real app we might only store this once
            pdf_s3_key=pdf_s3_key,
            pdf_s3_url=pdf_s3_url,
        )

    return response_data


@router.post("/upload-rules")
async def upload_rules(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
) -> dict:
    embedder = RegulationEmbedder()
    db_manager = VectorDBManager()
    
    docs = []
    if file:
        # Save temp file
        os.makedirs("data/intermediate", exist_ok=True)
        temp_path = f"data/intermediate/{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            docs = embedder.split_documents(temp_path)
            db_manager.add_documents(docs, embedder.get_embedding_model())
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    if text:
        text_docs = embedder.get_chunks(text)
        db_manager.add_documents(text_docs, embedder.get_embedding_model())
        docs.extend(text_docs)

    if not docs:
        return {"status": "error", "message": "No content provided"}

    return {"status": "success", "message": f"Processed {len(docs)} chunks"}
