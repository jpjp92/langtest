"""
Billing AI Assistant - Backend API Server
========================================

이 파일은 LangGraph 기반의 AI 상담원 에이전트를 구동하는 FastAPI 서버입니다.

[실행 방법]
프로젝트 루트 디렉토리에서 아래 명령어를 실행하세요:

    uv run python backend/main.py

또는 uvicorn을 직접 사용하는 경우:
    
    uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

서버가 실행되면 http://localhost:8000/docs 에서 Swagger UI를 확인할 수 있습니다.
"""
import os
import uvicorn
import logging
from datetime import datetime
from typing import TypedDict, Annotated, List, Optional
from pydantic import BaseModel, Field
import operator
from supabase import create_client, Client
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 외부 라이브러리의 너무 잦은 INFO 로그 표출 숨기기
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool

# ─────────────────────────────────────────
# 1. 환경 변수 로드 및 Supabase 초기화
# ─────────────────────────────────────────
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

# ─────────────────────────────────────────
# 2. 요금 계산 Tool 정의
# ─────────────────────────────────────────
PLAN_PRICES = {
    "라이트": 9_900,
    "lite": 9_900,
    "프로": 29_900,
    "pro": 29_900,
    "엔터프라이즈": None,
    "enterprise": None,
}

class PlanUsage(BaseModel):
    plan: str = Field(description="요금제 이름. '라이트', '프로', '엔터프라이즈' 중 하나.")
    months: int = Field(description="해당 요금제를 사용한 개월 수")

class BillingInput(BaseModel):
    plans: List[PlanUsage] = Field(
        description="요금제 사용 내역 리스트. 예: [{plan: '라이트', months: 3}, {plan: '프로', months: 2}]"
    )

class RecommendInput(BaseModel):
    budget: int = Field(description="사용자의 가용 예산 (단위: 원)")
    months: int = Field(default=12, description="예산을 사용할 기간 (개월 수, 기본값 12)")

@tool(args_schema=BillingInput)
def calculate_billing(plans: List[PlanUsage]) -> str:
    """사용자가 사용한 요금제별 개월 수를 입력받아 총 요금을 계산합니다."""
    total = 0
    lines = []
    for item in plans:
        plan_name = item.plan
        months = item.months
        price = PLAN_PRICES.get(plan_name.lower(), PLAN_PRICES.get(plan_name))
        if price is None:
            lines.append(f"- {plan_name} {months}개월: 별도 문의 (엔터프라이즈)")
        else:
            subtotal = price * months
            total += subtotal
            lines.append(f"- {plan_name} ({price:,}원/월) × {months}개월 = {subtotal:,}원")
    breakdown = "\n".join(lines)
    return f"[요금 계산 결과]\n{breakdown}\n\n💰 총 합계: {total:,}원"

class BillingHistoryInput(BaseModel):
    user_id: str = Field(description="조회할 사용자의 ID (예: 'user_123')")
    month: str = Field(description="조회할 연월 (형식: 'YYYY-MM', 예: '2026-02')")

@tool(args_schema=BillingHistoryInput)
def fetch_billing_history(user_id: str, month: str) -> str:
    """사용자의 특정 월 요금 청구 내역(DB)을 조회합니다."""
    if not supabase:
        return "시스템 오류: 데이터베이스에 연결할 수 없습니다."
    
    try:
        response = supabase.table("billing_history").select("details").eq("user_id", user_id).eq("billing_month", month).execute()
        if response.data:
            details = response.data[0]["details"]
            return (
                f"[{user_id} 님의 {month} 청구 상세 내역]\n"
                f"- 기본료: {details.get('base_fee', 0):,}원\n"
                f"- 초과 이용료: {details.get('exceed_fee', 0):,}원 ({details.get('exceed_reason', '상세 사유 없음')})\n"
                f"- 부가/소액결제: {details.get('extra_fee', 0):,}원 ({details.get('extra_reason', '상세 사유 없음')})\n"
                f"- 할인액: {details.get('discount', 0):,}원\n"
                f"- 총 청구 금액: {details.get('total', 0):,}원"
            )
        else:
            return f"{user_id} 님의 {month} 청구 내역이 존재하지 않습니다."
    except Exception as e:
        logger.error(f"DB 데이터 조회 중 오류 발생: {e}")
        return f"요금 내역 조회 중 오류 발생: {e}"

