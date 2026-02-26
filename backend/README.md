# Billing AI Assistant - Backend

이 디렉토리는 **FastAPI**와 **LangGraph**를 중심으로 구축된 **요금 안내 AI 상담원**의 백엔드 API 서버입니다. Gemini 2.5 Flash 모델과 연결되어 사용자의 요금 조회, 추천, 계산 등의 복잡한 요청을 처리합니다.

## 🚀 주요 기능

- **지능형 상담 에이전트**: LangGraph의 ReAct 패턴을 활용하여 사용자의 의도를 분석하고 적절한 도구(Tool)를 선택합니다.
- **도구(Tool) 통합**: 에이전트는 다양한 도구를 활용하여 필요한 데이터 수집 및 계산을 수행합니다. (자세한 내용은 [구현된 Tools](#-구현된-tools) 참고)
- **문맥 유지 (MemorySaver)**: `thread_id` 기반으로 대화 히스토리를 서버 메모리에 저장하여 끊김 없는 상담을 제공합니다.
- **오류 분석 및 로깅 체계**: 예외 발생 시 에러 코드를 분석(예: `API_ERROR`, `DATABASE_ERROR`)하고, 모든 요청과 처리에 대해 구체적인 로그를 기록합니다.

## 📦 구현된 Tools

현재 에이전트가 사용할 수 있도록 연동된 주요 도구(Function)들은 다음과 같습니다.

### 1. `calculate_billing(plans)`
- **기능**: 사용자가 입력한 요금제별 사용 개월 수를 기반으로 총 요금을 계산합니다.
- **용도**: 단순 가격 계산 및 요금 확인용으로 사용됩니다.

### 2. `fetch_billing_history(user_id, month)`
- **기능**: 특정 사용자의 특정 연월(예: 2026-02)에 대한 요금 청구 내역(DB)을 조회합니다.
- **용도**: 청구된 기본 요금, 애드온 요금 등을 상세 조회할 때 사용됩니다.

### 3. `recommend_plan_by_budget(budget, months)`
- **기능**: 사용자의 가용 예산과 사용 기간에 맞춰 최적의 요금제 조합을 추천합니다.
- **용도**: 단순 조회가 아닌, 규칙에 따라 연산을 수행하여 결과를 제안할 때 사용됩니다.

### 4. `analyze_overage_cause(user_id, month)`
- **기능**: 특정 월의 요금 초과 사유(API Overage, 애드온 활성화 등)를 분석하여 상세 명세를 조회합니다.
- **용도**: "왜 요금이 많이 나왔는지"에 대한 구체적인 대응과 상세 분석을 위해 `fetch_billing_history`와 함께 활용됩니다.

### 5. `change_subscription_plan(user_id, target_plan, apply_type, start_month)`
- **기능**: 사용자의 구독 요금제를 변경(즉시 변경, 지정하신 월부터 예약 등)하고, 변경 사항과 요금 청구 금액 시뮬레이션을 DB에 일괄 동기화(Update)합니다.
- **용도**: 고객 정보를 단순 조회할 뿐만 아니라, 특정 시점이나 요구사항에 맞춰 액션(Mutation)을 실행하고 이력(History)을 남길 목적으로 새롭게 구현된 도구입니다.

## 🛠 필수 환경 변수 (.env)

서버를 실행하기 전에 프로젝트 최상단 루트 디렉토리의 `.env` 파일에 다음 항목들이 설정되어 있어야 합니다:

```env
GOOGLE_API_KEY="your_gemini_api_key_here"
SUPABASE_URL="your_supabase_project_url"
SUPABASE_KEY="your_supabase_anon_key"
```

## ⚙️ 로컬 실행 (Development)

초고속 파이썬 패키지 매니저인 `uv`를 사용하는 것을 권장합니다.

```bash
# 1. 의존성 설치 (프로젝트 루트 경로에서 실행)
uv sync

# 2. 백엔드 서버 단독 실행 (기본 포트 확인: 8000)
uv run python backend/main.py

# 또는 uvicorn을 직접 사용할 경우
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔌 API 엔드포인트

서버가 실행되면 **`http://localhost:8000/docs`** (Swagger UI)에서 API를 직접 호출하고 테스트해 볼 수 있습니다.

- `POST /chat`: 상담원과 실제 대화를 주고받는 메인 엔드포인트입니다.
  - **Input**: `{"message": "...", "thread_id": "..."}`
  - **Output**: `[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]` (메시지 배열 형태)
- `GET /health`: 서버의 정상 구동 여부를 확인하기 위한 헬스체크 및 Liveness Probe용 엔드포인트입니다.

## 🐳 Docker 실행

이 프로젝트는 백엔드와 프론트엔드를 함께 컨테이너 환경에서 띄우도록 설정되어 있습니다. 
단일 컨테이너가 아닌 프로젝트 루트에 위치한 `docker-compose.yml`을 사용하여 전체 시스템을 시작하시길 권장합니다.

```bash
# 프로젝트 루트 공간에서 실행
docker compose up -d --build
```
(자세한 내용은 최상단의 `README.md`를 참고하세요.)
