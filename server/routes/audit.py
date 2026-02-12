from __future__ import annotations

import base64

from fastapi import APIRouter
from pydantic import BaseModel, Field

from server.services import AuditService, DBService, ReportService, StorageService

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

    response = AuditConfirmResponse(status="success", pdf_url=str(pdf_path)).model_dump()
    response["pdf_data"] = base64.b64encode(pdf_bytes).decode("ascii")

    db_service.upsert_report(receipt_data["receipt_id"], str(pdf_path), response)
    return response
