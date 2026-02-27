import os
from dotenv import load_dotenv, find_dotenv

# 루트 폴더의 .env 파일을 찾아 명시적으로 로드합니다.
load_dotenv(find_dotenv())

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams
from deepeval.models import DeepEvalBaseLLM
from langchain_google_genai import ChatGoogleGenerativeAI

class GoogleGemini(DeepEvalBaseLLM):
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model = ChatGoogleGenerativeAI(model=model_name)
        
    def load_model(self):
        return self.model
        
    def generate(self, prompt: str) -> str:
        return self.model.invoke(prompt).content
        
    async def a_generate(self, prompt: str) -> str:
        res = await self.model.ainvoke(prompt)
        return res.content
        
    def get_model_name(self):
        return "Google Gemini"

gemini_model = GoogleGemini()

# 1. 정합성/근거성 (Groundedness + Context Limitation) - 가중치 25
groundedness_metric = GEval(
    name="Groundedness & Context Limitation",
    model=gemini_model,
    criteria="""
    Determine if the actual output is fully grounded in the retrieval context.
    - The answer must be derivable ONLY from the provided context.
    - No external knowledge or assumptions should be used.
    - If the answer cannot be found in the context, it should be marked as 'OutsideContext' and score 0.
    """,
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.RETRIEVAL_CONTEXT],
    strict_mode=True
)

# 2. 증거가능성 (Evidenceability) - 가중치 15
evidenceability_metric = GEval(
    name="Evidenceability",
    model=gemini_model,
    criteria="""
    Evaluate whether the actual output contains specific evidence, citations, or spans from the retrieval context to support its claims.
    - High score if the output explicitly references terms, numbers, or sections from the context.
    - Low score if the output is vague without pointing to specific rationale from the context.
    """,
    evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.RETRIEVAL_CONTEXT],
)

# 3. 명확성/구체성 (Clarity) - 가중치 10
clarity_metric = GEval(
    name="Clarity and Specificity",
    model=gemini_model,
    criteria="""
    Evaluate how clear and specific the actual output is.
    - The output should avoid ambiguous pronouns or overly broad statements.
    - The scope and meaning of the answer should be unambiguous and easy to understand.
    """,
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
)

# 4. 원자성 (Atomicity) - 가중치 10
atomicity_metric = GEval(
    name="Atomicity",
    model=gemini_model,
    criteria="""
    Evaluate whether the actual output directly and concisely addresses the single core intent of the input request.
    - The response should focus on the main task without unnecessary rambling or trying to solve unasked secondary tasks.
    """,
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
)

# 5. 의미강건성 (Semantic Robustness) - 가중치 5
robustness_metric = GEval(
    name="Semantic Robustness",
    model=gemini_model,
    criteria="""
    Evaluate if the actual output effectively captures the semantic meaning of the input rather than relying on exact keyword matching.
    - The output should demonstrate an understanding of the underlying intent, even if the user phrased it unusually or without exact keywords.
    """,
    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
)

def calculate_weighted_score(TestCase) -> tuple[float, dict]:
    """
    주어진 테스트 케이스에 대해 모든 메트릭을 비동기로 평가하고,
    가중치가 적용된 100점 만점 총점을 계산합니다.
    (문서 커버리지(20)와 의도 다양성/중복(15)은 Q셋 단위 평가이므로 여기서는 개별 문항 점수만 합산 후 스케일링)
    
    가중치 구성 (개별 문항 기준 총 65점 만점 -> 100점 환산):
    - Groundedness: 25
    - Evidenceability: 15
    - Clarity: 10
    - Atomicity: 10
    - Robustness: 5
    """
    
    # 각 메트릭 측정 (measure 동작)
    groundedness_metric.measure(TestCase)
    evidenceability_metric.measure(TestCase)
    clarity_metric.measure(TestCase)
    atomicity_metric.measure(TestCase)
    robustness_metric.measure(TestCase)
    
    # GEval 스코어는 0~1 사이의 값으로 나옴
    scores = {
        "groundedness": groundedness_metric.score * 25,
        "evidenceability": evidenceability_metric.score * 15,
        "clarity": clarity_metric.score * 10,
        "atomicity": atomicity_metric.score * 10,
        "robustness": robustness_metric.score * 5
    }
    
    item_total = sum(scores.values())
    
    # 문항 단위 가중치 총합이 65이므로, 100점 만점으로 환산
    scaled_score = (item_total / 65) * 100
    
    return scaled_score, scores
