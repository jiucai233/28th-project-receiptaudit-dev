# Transparent-Audit React Frontend

조직 회계 투명성을 위한 스마트 영수증 감사 시스템 - React + TypeScript 버전

## 실행 방법

### Docker 사용 (권장)

```bash
# 1. web-react 폴더로 이동
cd web-react

# 2. Docker 컨테이너 실행
docker run -it --rm -v "${PWD}:/app" -w /app -p 5173:5173 node:24-alpine sh

# 3. 컨테이너 내부에서 의존성 설치 및 실행
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

브라우저에서 **http://localhost:5173** 접속

종료: `Ctrl + C` → `exit`

### Node.js 직접 사용 (v18 이상)

```bash
cd web-react
npm install
npm run dev
```

브라우저에서 **http://localhost:3000** 접속

### 빌드 (배포용)

```bash
npm run build
```

빌드된 파일은 `dist/` 폴더에 생성됩니다.

## 백엔드 연동

기본값은 **Demo Mode**로, 백엔드 없이 샘플 데이터로 테스트 가능합니다.

백엔드와 연동하려면:

1. `src/App.tsx`에서 `USE_MOCK_MODE`를 `false`로 변경
2. 백엔드를 실행

```bash
# 터미널 1: 백엔드 실행
cd 28th-project-receiptaudit-dev
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000

# 터미널 2: 프론트엔드 실행
cd 28th-project-receiptaudit-dev/web-react
docker run -it --rm -v "${PWD}:/app" -w /app -p 5173:5173 node:24-alpine sh
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

백엔드 주소가 `localhost:8000`이 아닌 경우 `web-react/.env` 파일 생성:

```
VITE_API_BASE_URL=http://<백엔드주소>:<포트>
```

## 프로젝트 구조

```
web-react/
├── src/
│   ├── components/          # React 컴포넌트
│   │   ├── UploadStep.tsx   # 영수증 업로드
│   │   ├── DataEditor.tsx   # 데이터 편집 테이블
│   │   └── AuditResults.tsx # 감사 결과 표시
│   ├── services/            # API 통신
│   │   ├── api.ts           # 실제 API 클라이언트
│   │   └── mockData.ts      # Mock 데이터
│   ├── types/               # TypeScript 타입
│   │   └── index.ts         # 백엔드 스키마와 일치
│   ├── hooks/               # Custom Hooks
│   │   ├── useReceipt.ts    # 상태 관리
│   │   └── useCountUp.ts    # 숫자 카운트업 애니메이션
│   ├── App.tsx              # 메인 앱
│   └── main.tsx             # 진입점
├── package.json
├── vite.config.ts
└── tailwind.config.js
```

## 기술 스택

- **React 18** + **TypeScript**
- **Vite** - 빌드 도구
- **Tailwind CSS** - 스타일링
- **Axios** - HTTP 클라이언트
- **Lucide React** - 아이콘

## 백엔드 API 엔드포인트

- `POST /api/v1/ocr/extract` - OCR 텍스트 추출
- `POST /api/v1/audit/check` - 감사 검사
- `POST /api/v1/audit/confirm` - PDF 생성

## 트러블슈팅

### 백엔드 연결 오류

```
Error: connect ECONNREFUSED 127.0.0.1:8000
```

1. 백엔드 서버가 실행 중인지 확인
2. `.env` 파일의 URL 확인
3. 또는 Mock 모드로 전환

### CORS 오류

백엔드에서 CORS 허용 확인:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
)
```
