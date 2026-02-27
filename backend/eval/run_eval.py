import os
import json
import asyncio
from dotenv import load_dotenv
from supabase import create_client, Client
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from deepeval.test_case import LLMTestCase

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from eval_metrics import (
    groundedness_metric,
    evidenceability_metric,
    clarity_metric,
    atomicity_metric,
    robustness_metric
)

# 백엔드 API 대신 LangGraph 에이전트 모듈 직접 연동
from backend.main import app_graph, HumanMessage, AIMessage

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
console = Console()

def fetch_eval_data_from_db():
    response = supabase.table("evaluation_dataset").select("*").execute()
    return response.data

async def generate_agent_response(question: str, user_id: str) -> str:
    """Agent에 비동기로 질문을 던져 응답을 가져옵니다."""
    config = {"configurable": {"thread_id": f"eval_{user_id}"}}
    input_data = {"messages": [HumanMessage(content=question)]}
    
    final_state = await app_graph.ainvoke(input_data, config=config)
    ai_msg = next((m for m in reversed(final_state["messages"]) if isinstance(m, AIMessage)), None)
    
    if not ai_msg:
        return "응답 없음"
        
    if isinstance(ai_msg.content, str):
        return ai_msg.content
    elif isinstance(ai_msg.content, list):
        return "".join([part.get("text", "") for part in ai_msg.content if isinstance(part, dict)])
    return str(ai_msg.content)

async def measure_metric_with_retry(metric, test_case, retries=3):
    """Gemini API 429 에러(Rate Limit) 발생 시 대기 후 재시도하는 래퍼 함수"""
    for attempt in range(retries):
        try:
            await metric.a_measure(test_case)
            return
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                # 콘솔에 덮어쓰기 형태로 잠시 대기를 알림
                if attempt < retries - 1:
                    await asyncio.sleep(20) # 무료 티어 API 할당량 리셋 대기
                else:
                    raise e
            else:
                raise e

async def main():
    console.print(Panel("[bold green]🚀 요금 안내 AI 모델 (LLM as a Judge) 자동 채점 파이프라인[/bold green]", expand=False))
    
    with console.status("[bold cyan]📥 Supabase에서 평가 데이터셋 조회 중...[/bold cyan]"):
        dataset = fetch_eval_data_from_db()

    if not dataset:
        console.print("[bold red]❌ 평가할 데이터가 DB에 없습니다.[/bold red]")
        return

    eval_subset = dataset[:5]
    console.print(f"✅ 평가 진행 문항 수: [bold yellow]{len(eval_subset)}[/bold yellow]건\n")
    
    total_scaled_score = 0
    results_log = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
        transient=False
    ) as progress:
        
        main_task = progress.add_task("[bold cyan]전체 평가 진행률", total=len(eval_subset))
        
        for idx, data in enumerate(eval_subset):
            q_id = data.get("id", str(idx))
            question = data["question"]
            expected_ans = data["expected_answer"]
            context_refs = data.get("context_references", [])
            
            # API 제한 방지를 위한 고정 딜레이 (무료 티어 15 RPM 고려)
            if idx > 0:
                progress.update(main_task, description=f"[cyan]문항 {idx+1}/{len(eval_subset)} 준비 중 (API 쿨다운 대기)...")
                await asyncio.sleep(15)

            progress.update(main_task, description=f"[cyan]문항 {idx+1}/{len(eval_subset)} 평가 중: [white]{question[:15]}...")
            
            # 시스템에 질문 던지기 (비동기)
            actual_answer = await generate_agent_response(question, q_id)
            
            # DeepEval용 LLMTestCase 생성
            test_case = LLMTestCase(
                input=question,
                actual_output=actual_answer,
                expected_output=expected_ans,
                retrieval_context=[json.dumps(context_refs)] if context_refs else ["No explicit context provided"]
            )
            
            try:
                # 각 메트릭마다 Rate limit 429 회피용 재시도 함수 사용 및 약간의 딜레이
                await measure_metric_with_retry(groundedness_metric, test_case)
                await asyncio.sleep(3)
                
                await measure_metric_with_retry(evidenceability_metric, test_case)
                await asyncio.sleep(3)
                
                await measure_metric_with_retry(clarity_metric, test_case)
                await asyncio.sleep(3)
                
                await measure_metric_with_retry(atomicity_metric, test_case)
                await asyncio.sleep(3)
                
                await measure_metric_with_retry(robustness_metric, test_case)
                
                # 가중치 계산 체계
                g_score = groundedness_metric.score * 25
                e_score = evidenceability_metric.score * 15
                c_score = clarity_metric.score * 10
                a_score = atomicity_metric.score * 10
                r_score = robustness_metric.score * 5
                
                item_score = g_score + e_score + c_score + a_score + r_score
                scaled_100 = (item_score / 65) * 100
                total_scaled_score += scaled_100
                
                results_log.append({
                    "id": q_id,
                    "score": scaled_100,
                    "Grd": g_score, "Evi": e_score, "Cla": c_score, "Ato": a_score, "Rob": r_score
                })
                
            except Exception as e:
                console.print(f"[bold red]❌ 채점 오류 발생 (문항 {idx+1}): {e}[/bold red]")
                
            # 평가 한 건 완료마다 게이지 바 채우기
            progress.advance(main_task)

    # 평가 결과 테이블 UI 구성
    print("\n")
    table = Table(title="📊 문항 단위 개별 평가 결과 요약", show_header=True, header_style="bold magenta")
    table.add_column("문항 ID", style="dim", width=10)
    table.add_column("총점(100)", justify="right", style="bold green")
    table.add_column("정합(25)", justify="right")
    table.add_column("증거(15)", justify="right")
    table.add_column("명확(10)", justify="right")
    table.add_column("원자(10)", justify="right")
    table.add_column("강건(5)", justify="right")

    for log in results_log:
        table.add_row(
            str(log["id"])[:8],
            f"{log['score']:.1f}",
            f"{log['Grd']:.1f}", f"{log['Evi']:.1f}", f"{log['Cla']:.1f}", f"{log['Ato']:.1f}", f"{log['Rob']:.1f}"
        )

    console.print(table)
    
    if results_log:
        final_avg = total_scaled_score / len(results_log)
        console.print(Panel(f"[bold gold1]🏆 미니 배치(5건) 최종 평균 평가 점수: {final_avg:.1f} / 100점[/bold gold1]", expand=False))

if __name__ == "__main__":
    asyncio.run(main())
