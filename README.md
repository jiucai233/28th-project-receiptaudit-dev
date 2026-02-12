# 🧾 Transparent-Audit

조직 회계 투명성을 위한 스마트 영수증 감사 시스템 (Smart Receipt Audit System for Organizational Accounting Transparency)

## 🌟 프로젝트 개요
'Transparent-Audit'은 영수증 이미지를 분석하여 조직의 회계 규정 위반 여부를 자동으로 감시하는 시스템입니다. OCR 기술로 데이터를 추출하고, RAG(Retrieval-Augmented Generation) 기반의 AI Agent가 복잡한 규정 문서를 바탕으로 감사를 수행합니다.

## 📁 전체 프로젝트 구조

```
.
├── core/                           # 핵심 비즈니스 로직
│   ├── audit_agent/                # AI 감사 에이전트 (Reasoning, Prompt)
│   ├── ocr_engine/                 # OCR 처리 (PaddleOCR)
│   ├── rag_engine/                 # RAG 엔진 (Vector DB, Embedding)
│   └── report_engine/              # 보고서 생성 (PDF Generator)
├── server/                         # Backend API (FastAPI)
│   ├── routes/                     # API 라우팅
│   └── services/                   # 비즈니스 서비스 레이어
├── web/                            # Frontend (Streamlit)
│   ├── app.py                      # Main Streamlit application
│   ├── config.py                   # Configuration
│   └── src/
│       ├── components/             # UI UI 컴포넌트
│       └── utils/                  # API 클라이언트 및 유틸리티
├── data/                           # 데이터 저장소
│   ├── raw/                        # 원본 규정 PDF 및 영수증 이미지
│   ├── intermediate/               # 중간 처리 결과
│   ├── output/                     # 생성된 감사 보고서
│   └── vector_store/               # ChromaDB 벡터 데이터
├── requirements.txt                # 전체 프로젝트 의존성
└── README.md                       # 프로젝트 통합 문서
```

## 🚀 시작하기

### 1. 환경 설정
Python 3.9+ 환경이 필요합니다.

```bash
# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 설정
`.env.example` 파일을 참고하여 `.env` 파일을 생성하고 필요한 API 키(Upstage 등)를 설정하세요.

### 3. 데이터 준비 (RAG)
규정집 PDF를 `data/raw/`에 넣은 후 벡터 DB를 구축합니다.
```bash
python -m core.rag_engine.ingest
```

### 4. 실행

#### 프론트엔드 (Streamlit)
```bash
cd web
streamlit run app.py
```

#### 백엔드 (FastAPI)
```bash
uvicorn server.routes.app:app --reload
```

백엔드 기본 엔드포인트:
- `GET /health`
- `POST /api/v1/ocr/extract`
- `POST /api/v1/audit/check`
- `POST /api/v1/audit/confirm`

## 📝 주요 기능 흐름
1. **영수증 업로드**: 사용자가 영수증 이미지를 웹 UI에 업로드.
2. **데이터 추출 (OCR)**: 이미지에서 상호명, 일시, 품목, 금액 등을 자동 추출.
3. **규정 검색 (RAG)**: 업로드된 영수증과 관련된 회계 규정을 벡터 DB에서 검색.
4. **AI 감사 (Agent)**: AI 감사관이 추출된 데이터와 검색된 규정을 대조 분석.
5. **결과 리포트**: 위반 항목, 위험도 점수, 판단 근거를 포함한 PDF 보고서 생성.

## 🧪 테스트 (Mock 모드)
백엔드 서버 없이 프론트엔드 기능을 확인하려면 `web/app.py`에서 Mock 클라이언트를 사용하도록 설정되어 있습니다. 샘플 데이터를 통해 전체 UI 흐름을 체험해 볼 수 있습니다.

## 🛠 기술 스택
- **Frontend**: Streamlit, Pandas
- **Backend**: FastAPI
- **AI/LLM**: LangChain, Upstage (Solar LLM), ChromaDB
- **OCR**: PaddleOCR
- **Language**: Python

---
*이 프로젝트는 회계 투명성 확보를 위한 자동화 도구로 개발되었습니다.*
