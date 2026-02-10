"""
API Client for communicating with FastAPI backend
"""

import requests
import streamlit as st
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import API_ENDPOINTS, API_TIMEOUT


class BaseAPIClient:
    """Base API client with common functionality"""

    def __init__(self):
        self.timeout = API_TIMEOUT

    def _handle_response(self, response: requests.Response) -> Optional[Dict[str, Any]]:
        """Handle API response"""
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            st.error(f"❌ API 오류: {e}")
            if response.text:
                st.error(f"상세 정보: {response.text}")
            return None
        except requests.exceptions.ConnectionError:
            st.error("❌ 서버에 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인하세요.")
            return None
        except requests.exceptions.Timeout:
            st.error("❌ 요청 시간이 초과되었습니다.")
            return None
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류: {e}")
            return None


class OCRClient(BaseAPIClient):
    """Client for OCR extraction API"""

    def extract(self, uploaded_file) -> Optional[Dict[str, Any]]:
        """
        Extract data from receipt image

        Args:
            uploaded_file: Streamlit UploadedFile object

        Returns:
            Dictionary with extracted receipt data or None if failed
        """
        try:
            # Prepare file for upload
            files = {
                'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
            }

            # Make API request
            response = requests.post(
                API_ENDPOINTS['ocr_extract'],
                files=files,
                timeout=self.timeout
            )

            result = self._handle_response(response)

            if result:
                st.success("✅ OCR 추출 성공!")
                return result
            else:
                return None

        except Exception as e:
            st.error(f"❌ OCR 처리 중 오류 발생: {e}")
            return None


class AuditClient(BaseAPIClient):
    """Client for Audit API"""

    def check(self, receipt_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check receipt data against policy

        Args:
            receipt_data: Receipt data dictionary

        Returns:
            Dictionary with audit results or None if failed
        """
        try:
            # Make API request
            response = requests.post(
                API_ENDPOINTS['audit_check'],
                json=receipt_data,
                timeout=self.timeout
            )

            result = self._handle_response(response)

            if result:
                st.success("✅ 감사 완료!")
                return result
            else:
                return None

        except Exception as e:
            st.error(f"❌ 감사 처리 중 오류 발생: {e}")
            return None

    def confirm(self, receipt_data: Dict[str, Any], audit_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Confirm final audit and generate PDF report

        Args:
            receipt_data: Receipt data dictionary
            audit_result: Audit result dictionary

        Returns:
            Dictionary with PDF URL or None if failed
        """
        try:
            # Prepare payload
            payload = {
                "receipt_data": receipt_data,
                "audit_result": audit_result
            }

            # Make API request
            response = requests.post(
                API_ENDPOINTS['audit_confirm'],
                json=payload,
                timeout=self.timeout
            )

            result = self._handle_response(response)

            if result:
                st.success("✅ 최종 확정 완료!")
                return result
            else:
                return None

        except Exception as e:
            st.error(f"❌ 최종 확정 처리 중 오류 발생: {e}")
            return None


# Mock data for testing when backend is not available
MOCK_OCR_RESPONSE = {
    "receipt_id": "mock-uuid-1234",
    "store_name": "GS25 연세점",
    "date": "2026-02-09 13:40",
    "items": [
        {"id": 1, "name": "참이슬", "unit_price": 1800, "count": 2, "price": 3600},
        {"id": 2, "name": "삼각김밥", "unit_price": 1200, "count": 1, "price": 1200},
        {"id": 3, "name": "바나나우유", "unit_price": 1500, "count": 2, "price": 3000},
    ],
    "total_price": 7800
}

MOCK_AUDIT_RESPONSE = {
    "audit_decision": "Anomaly Detected",
    "violation_score": 0.95,
    "violations": [
        {
            "item_id": 1,
            "reason": "회계 규정 제3조(주류 구매 금지) 위반 가능성 높음",
            "policy_reference": "학생 자치 기구 예산으로 주류 구매는 엄격히 금지됨"
        }
    ],
    "reasoning": "영수증에 포함된 '참이슬'은 주류로 분류되며, 이는 등록된 정책 문서의 금지 품목에 해당합니다."
}


class MockOCRClient(OCRClient):
    """Mock OCR client for testing without backend"""

    def extract(self, uploaded_file) -> Optional[Dict[str, Any]]:
        """Return mock data instead of calling real API"""
        import time
        time.sleep(1)  # Simulate processing time

        if uploaded_file is None:
            st.success("🎯 Mock 모드: 샘플 영수증 데이터를 불러왔습니다")
        else:
            st.info("🔧 Mock 모드: 업로드된 이미지 대신 샘플 데이터를 반환합니다")

        return MOCK_OCR_RESPONSE


class MockAuditClient(AuditClient):
    """Mock Audit client for testing without backend"""

    def check(self, receipt_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return mock data instead of calling real API"""
        import time
        time.sleep(1)  # Simulate processing time
        st.info("🔧 Mock 모드: 실제 감사 대신 샘플 결과를 반환합니다")
        return MOCK_AUDIT_RESPONSE

    def confirm(self, receipt_data: Dict[str, Any], audit_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return mock data instead of calling real API"""
        import time
        time.sleep(1)  # Simulate processing time
        st.info("🔧 Mock 모드: 실제 PDF 생성을 건너뜁니다")
        return {
            "status": "success",
            "pdf_url": "/mock/report.pdf",
            "pdf_data": b"Mock PDF data"
        }
