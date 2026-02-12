"""
API Client for communicating with FastAPI backend
"""

import base64
import requests
import streamlit as st
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import API_ENDPOINTS, API_TIMEOUT


# ──────────────────────────────────────────────
# Real API Clients (for backend integration)
# ──────────────────────────────────────────────

class OCRClient:
    """Real OCR client - calls POST /api/v1/ocr/extract"""

    def extract(self, uploaded_file) -> Optional[Dict[str, Any]]:
        try:
            files = {
                'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
            }
            response = requests.post(
                API_ENDPOINTS['ocr_extract'],
                files=files,
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            st.error("❌ 서버에 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인하세요.")
            return None
        except Exception as e:
            st.error(f"❌ OCR 처리 중 오류: {e}")
            return None


class AuditClient:
    """Real Audit client - calls POST /api/v1/audit/check and /confirm"""

    def check(self, receipt_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            response = requests.post(
                API_ENDPOINTS['audit_check'],
                json=receipt_data,
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            st.error("❌ 서버에 연결할 수 없습니다.")
            return None
        except Exception as e:
            st.error(f"❌ 감사 처리 중 오류: {e}")
            return None

    def confirm(self, receipt_data: Dict[str, Any], audit_result: Dict[str, Any]) -> Dict[str, Any]:
        try:
            payload = {
                "receipt_data": receipt_data,
                "audit_result": audit_result
            }
            response = requests.post(
                API_ENDPOINTS['audit_confirm'],
                json=payload,
                timeout=API_TIMEOUT
            )
            response.raise_for_status()
            result = response.json()

            # Backend returns base64-encoded pdf_data -> decode to bytes for download
            if "pdf_data" in result:
                result["pdf_data"] = base64.b64decode(result["pdf_data"])

            # Extract filename from pdf_url for download button
            pdf_url = result.get("pdf_url", "")
            result["filename"] = Path(pdf_url).name if pdf_url else "audit_report.pdf"

            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}


# ──────────────────────────────────────────────
# Mock Data & Clients (for testing without backend)
# ──────────────────────────────────────────────

# --- Scenario Data ---
MOCK_RECEIPTS = {
    "Scenario A: Normal Office Supply": {
        "receipt_id": "DEMO-001",
        "store_name": "Alpha Stationeries",
        "date": "2026-02-10 14:00",
        "items": [
            {"id": 1, "name": "A4 Paper (500 sheets)", "unit_price": 5500, "count": 2, "price": 11000},
            {"id": 2, "name": "Ballpoint Pen Black", "unit_price": 1200, "count": 5, "price": 6000},
        ],
        "total_price": 17000
    },
    "Scenario B: Alcohol Violation": {
        "receipt_id": "DEMO-002",
        "store_name": "GS25 Convenience",
        "date": "2026-02-11 19:30",
        "items": [
            {"id": 1, "name": "Soju (Chamisul)", "unit_price": 1800, "count": 3, "price": 5400},
            {"id": 2, "name": "Snack", "unit_price": 1500, "count": 1, "price": 1500},
            {"id": 3, "name": "Beer (Cass)", "unit_price": 2500, "count": 2, "price": 5000},
        ],
        "total_price": 11900
    }
}

class MockAuditClient:
    """Smart Mock Client that reacts to data edits"""

    def check(self, receipt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Dynamically check for violations in edited data"""
        import time
        time.sleep(1)
        
        violations = []
        items = receipt_data.get("items", [])
        
        # 1. Check for Alcohol keywords
        alcohol_keywords = ["soju", "beer", "wine", "whisky", "소주", "맥주", "주류"]
        for item in items:
            name_lower = item.get("name", "").lower()
            if any(kw in name_lower for kw in alcohol_keywords):
                violations.append({
                    "item_id": item.get("id"),
                    "reason": f"Prohibited item detected: {item.get('name')}",
                    "policy_reference": "Financial Regulation Article 3 (Prohibition of Alcohol)"
                })
        
        # 2. Check for suspicious time (if edited)
        date_str = receipt_data.get("date", "")
        if "23:" in date_str or "00:" in date_str:
             violations.append({
                "item_id": 0,
                "reason": "Suspicious transaction time (Late Night)",
                "policy_reference": "Article 7: Midnight expenses require justification"
            })

        if not violations:
            return {
                "audit_decision": "Pass",
                "violation_score": 0.05,
                "violations": [],
                "reasoning": "No policy violations found in the provided data."
            }
        else:
            return {
                "audit_decision": "Anomaly Detected",
                "violation_score": 0.9,
                "violations": violations,
                "reasoning": f"Audit failed due to {len(violations)} potential policy violations."
            }

    def confirm(self, receipt_data: Dict[str, Any], audit_result: Dict[str, Any]) -> Dict[str, Any]:
        """Actually trigger the PDF generator and return file path"""
        try:
            from core.report_engine.generator import AuditReportGenerator
            generator = AuditReportGenerator()
            pdf_path = generator.generate(receipt_data, audit_result)
            
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
                
            return {
                "status": "success",
                "pdf_path": pdf_path,
                "pdf_data": pdf_bytes,
                "filename": Path(pdf_path).name
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

class MockOCRClient:
    def extract(self, scenario_name: str) -> Optional[Dict[str, Any]]:
        return MOCK_RECEIPTS.get(scenario_name)
