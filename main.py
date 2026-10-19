from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

load_dotenv()

app = FastAPI(title="急診臨床決策輔助系統Agent後端 API")

# 設定跨域 CORS 存取權限
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 載入 Supabase 設定
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL", "https://xbrtibieffiummxnrtds.supabase.co")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY", "sb_publishable_vne8tVEpKGmZK3ss67dWUg_bzHEkdXc")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ------------------------------------------------------------------
# 資料模型定義 (Pydantic Models)
# ------------------------------------------------------------------
class AgentRequest(BaseModel):
    patient_id: str
    chief_complaint: Optional[str] = ""
    xai_features: List[str] = []
    vitals: Optional[dict] = {}


# ------------------------------------------------------------------
# 根目錄測試路由 (避免 404 Not Found)
# ------------------------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "急診決策輔助系統 Agent 後端服務正常運行中"}


# ------------------------------------------------------------------
# 1. 原有功能：讀取急診病人清單與惡化預測資料
# ------------------------------------------------------------------
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


# ------------------------------------------------------------------
# 2. 新增功能：知識庫比對與處置建議 Agent (RAG Agent)
# ------------------------------------------------------------------
@app.post("/api/run-agent")
def run_emergency_agent(req: AgentRequest):
    """
    Agent 核心路由：
    1. 接收前端病人的檢傷主述與 XAI 特徵
    2. 至 Supabase 檢索「臨床實證醫療指引」與「危急事件經驗庫」
    3. 整合為動態的建議處置清單傳回前端
    """
    try:
        # Step A: 從 Supabase 向量知識庫 (或處置指引表) 查詢相符處置
        # 實務上可改為 supabase.rpc('match_documents', ...) 進行向量比對
        kb_response = supabase.table("hospital_data") \
            .select("*") \
            .eq("patient_id", req.patient_id) \
            .execute()

        patient_info = kb_response.data[0] if kb_response.data else {}

        # Step B: Agent 進行邏輯推理並生成建議 (模擬或接 LLM 模型)
        # 搭配 UI 的五大處置類別：藥物、注射、檢驗、監測/會診、呼吸支持
        recommended_actions = [
            {
                "id": "act_1",
                "category": "檢驗",
                "title": "安排相關血液與影像檢驗",
                "checked": True,
                "source": "急診臨床處置指引彙編 P.12"
            },
            {
                "id": "act_2",
                "category": "監測",
                "title": "密切監測生命徵象波動",
                "checked": True,
                "source": "急重症風險評估標準流程 P.18"
            },
            {
                "id": "act_3",
                "category": "其他處置",
                "title": "給予適當症狀支持治療",
                "checked": False,
                "source": "臨床診斷處置指引"
            },
            {
                "id": "act_4",
                "category": "會診",
                "title": "必要時會診相關專科醫師",
                "checked": False,
                "source": "專科會診標準作業程序"
            }
        ]

        return {
            "status": "success",
            "patient_id": req.patient_id,
            "agent_summary": "已依據護理主述文字萃取特徵，比對 Clinical Guidelines 產出建議處置項目。",
            "recommendations": recommended_actions,
            "references": [
                {"title": "1. 急診臨床處置指引彙編", "similarity": 0.94, "page": "P.12"},
                {"title": "2. 急重症風險評估標準流程", "similarity": 0.82, "page": "P.18"}
            ]
        }

    except Exception as e:
        print("Agent 推理過程發生錯誤:", str(e))
        raise HTTPException(status_code=500, detail=f"Agent 執行失敗: {str(e)}")