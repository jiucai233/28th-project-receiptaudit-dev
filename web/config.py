"""
Configuration file for Transparent-Audit Frontend
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# API Configuration
# Backend API base URL (FastAPI server)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# API Endpoints
API_ENDPOINTS = {
    "ocr_extract": f"{API_BASE_URL}/api/v1/ocr/extract",
    "audit_check": f"{API_BASE_URL}/api/v1/audit/check",
    "audit_confirm": f"{API_BASE_URL}/api/v1/audit/confirm",
}

# API Configuration
API_TIMEOUT = 60  # seconds
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

# Supported image formats
SUPPORTED_IMAGE_FORMATS = ["jpg", "jpeg", "png", "bmp"]

# UI Configuration
APP_TITLE = "Transparent-Audit"
APP_ICON = "🧾"
APP_DESCRIPTION = "조직 회계 투명성을 위한 스마트 영수증 감사 시스템"

# Color scheme
COLORS = {
    "primary": "#1f77b4",
    "success": "#28a745",
    "warning": "#ffc107",
    "danger": "#dc3545",
    "info": "#17a2b8",
}

# Audit decision colors
AUDIT_DECISION_COLORS = {
    "Pass": "success",
    "Anomaly Detected": "danger",
    "Warning": "warning",
}

# Sample policy text (for testing)
SAMPLE_POLICY = """
학생 자치 기구 예산 사용 규정

제1조 (목적)
이 규정은 학생 자치 기구의 예산 사용에 관한 기본 원칙을 정함을 목적으로 한다.

제2조 (예산 사용 원칙)
1. 모든 예산은 투명하고 공정하게 집행되어야 한다.
2. 영수증 및 증빙 서류를 반드시 제출해야 한다.

제3조 (금지 품목)
다음 품목에 대한 지출은 엄격히 금지된다:
1. 주류 (소주, 맥주, 와인 등)
2. 담배
3. 개인적 용도의 물품

제4조 (허용 시간)
예산 집행은 원칙적으로 오전 8시부터 오후 10시 사이에만 가능하다.
"""