def classify_error(error_msg: str) -> tuple[str, int]:
    """오류 메시지를 분석하여 에러 코드와 HTTP 상태 코드를 반환"""
    error_code = "PROCESSING_ERROR"
    status_code = 500
    
    error_msg_lower = error_msg.lower()
    
    if "api" in error_msg_lower or "gemini" in error_msg_lower:
        error_code = "API_ERROR"
        if "quota" in error_msg_lower or "rate limit" in error_msg_lower:
            status_code = 429
    elif "supabase" in error_msg_lower or "database" in error_msg_lower:
        error_code = "DATABASE_ERROR"
        status_code = 503
        
    return error_code, status_code

@tool(args_schema=RecommendInput)
def recommend_plan_by_budget(budget: int, months: int = 12) -> str:
    """사용자의 예산과 기간에 맞춤화된 요금제 조합을 추천합니다."""
    lite_total = PLAN_PRICES["라이트"] * months
    pro_total = PLAN_PRICES["프로"] * months
    recommendations = [f"입력하신 예산 {budget:,}원 ({months}개월 기준) 추천안입니다:"]
    
    if budget >= pro_total:
        recommendations.append(f"✅ [Pro 추천] {months}개월 동안 모든 고급 기능을 제약 없이 사용하실 수 있습니다. (총 {pro_total:,}원)")
    elif budget >= lite_total:
        recommendations.append(f"✅ [Lite 추천] {months}개월 동안 안정적으로 기본 기능을 이용하실 수 있습니다. (총 {lite_total:,}원)")
        extra_budget = budget - lite_total
        pro_upgrade_cost = PLAN_PRICES["프로"] - PLAN_PRICES["라이트"]
        upgrade_months = extra_budget // pro_upgrade_cost
        if upgrade_months > 0:
            # 기간(months)을 초과하지 않도록 제한
            actual_upgrade_months = min(upgrade_months, months)
            recommendations.append(f"💡 [하이브리드안] 라이트 요금제를 기본으로 쓰시되, 중요한 프로젝트가 있는 {actual_upgrade_months}개월 동안은 프로로 업그레이드하셔도 예산 내에 들어옵니다.")
    else:
        possible_months = budget // PLAN_PRICES["라이트"]
        if possible_months > 0:
            recommendations.append(f"⚠️ 라이트 요금제를 최대 {possible_months}개월 동안 이용하실 수 있습니다. 요청하신 {months}개월을 모두 쓰시기에는 예산이 조금 부족하네요.")
        else:
            recommendations.append(f"⚠️ 현재 예산으로는 유료 요금제 이용이 어렵습니다. 무료 체험판이나 예산을 조금 더 확보하시는 것을 추천드립니다.")
            
    return "\n".join(recommendations)

class OverageInput(BaseModel):
    user_id: str = Field(description="조회할 사용자의 ID (예: 'user_123')")
    month: str = Field(description="조회할 연월 (형식: 'YYYY-MM', 예: '2026-02')")

@tool(args_schema=OverageInput)
def analyze_overage_cause(user_id: str, month: str) -> str:
    """특정 월의 요금 초과 사유를 분석하기 위해 DB에서 시스템 로그 데이터를 조회합니다."""
    if not supabase:
        return "시스템 오류: 데이터베이스에 연결할 수 없습니다."
    
    try:
        response = supabase.table("billing_history").select("details").eq("user_id", user_id).eq("billing_month", month).execute()
        if response.data:
            details = response.data[0]["details"]
            # DB의 details 컬럼 내에 저장된 로그성 데이터들을 추출
            logs = {
                "usage_stats": details.get("usage_stats", "기록 없음"),
                "active_addons": details.get("active_addons", "기록 없음"),
                "billing_notes": details.get("billing_notes", "특이사항 없음")
            }
            return f"[{user_id} 님의 {month} 시스템 활동 로그 보고서]\n{logs}"
        else:
            return f"{user_id} 님의 {month} 청구 기록이 없어 분석이 불가능합니다."
    except Exception as e:
        logger.error(f"로그 데이터 조회 중 오류 발생: {e}")
        return f"로그 데이터 조회 중 오류 발생: {e}"

