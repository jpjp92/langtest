import json
import os
import random
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

# 사용할 데이터셋 형식 정의 (Pydantic)
class QAPair(BaseModel):
    id: str = Field(description="고유 ID (예: 'syn_qa_001')")
    topic_path: str = Field(description="카테고리 경로 (예: '요금 > 모바일 > 라이트 요금제 > 요금안내')")
    question: str = Field(description="평가용 질문 (다양한 의도와 표현 방식 포함)")
    expected_answer: str = Field(description="모범 답안 (핵심 내용)")
    context_references: List[str] = Field(description="질문의 정확한 근거가 되는 시스템 프롬프트의 실제 문장/본문 텍스트 목록")
    intent_type: str = Field(description="의도 유형 (factoid, why, list, boolean, how, procedure, multi-turn 등)")

class QADataset(BaseModel):
    qa_pairs: List[QAPair] = Field(description="생성된 질문 답변 쌍 목록")

# Gemini LLM 초기화 (Structured Output 적용)
eval_api_key = os.getenv("EVAL_GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=eval_api_key)
structured_llm = llm.with_structured_output(QADataset)

# 공통 컨텍스트
CONTEXT = """
[서비스 정보]
- 라이트 요금제: 9,900원/월 (기본 분석, 채팅 지원, API 100회)
- 프로 요금제: 29,900원/월 (고급 시각화, 우선 지원, API 1,000회)
- 엔터프라이즈: 별도 문의 (맞춤 API, 전담 매니저, 무제한)

[기능 및 도구 가이드]
- 요금 자동 계산 (calculate_billing): 요금제별 개월 수 합산 산출
- 요금 내역 조회 (fetch_billing_history): 특정 연월 청구서(기본료, 초과 이용료, 할인액 등) 확인
- 추가 분석 (analyze_overage_cause): 요금이 초과된 상세 사유 (API 호출 초과, 부가서비스 등) 분석
- 요금제 맞춤 추천 (recommend_plan_by_budget): 예산과 기간 입력에 맞춰 최적 요금제 계산 제안
- 요금제 변경 (change_subscription_plan): 라이트/프로 요금제로 즉시 변경, 혹은 다음 달, 특정 달로 예약

[결제수단]
- 신용카드: 국내/해외 카드 (비자, 마스터, 삼성 등)
- 간편결제: 카카오페이, 네이버페이, 애플페이
- 기타: 계좌이체, 자동이체
"""

def generate_base_qa(count=5) -> List[QAPair]:
    print(f"--- 1. 기본 합성 데이터 생성 ({count}개) ---")
    prompt = f"""
    당신은 AI 평가용 Q&A 데이터셋을 구축하는 전문가입니다.
    아래 [기술 컨텍스트]를 바탕으로, 지능형 요금 안내 에이전트를 평가하기 위한 질문-답변 세트 {count}개를 생성해주세요.
    
    1. 각 질문은 컨텍스트를 벗어나지 않아야 합니다. (Groundedness)
    2. 질문 의도(intent_type)가 한쪽으로 치우치지 않도록 골고루 섞어주세요.
       (예: 단순 사실 확인(factoid), 이유 분석(why), 목록 나열(list), 예/아니오(boolean), 절차나 방법(how/procedure))
    3. 동일한 의미를 묻더라도 다른 어휘(동의어)로 변형한 질문 등 다양성을 높이세요.
    4. [중요] context_references 에는 단순히 카테고리나 섹션 이름만 넣지 말고, 답변의 확실한 근거가 되는 **실제 컨텍스트 본문 문장(Text)**을 그대로 복사해서 넣어주세요. (예: "라이트 요금제: 9,900원/월 (기본 분석, 채팅 지원, API 100회)")
    
    [기술 컨텍스트]
    {CONTEXT}
    """
    try:
        response = structured_llm.invoke([
            SystemMessage(content="You are an expert in creating diverse FAQ and Golden QA datasets."),
            HumanMessage(content=prompt)
        ])
        for qa in response.qa_pairs:
            qa.id = f"syn_base_{random.randint(1000, 9999)}"
        return response.qa_pairs
    except Exception as e:
        print(f"❌ 기본 데이터 생성 중 오류 발생: {e}")
        return []

def augment_by_tone(base_qa: List[QAPair]) -> List[QAPair]:
    print(f"--- 2. 어조 변환(Tone Shift) 증강 ({len(base_qa)}개) ---")
    augmented = []
    tones = [
        "10대들이 카톡에서 쓸 법한 줄임말과 유행어를 포함하여",
        "매우 화가 난 고객이 클레임을 거는 공격적인 어조와 다급함을 담아서",
        "오타 및 문법적 오류를 1~2군데 의도적으로 포함하여 모바일에서 급하게 친 것처럼",
        "매우 격식있고 정중한 비즈니스 파트너의 이메일 어조로",
        "IT 전문가가 기술적인 뉘앙스를 풍기며 따져 묻는 것처럼"
    ]
    
    for qa in base_qa:
        target_tone = random.choice(tones)
        prompt = f"""
        당신은 다양한 페르소나를 연기하는 평가용 데이터 생성기입니다.
        다음 원본 질문을 **{target_tone}** 변형하여 새 질문을 하나만 작성해주세요.
        주의: 질문의 핵심 의도(Intent)나 묻고자 하는 서비스 내용은 절대 바꾸거나 없애지 말고 어조만 바꿔야 합니다.
        
        원본 질문: "{qa.question}"
        """
        try:
            res = llm.invoke(prompt)
            new_question = res.content.strip()
            
            # 따옴표 제거 정리
            if new_question.startswith('"') and new_question.endswith('"'):
                new_question = new_question[1:-1]
                
            # 빈 결과 방어 로직
            if not new_question or len(new_question.strip()) < 2:
                print(f"⚠️ 어조 변환 실패 (빈 응답). 원본 유지: {qa.id}")
                new_question = qa.question

            new_qa = qa.model_copy()
            new_qa.id = f"syn_tone_{random.randint(1000, 9999)}"
            new_qa.question = new_question
            
            augmented.append(new_qa)
        except Exception as e:
            print(f"⚠️ 어조 변환 오류: {qa.id} - {e}")
            
    return augmented

def augment_by_variable_swap() -> List[QAPair]:
    print("--- 3. 메타데이터 변수 치환(Variable Swap) 증강 ---")
    
    templates = [
        {
            "topic_path": "요금 > 추천",
            "intent_type": "how",
            "context_references": [
                "- 요금제 맞춤 추천 (recommend_plan_by_budget): 예산과 기간 입력에 맞춰 최적 요금제 계산 제안",
                "- 라이트 요금제: 9,900원/월 (기본 분석, 채팅 지원, API 100회)",
                "- 프로 요금제: 29,900원/월 (고급 시각화, 우선 지원, API 1,000회)"
            ],
            "q_template": "제 한 달 예산이 {budget}원인데, {plan} 요금제를 써도 괜찮을지 추천 좀 해볼래요?",
            "a_template": "예산 {budget}원을 기준으로 {plan} 요금제의 사용 적합성 여부와 가장 예산에 잘 맞는 최적의 플랜을 계산하여 추천해 드리겠습니다."
        },
        {
            "topic_path": "요금 > 내역조회",
            "intent_type": "factoid",
            "context_references": ["- 요금 내역 조회 (fetch_billing_history): 특정 연월 청구서(기본료, 초과 이용료, 할인액 등) 확인"],
            "q_template": "나 저번 {month}월에 청구서 요금 얼마나 나왔는지 확인해줘. 기본료랑 다 합쳐서.",
            "a_template": "요청하신 시간 기준 {month}월에 대한 요금 청구 내역(기본료, 초과 이용료 등)을 조회하여 상세히 알려드리겠습니다."
        },
        {
            "topic_path": "결제 > 변경",
            "intent_type": "procedure",
            "context_references": ["- 신용카드: 국내/해외 카드 (비자, 마스터, 삼성 등)", "- 간편결제: 카카오페이, 네이버페이, 애플페이"],
            "q_template": "결제 수단을 좀 바꾸려고 하는데요. {payment} 말고 다른 카드로 결제해도 되나요?",
            "a_template": "현재 결제 수단을 {payment}에서 변경하시려는군요. 결제 수단은 비자, 마스터, 삼성 등의 신용카드뿐만 아니라 네이버페이, 카카오페이, 애플페이 같은 간편결제와 계좌이체 등 다양한 방법으로 지원하고 있습니다."
        }
    ]
    
    augmented = []
    budgets = ["3만원", "5만원", "10만원", "15만원"]
    plans = ["라이트", "프로", "엔터프라이즈", "가장 싼"]
    months = ["1", "2", "3", "5", "10", "12"]
    payments = ["카카오페이", "네이버페이", "애플페이", "삼성카드", "계좌이체"]
    
    # 각 템플릿별로 4개씩 증강 생성
    for t in templates:
        for _ in range(4):
            q, a = t["q_template"], t["a_template"]
            
            if "{budget}" in q:
                b, p = random.choice(budgets), random.choice(plans)
                q, a = q.format(budget=b, plan=p), a.format(budget=b, plan=p)
            elif "{month}" in q:
                m = random.choice(months)
                q, a = q.format(month=m), a.format(month=m)
            elif "{payment}" in q:
                pay = random.choice(payments)
                q, a = q.format(payment=pay), a.format(payment=pay)
                
            qa = QAPair(
                id=f"syn_var_{random.randint(1000, 9999)}",
                topic_path=t["topic_path"],
                question=q,
                expected_answer=a,
                context_references=t["context_references"],
                intent_type=t["intent_type"]
            )
            augmented.append(qa)
            
    return augmented

def generate_multiturn_qa(count=5) -> List[QAPair]:
    print(f"--- 4. 멀티턴 대화증강 (Multi-turn Context Simulation) ({count}개) ---")
    prompt = f"""
    당신은 AI 평가용 Q&A 데이터셋을 구축하는 전문가입니다.
    아래 [기술 컨텍스트]를 바탕으로, 단순한 단일 질문이 아닌 전후 맥락(Multi-turn)을 담은 질문-답변 세트 {count}개를 생성해주세요.
    
    [핵심 조건]
    1. 사용자가 앞선 대화의 내용을 지칭하는 대명사("그거", "저번에 말한 거", "그다음 거")를 사용하거나, 이전에 진행하던 작업을 이어서 질문하는 상황이어야 합니다.
    2. 평가용 질문(question) 에는 [이전 대화 맥락: ...] 형태의 전제 상황과, 사용자의 새로운 후속 질문을 연달아 작성해주세요.
    3. expected_answer 에는 AI 에이전트가 이전 맥락을 파악하고 정확히 응답해야 할 모범 답안을 작성하세요.
    4. 질문 의도(intent_type)는 모두 "multi-turn" 으로 지정해주세요.
    
    [형식 예시]
    question: "[이전 대화 맥락: 사용자: 요금제 제일 싼 거 뭐야? -> 에이전트: 라이트 요금제 9900원입니다.] 사용자: 그거 말고 그다음으로 저렴한 건 얼마야?"
    expected_answer: "라이트 요금제 다음으로 저렴한 요금제는 프로 요금제로, 월 29,900원입니다."
    
    [기술 컨텍스트]
    {CONTEXT}
    """
    try:
        response = structured_llm.invoke([
            SystemMessage(content="You are an expert in creating diverse multi-turn interaction datasets."),
            HumanMessage(content=prompt)
        ])
        for qa in response.qa_pairs:
            qa.id = f"syn_multi_{random.randint(1000, 9999)}"
            qa.intent_type = "multi-turn"
        return response.qa_pairs
    except Exception as e:
        print(f"❌ 멀티턴 대화 증강 오류: {e}")
        return []

def main():
    print("🚀 합성 데이터(Synthetic QA) 자동 증강 파이프라인을 시작합니다...")
    
    final_dataset = []
    
    # 1. Base QA 뼈대 생성 (12개)
    base_qa = generate_base_qa(count=12)
    final_dataset.extend(base_qa)
    
    # 2. Base QA를 바탕으로 스타일 및 어조 변환 복제 (12개 추가생성)
    if base_qa:
        tone_qa = augment_by_tone(base_qa)
        final_dataset.extend(tone_qa)
    
    # 3. 변수 치환(Variable Swap) (12개 추가생성)
    var_qa = augment_by_variable_swap()
    final_dataset.extend(var_qa)
    
    # 4. 멀티턴 생성 (10개 추가생성)
    multi_qa = generate_multiturn_qa(count=10)
    final_dataset.extend(multi_qa)
    
    # 5. 파일 저장
    filepath = os.path.join(os.path.dirname(__file__), "qa_dataset_synthetic.json")
    
    # 저장 시 id 중복 가능성을 배제하고 일괄 Pydantic Dump
    output_data = [pair.model_dump() for pair in final_dataset]
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    print(f"\\n✅ 모든 데이터 증강 완료!")
    print(f"총 {len(final_dataset)}개의 합성 데이터 쌍이 '{filepath}'에 저장되었습니다.")
    print("이후 `upload_to_supabase.py` 스크립트를 실행하여 데이터베이스에 일괄 적재(Bulk Insert) 하세요.")

if __name__ == "__main__":
    main()
