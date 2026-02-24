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

_FALLBACK_RULES = [
    {"id": "fallback-1", "title": "제3조 금지 품목", "content": "주류(참이슬, 소주, 맥주, 와인, 카스 등) 및 담배 구매 금지"},
    {"id": "fallback-2", "title": "제4조 허용 시간", "content": "오전 08:00 이전 및 오후 22:00 이후 결제 금지"},
]

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


@router.get("/rules")
def get_rules() -> dict:
    persist_path = "./data/vector_store"
    if not os.path.exists(persist_path) or not os.listdir(persist_path):
        return {"mode": "fallback", "rules": _FALLBACK_RULES}

    try:
        from langchain_chroma import Chroma
        embedder = RegulationEmbedder()
        db = Chroma(persist_directory=persist_path, embedding_function=embedder.get_embedding_model())
        count = db._collection.count()
        if count == 0:
            return {"mode": "fallback", "rules": _FALLBACK_RULES}

        results = db._collection.get(limit=20)
        docs = results.get("documents", [])
        ids = results.get("ids", [])
        return {
            "mode": "rag",
            "total_chunks": count,
            "rules": [
                {"id": ids[i], "title": f"조항 {i + 1}", "content": doc}
                for i, doc in enumerate(docs[:10])
            ],
        }
    except Exception:
        return {"mode": "fallback", "rules": _FALLBACK_RULES}

class RuleUpdateRequest(BaseModel):
    content: str

@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: str) -> dict:
    embedder = RegulationEmbedder()
    db_manager = VectorDBManager()
    success = db_manager.delete_document(rule_id, embedder.get_embedding_model())
    if success:
        return {"status": "success", "message": f"Rule {rule_id} deleted"}
    return {"status": "error", "message": "Failed to delete rule"}

@router.put("/rules/{rule_id}")
def update_rule(rule_id: str, payload: RuleUpdateRequest) -> dict:
    from langchain_core.documents import Document
    embedder = RegulationEmbedder()
    db_manager = VectorDBManager()
    
    doc = Document(page_content=payload.content, metadata={"source": "manual_update"})
    success = db_manager.update_document(rule_id, doc, embedder.get_embedding_model())
    if success:
        return {"status": "success", "message": f"Rule {rule_id} updated"}
    return {"status": "error", "message": "Failed to update rule"}


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


@router.post("/demo/{scenario}")
def run_demo_scenario(scenario: str) -> dict:
    import time
    from core.ocr_engine.paddle_wrapper import PaddleOCRWrapper
    from core.ocr_engine.processor import ReceiptProcessor
    from core.audit_agent.reasoning import AuditReasoning
    from core.audit_agent.prompt_templates import AUDIT_SYSTEM_PROMPT
    from core.rag_engine.embedder import RegulationEmbedder
    from core.rag_engine.vector_db import VectorDBManager
    import json

    if scenario == "normal":
        image_path = "data/raw/receipt-0140302be513.jpg"
    elif scenario == "alcohol":
        image_path = "data/raw/alchohol/Alcho_001.jpg"
    else:
        return {"status": "error", "message": f"Unknown scenario: {scenario}"}
        
    ocr_wrapper = PaddleOCRWrapper()
    processor = ReceiptProcessor()
    
    agent = AuditReasoning()
    embedder = RegulationEmbedder()
    db_manager = VectorDBManager()
    
    # 1. OCR Extraction
    try:
        ocr_lines = ocr_wrapper.extract(image_path)
        receipt_val = processor.process(ocr_lines)
        receipt_json = receipt_val if isinstance(receipt_val, dict) else json.loads(str(receipt_val))
    except Exception as e:
        return {"status": "error", "message": f"OCR/Parsing Failed: {str(e)}"}
        
    store_name = receipt_json.get("store_name", "")
    store_address = receipt_json.get("store_address", "")
    items = receipt_json.get("items", [])
    
    # 2. Naver API
    store_info = agent.verifier.get_store_category(store_name, store_address)
    
    # 3. RAG Retrieval + LLM Re-ranking (with Retry)
    from openai import RateLimitError
    import random
    
    def with_retry(func, max_retries=5):
        for attempt in range(max_retries):
            try:
                return func()
            except RateLimitError:
                if attempt == max_retries - 1:
                    raise
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(sleep_time)
            except Exception as e:
                raise e

    rules_rerank_list = []
    unique_contents = set()
    for item in items:
        item_name = item.get('name', '')
        query = f"가게: {store_name}, 품목: {item_name}"
        
        def _run_rerank_search():
            return db_manager.search_rules(query, embedder.get_embedding_model(), k=3, agent_llm=agent.llm)
        try:
            docs = with_retry(_run_rerank_search)
            for d in docs:
                if d.page_content not in unique_contents:
                    rules_rerank_list.append(d.page_content)
                    unique_contents.add(d.page_content)
        except Exception:
            pass
            
    rules_text = "\n\n".join(rules_rerank_list)
    
    # 4. Final Audit
    final_prompt = f"{AUDIT_SYSTEM_PROMPT}\n\n상호명: {store_name}\n가맹점 업종(네이버): {json.dumps(store_info, ensure_ascii=False)}\n규정: {rules_text}\n\n영수증: {json.dumps(receipt_json, ensure_ascii=False)}"
    
    try:
        def _run_final():
            prompt_obj = agent.llm.invoke(final_prompt)
            res = agent.parser.invoke(prompt_obj)
            return res if isinstance(res, dict) else {}
        final_decision_json = with_retry(_run_final) or {}
    except Exception as e:
        return {"status": "error", "message": f"LLM Inference Failed: {str(e)}"}
        
    # receipt_id 생성이 안되어있을 수 있으므로 보완
    if not receipt_json.get("receipt_id"):
        import uuid
        receipt_json["receipt_id"] = f"demo-{uuid.uuid4().hex[:8]}" # pyre-ignore
        
    audit_result = AuditCheckResponse(**final_decision_json).model_dump()
    
    # DB/Storage에는 저장하지 않고 클라이언트로 바로 반환
    return {
        "status": "success",
        "receipt_data": receipt_json,
        "audit_result": audit_result
    }
