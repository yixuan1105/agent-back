from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL", "https://xbrtibieffiummxnrtds.supabase.co")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY", "sb_publishable_vne8tVEpKGmZK3ss67dWUg_bzHEkdXc")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/api/predictions")
def get_predictions():
    try:
        response = supabase.table("hospital_data").select("*").execute()
        results = response.data

        # 處理到診時間格式化
        for row in results:
            if row.get('arrival_time'):
                try:
                    # 將 Supabase 的 ISO 時間格式轉為 datetime 物件
                    iso_str = row['arrival_time'].replace('Z', '+00:00')
                    dt = datetime.fromisoformat(iso_str)
                    # 格式化為 時:分 (例如 10:39)
                    row['arrivalTime'] = dt.strftime("%H:%M")
                except Exception:
                    row['arrivalTime'] = "10:00"
            else:
                row['arrivalTime'] = "10:00"

        return results
    except Exception as e:
        print("資料讀取錯誤:", str(e))
        return {"error": str(e)}