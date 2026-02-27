import json
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# 환경변수에서 Supabase 접속 정보 로드
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ 환경 변수에 SUPABASE_URL 또는 SUPABASE_KEY가 설정되지 않았습니다.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_json_data(filepath: str) -> list:
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def main():
    print("🚀 로컬 QA 데이터셋을 Supabase로 업로드를 시작합니다...")
    
    base_dir = os.path.dirname(__file__)
    manual_data_path = os.path.join(base_dir, "qa_dataset.json")
    synthetic_data_path = os.path.join(base_dir, "qa_dataset_synthetic.json")
    
    # 두 JSON 데이터 병합
    manual_data = load_json_data(manual_data_path)
    synthetic_data = load_json_data(synthetic_data_path)
    
    # is_synthetic 플래그 추가
    for item in manual_data:
        item["is_synthetic"] = False
        if "id" in item:
            del item["id"] # DB 자동생성 활용

    for item in synthetic_data:
        item["is_synthetic"] = True
        if "id" in item:
            del item["id"]

    combined_data = manual_data + synthetic_data
    
    if not combined_data:
        print("❌ 업로드할 데이터가 없습니다.")
        return

    try:
        # Supabase bulk insert
        response = supabase.table("evaluation_dataset").insert(combined_data).execute()
        print(f"✅ 총 {len(combined_data)}개의 데이터가 'evaluation_dataset' 테이블에 성공적으로 업로드되었습니다.")
    except Exception as e:
        print(f"❌ 데이터베이스 업로드 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
