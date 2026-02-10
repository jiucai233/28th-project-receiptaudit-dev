# Transparent-Audit Frontend

조직 회계 투명성을 위한 스마트 영수증 감사 시스템 - Streamlit 프론트엔드

## 📁 프로젝트 구조

```
web/
├── app.py                          # Main Streamlit application
├── streamlit_app.py                # Entry point for Streamlit Cloud deployment
├── config.py                       # Configuration (API endpoints, constants)
├── .streamlit/
│   └── config.toml                 # Streamlit configuration
├── .env.example                    # Environment variables template
├── .gitignore                      # Git ignore rules
├── packages.txt                    # System dependencies for deployment
├── run.bat / run.sh                # Run scripts
├── README.md                       # This file
└── src/
    ├── components/                 # UI components
    │   ├── __init__.py
    │   ├── upload_component.py     # Image upload interface
    │   ├── data_editor_component.py # Editable table for receipt data
    │   └── audit_result_component.py # Audit results display
    └── utils/
        ├── __init__.py
        └── api_client.py           # API communication (OCR, Audit, Confirm)
```

## 🚀 실행 방법

### 1. 의존성 설치

```bash
# 프로젝트 루트 디렉토리에서
cd c:\computer\28th-project-receiptaudit-dev

# uv 사용 (권장)
uv pip install -r requirements.txt

# 또는 pip 사용
pip install -r requirements.txt
```

### 2. 백엔드 서버 실행 (선택사항)

백엔드 팀이 FastAPI 서버를 준비하기 전까지는 Mock 모드로 실행 가능합니다.

```bash
# Backend 서버 실행 (server/ 디렉토리)
cd server
uvicorn main:app --reload --port 8000
```

### 3. Streamlit 앱 실행

```bash
# web 디렉토리로 이동
cd web

# Streamlit 실행
streamlit run app.py
```

브라우저가 자동으로 열리고 `http://localhost:8501` 에서 앱이 실행됩니다.

### 4. Streamlit Cloud 배포 (선택사항)

**로컬 실행**:
```bash
streamlit run app.py
```

**Streamlit Cloud 배포**:
- `streamlit_app.py`가 자동으로 인식됩니다
- GitHub 저장소를 연결하면 자동 배포됩니다
- [Streamlit Cloud](https://streamlit.io/cloud) 참고

## 🔧 설정

### API 엔드포인트 설정

`config.py` 파일에서 백엔드 서버 주소를 변경할 수 있습니다:

```python
# Default: http://localhost:8000
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
```

환경 변수로도 설정 가능:

```bash
export API_BASE_URL=http://your-backend-server:8000
streamlit run app.py
```

## 📝 사용 흐름

1. **영수증 업로드**: 영수증 이미지를 업로드합니다 (JPG, PNG 등)
2. **OCR 추출**: 이미지에서 텍스트를 자동으로 추출합니다
3. **데이터 편집**: 추출된 데이터를 확인하고 필요시 수정합니다
4. **감사 실행**: AI가 조직의 회계 규정과 대조하여 위반 여부를 판단합니다
5. **결과 확인**: 위반 항목과 판단 근거를 확인합니다
6. **최종 확정**: PDF 보고서를 생성하고 다운로드합니다

## 🔌 API 통신

### 사용되는 API 엔드포인트:

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/v1/ocr/extract` | POST | 영수증 이미지에서 텍스트 추출 |
| `/api/v1/audit/check` | POST | 정책 위반 여부 검사 |
| `/api/v1/audit/confirm` | POST | 최종 확정 및 PDF 생성 |

자세한 API 명세는 상위 디렉토리의 API 문서를 참고하세요.

## 🧪 Mock 모드

백엔드 서버 없이 테스트하려면 `api_client.py`에서 Mock 클라이언트를 사용하세요:

```python
# app.py에서
from utils.api_client import MockOCRClient, MockAuditClient

# 대신 이렇게 사용:
ocr_client = MockOCRClient()  # 실제: OCRClient()
audit_client = MockAuditClient()  # 실제: AuditClient()
```

Mock 모드는 샘플 데이터를 반환하여 UI 개발 및 테스트를 도와줍니다.

## 🎨 커스터마이징

### 색상 변경

`config.py`의 `COLORS` 딕셔너리에서 색상 테마를 변경할 수 있습니다.

### 컴포넌트 수정

`src/components/` 디렉토리의 각 파일은 독립적인 컴포넌트입니다:
- `upload_component.py` - 업로드 UI
- `data_editor_component.py` - 데이터 편집 테이블
- `audit_result_component.py` - 감사 결과 표시

## 의존성

주요 라이브러리:
- `streamlit` - 웹 프레임워크
- `requests` - API 통신
- `pandas` - 데이터 처리

전체 의존성은 `requirements.txt` 참조

## 트러블슈팅

### 서버 연결 오류

```
❌ 서버에 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인하세요.
```

**해결 방법**:
1. 백엔드 서버가 실행 중인지 확인
2. `config.py`의 `API_BASE_URL`이 올바른지 확인
3. 또는 Mock 모드로 전환