class ChangePlanInput(BaseModel):
    user_id: str = Field(description="요금제를 변경할 사용자의 ID (예: 'user_123')")
    target_plan: str = Field(description="변경할 요금제 이름. ('라이트', '프로', '엔터프라이즈' 중 하나 등)")
    apply_type: str = Field(description="변경 적용 방식. 'immediate'(즉시 변경), 'next_billing'(다음 결제일 적용), 'specific_month'(특정 월부터 적용) 중 하나.")
    start_month: Optional[str] = Field(default=None, description="'specific_month' 적용 방식일 경우, 적용을 시작할 연월 (형식: 'YYYY-MM', 예: '2026-04')")

@tool(args_schema=ChangePlanInput)
def change_subscription_plan(user_id: str, target_plan: str, apply_type: str, start_month: Optional[str] = None) -> str:
    """사용자의 구독 요금제를 변경하거나 변경을 예약합니다."""
    # DB 업데이트 로직 (supabase 연동)
    if not supabase:
        return "시스템 오류: 데이터베이스에 연결할 수 없어 변경을 처리할 수 없습니다."
        
    current_month_str = datetime.now().strftime("%Y-%m")
    
    # 상태값 정의
    status = "active" if apply_type == "immediate" else "pending_change"
    
    try:
        # 1. 이번 달 상태부터 먼저 조회하여 히스토리 저장을 위한 이전 요금제 파악 (details 컬럼 추가)
        response = supabase.table("billing_history").select("billing_month, subscription_info, details").eq("user_id", user_id).execute()
        
        if not response.data:
            return f"사용자 [{user_id}]의 청구 데이터가 없습니다."
            
        # 모든 월 데이터를 가져옴
        all_months_data = response.data
        
        # 이번 달의 현재 정보 찾기 (없으면 대체값)
        current_month_data = next((item for item in all_months_data if item["billing_month"] == current_month_str), None)
        
        current_info = {}
        previous_plan = "알 수 없음"
        if current_month_data and current_month_data.get("subscription_info"):
            current_info = current_month_data["subscription_info"]
            previous_plan = current_info.get("current_plan", "알 수 없음")
            
        # 2. 히스토리 로그 단일 객체 생성 (동일하게 사용)
        change_record = {
            "changed_at": datetime.now().isoformat(),
            "previous_plan": previous_plan,
            "target_plan": target_plan,
            "apply_type": apply_type
        }
        
        # 3. 업데이트할 타겟 달 결정
        months_to_update = []
        for item in all_months_data:
            b_month = item["billing_month"]
            # 문자열 크기 비교로 미래 달인지 확인 (예: '2026-03' > '2026-02')
            if apply_type == "immediate" and b_month >= current_month_str:
                months_to_update.append(item)
            elif apply_type == "next_billing" and b_month > current_month_str:
                months_to_update.append(item)
            elif apply_type == "specific_month" and start_month and b_month >= start_month:
                months_to_update.append(item)
                
        # 변경될 요금제의 기본 요금 확인 (PLAN_PRICES 참조)
        new_base_fee = PLAN_PRICES.get(target_plan.lower(), PLAN_PRICES.get(target_plan))
        
        # 4. 루프 돌면서 해당 달 업데이트 (Bulk update가 지원 안 되므로 개별 update)
        for item in months_to_update:
            b_month = item["billing_month"]
            
            # 각 달의 기존 subscription_info
            month_info = item.get("subscription_info") or {}
            change_history = month_info.get("change_history", [])
            # 이번 업데이트 추가
            change_history.append(change_record)
            
            # [추가] 실제 청구액(details) 업데이트
            details = item.get("details") or {}
            if new_base_fee is not None:
                details["base_fee"] = new_base_fee
                # 총 청구 금액 재계산: 기본료 + 초과료 + 부가료 + 할인값 (할인이 음수로 들어있음)
                exceed = details.get("exceed_fee", 0)
                extra = details.get("extra_fee", 0)
                discount = details.get("discount", 0)
                details["total"] = new_base_fee + exceed + extra + discount
            
            # 기존 subscription_info 속성들을 유지하면서 업데이트할 항목만 덮어쓰기
            new_subscription_info = month_info.copy()
            new_subscription_info.update({
                "current_plan": target_plan,
                "status": "active", # 미래 달들은 모두 적용되었다고 가정 (active)
                "updated_at": datetime.now().isoformat(),
                "change_history": change_history # 변경 이력 배열 추가
            })
            
            # DB의 billing_history 테이블에서 해당 월의 행 업데이트 (subscription_info + details 동시 업데이트)
            supabase.table("billing_history").update({
                "subscription_info": new_subscription_info,
                "details": details # 요금이 변경된 details 반영
            }).eq("user_id", user_id).eq("billing_month", b_month).execute()
            
            # 주의: 만약 'next_billing' 이라면 이번 달('current_month_str')의 상태도 
            # 'pending_change'로 업데이트해야 함. (위에 for문에서는 제외됐으므로 별도 처리)
            
        # 다음 결제일 적용 예약일 경우, "이번 달"의 상태 업데이트 (pending_change 명시, details 요금은 변경 안함)
        if apply_type == "next_billing" and current_month_data:
            c_info = current_month_data.get("subscription_info") or {}
            c_history = c_info.get("change_history", [])
            c_history.append(change_record)
            
            new_c_info = c_info.copy()
            new_c_info.update({
                "current_plan": previous_plan, # 이번달 유지 테스트
                "status": "pending_change",    # 상태만 변경
                "apply_type": apply_type,
                "updated_at": datetime.now().isoformat(),
                "change_history": c_history
            })
            
            supabase.table("billing_history").update({
                "subscription_info": new_c_info
            }).eq("user_id", user_id).eq("billing_month", current_month_str).execute()
        
        if apply_type == "immediate":
            return f"✅ [{user_id}] 님의 요금제가 ({current_month_str}월 포함 이후 모든 월) 즉시 '{previous_plan}'에서 '{target_plan}'(으)로 일괄 변경 업데이트 되었습니다."
        elif apply_type == "specific_month" and start_month:
            return f"📅 [{user_id}] 님의 요금제가 지정하신 {start_month}월 결제일 기준으로 '{previous_plan}'에서 '{target_plan}'(으)로 일괄 변경 완료되었습니다."
        else:
            return f"📅 [{user_id}] 님의 요금제가 (다음 달부터 이후 모든 월) 결제일 기준으로 '{previous_plan}'에서 '{target_plan}'(으)로 일괄 변경 예약되었습니다."
            
    except Exception as e:
        logger.error(f"요금제 일괄 변경 업데이트 중 오류 발생: {e}")
        return f"요금제 변경을 처리하는 중 연동 오류가 발생했습니다: {e}"

