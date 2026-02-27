import json
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
import operator
from typing import List
from dotenv import load_dotenv

load_dotenv()

# 사용할 데이터셋 형식 정의 (Pydantic)
class QAPair(BaseModel):
    id: str = Field(description="고유 ID (예: 'syn_qa_001')")
    topic_path: str = Field(description="카테고리 경로 (예: '요금 > 모바일 > 라이트 요금제 > 요금안내')")
    question: str = Field(description="평가용 질문 (다양한 의도와 표현 방식 포함)")
    expected_answer: str = Field(description="모범 답안 (핵심 내용)")
    context_references: List[str] = Field(description="질문의 근거가 되는 시스템 프롬프트 섹션 또는 도구 이름 목록")
    intent_type: str = Field(description="의도 유형 (factoid, why, list, boolean, how, procedure 등)")

class QADataset(BaseModel):
    qa_pairs: List[QAPair] = Field(description="생성된 질문 답변 쌍 목록 (10~15개 요청)")

# Gemini LLM 초기화 (Structured Output 적용)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
structured_llm = llm.with_structured_output(QADataset)

def generate_synthetic_qa() -> None:
    print("🚀 합성 데이터(Synthetic QA) 생성을 시작합니다...")
    
    # 텍스트 컨텍스트 (실제 시스템 프롬프트 및 도구 기반)
    context = """
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
    
    prompt = f"""
    당신은 AI 평가용 Q&A 데이터셋을 구축하는 전문가입니다.
    아래 [기술 컨텍스트]를 바탕으로, 지능형 요금 안내 에이전트를 평가하기 위한 질문-답변 세트 10개를 생성해주세요.
    
    1. 각 질문은 컨텍스트를 벗어나지 않아야 합니다. (Groundedness)
    2. 질문 의도(intent_type)가 한쪽으로 치우치지 않도록 골고루 섞어주세요.
       (예: 단순 사실 확인(factoid), 이유 분석(why), 목록 나열(list), 예/아니오(boolean), 절차나 방법(how/procedure))
    3. 동일한 의미를 묻더라도 다른 어휘(동의어)로 변형한 질문 등 다양성을 높이세요.
    
    [기술 컨텍스트]
    {context}
    """
    
    try:
        response = structured_llm.invoke([
            SystemMessage(content="You are an expert in creating diverse FAQ and Golden QA datasets."),
            HumanMessage(content=prompt)
        ])
        
        filepath = os.path.join(os.path.dirname(__file__), "qa_dataset_synthetic.json")
        
        # Pydantic 객체를 JSON(dict)으로 파싱 후 파일 저장
        output_data = [pair.model_dump() for pair in response.qa_pairs]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ 총 {len(output_data)}개의 합성 데이터 쌍이 생성되어 '{filepath}'에 저장되었습니다.")
        
    except Exception as e:
        print(f"❌ 데이터 자동 생성 중 오류 발생: {e}")

if __name__ == "__main__":
    generate_synthetic_qa()