# ─────────────────────────────────────────
# 3. LangGraph 설정
# ─────────────────────────────────────────
class State(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]

tools = [calculate_billing, recommend_plan_by_budget, fetch_billing_history, analyze_overage_cause, change_subscription_plan]
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
llm_with_tools = llm.bind_tools(tools)
tool_map = {t.name: t for t in tools}

def billing_agent(state: State):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def tool_executor(state: State):
    last_message = state["messages"][-1]
    tool_results = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        result = tool_map[tool_name].invoke(tool_args)
        tool_results.append(
            ToolMessage(content=str(result), tool_call_id=tool_call["id"])
        )
    return {"messages": tool_results}

def should_use_tool(state: State):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_executor"
    return END

workflow = StateGraph(State)
workflow.add_node("billing_assistant", billing_agent)
workflow.add_node("tool_executor", tool_executor)
workflow.add_edge(START, "billing_assistant")
workflow.add_conditional_edges("billing_assistant", should_use_tool)
workflow.add_edge("tool_executor", "billing_assistant")

memory = MemorySaver()
app_graph = workflow.compile(checkpointer=memory)

# ─────────────────────────────────────────
# 4. FastAPI 설정
# ─────────────────────────────────────────
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """서버 상태 확인용 (Docker Liveness Probe 대응)"""
    return {"status": "ok"}

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default_user"

class MessageDict(BaseModel):
    role: str
    content: str

# SYSTEM_PROMPT 부분 수정
current_date = datetime.now().strftime("%Y-%m-%d")

SYSTEM_PROMPT = f"""
You are a professional and friendly AI Billing Assistant. 
The current system date is {current_date}. If a user mentions a month without a year (e.g., 'February'), use this current year as the default.

[Service Information]
- Lite: 9,900 KRW/month | Personal | Basic analysis, Chat support, 100 API calls
- Pro: 29,900 KRW/month | Professional/Teams | Advanced visualization, Priority support, 1,000 API calls
- Enterprise: Inquire separately | Corporate | Custom API, Dedicated manager, Unlimited calls

[Payment Methods]
- Credit Cards: All major domestic/international cards (Visa, Master, Hyundai, Samsung, etc.)
- Easy Payment: KakaoPay, NaverPay, ApplePay
- Others: Bank transfer (Corporate only), Automatic debit setup available

[User Context]
- The authenticated ID of the current customer is 'user_123'.
- Always use 'user_123' as the user_id when calling 'fetch_billing_history'.

[Strict Operational Guidelines]
1. **RESPONSE LANGUAGE**: ALWAYS respond to the user in **KOREAN**.
2. **BILLING & OVERAGE INQUIRIES**: If the user asks about their billing amounts, comparisons, OR WHY their bill is high, you MUST trigger BOTH `fetch_billing_history` AND `analyze_overage_cause` tools. Do not skip either.
3. **NO INTERMEDIATE REPLIES**: NEVER send intermediate messages like "잠시만 기다려 주세요" or "조회해 보겠습니다". Call the required tools simultaneously, gather all data, and provide ONLY ONE final, complete answer.
4. **RECOMMENDATION**: Call `recommend_plan_by_budget` immediately if the user asks for budget advice or plan recommendations.
5. **CALCULATION**: Use `calculate_billing` for multi-plan cost estimations.
6. **FORMATTING**: When providing details for a **specific single month** from `fetch_billing_history`, always emphasize the total with **'💰 총 청구 금액: [Amount]원'** at the very end of the response. For multi-month calculations (averages, totals), provide the summary clearly in the text and skip the redundant footer if the total has already been emphasized.
7. Base your final response strictly on the data analysis results from the tools.
"""

@app.post("/chat", response_model=List[MessageDict])
async def chat(request: ChatRequest):
    logger.info(f"💬 신규 채팅 요청 접수: thread_id={request.thread_id}, 내용='{request.message}'")
    config = {"configurable": {"thread_id": request.thread_id}}
    
    # 해당 스레드의 상태가 없으면 시스템 메시지로 초기화
    state = app_graph.get_state(config)
    if not state.values:
        input_data = {"messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=request.message)]}
    else:
        input_data = {"messages": [HumanMessage(content=request.message)]}

    try:
        final_state = app_graph.invoke(input_data, config=config)
        
        # 마지막 AI 메시지 추출
        ai_msg = next((m for m in reversed(final_state["messages"]) if isinstance(m, AIMessage)), None)
        
        if not ai_msg:
            logger.error(f"❌ 오류: 워크플로우를 완료했지만 AI 응답이 없습니다. (thread_id={request.thread_id})")
            raise HTTPException(status_code=500, detail={"error_code": "EMPTY_RESPONSE", "message": "AI 응답을 생성하지 못했습니다."})
        
        # 메시지 히스토리 정리 (프론트엔드 전달용)
        history = []
        for m in final_state["messages"]:
            if isinstance(m, SystemMessage): continue
            if isinstance(m, ToolMessage): continue
            if not m.content: continue # 빈 메시지(tool call 용) 제외
            
            role = "user" if isinstance(m, HumanMessage) else "assistant"
            
            # Content 처리 개선: 리스트 형태의 응답에서 텍스트만 추출 (Gemini 등 대응)
            if isinstance(m.content, str):
                content = m.content
            elif isinstance(m.content, list):
                texts = []
                for part in m.content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        texts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        texts.append(part)
                content = "".join(texts)
            else:
                content = str(m.content)
            
            # 텍스트 내용이 없으면 (예: 도구 호출용 메시지) 스킵
            if not content.strip():
                continue
                
            history.append(MessageDict(role=role, content=content))
            
        logger.info(f"✅ 채팅 처리 완료: thread_id={request.thread_id}")
        return history

    except Exception as e:
        error_msg = str(e)
        error_code, status_code = classify_error(error_msg)
        logger.error(f"❌ 채팅 처리 중 예외 발생 [{error_code}]: {error_msg} (thread_id={request.thread_id})")
        
        # HTTP 에러 응답시 구체화된 에러코드와 메시지 전달
        raise HTTPException(
            status_code=status_code, 
            detail={"error_code": error_code, "message": "서버 처리 중 문제가 발생했습니다. (내부 로그 확인)"}
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
