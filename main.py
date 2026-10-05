from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import pymysql
import random
import json  # 匯入 json 模組以解析資料庫中的 JSON 字串

# 讓程式啟動時去讀取 .env 檔案
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 資料庫連線設定 (整合環境變數與預設值)
db_config = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'fjcu_hospital'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'cursorclass': pymysql.cursors.DictCursor
}

@app.get("/")
def read_root():
    return {"message": "急診系統 API 伺服器已啟動！"}

@app.get("/api/patients")
def get_patients():
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # 整合兩邊的 SQL 查詢欄位（包含年齡、生日、血氧等完整資訊）
            sql = """
                SELECT 
                    p.patient_id, 
                    p.name, 
                    p.gender,
                    p.age,
                    p.birth_date,
                    
                    t.triage_id,
                    t.triage_level AS final_level,
                    t.chief_complaint,
                    
                    v.measured_at,
                    v.temperature, 
                    v.heart_rate,
                    v.respiratory_rate,
                    v.systolic_bp AS blood_pressure_sys, 
                    v.diastolic_bp AS blood_pressure_dia, 
                    v.spo2
                FROM patients p
                LEFT JOIN triage_records t ON p.patient_id = t.patient_id
                LEFT JOIN vital_signs v ON p.patient_id = v.patient_id
            """
            cursor.execute(sql)
            results = cursor.fetchall()
        connection.close()

        # AI 風險評分邏輯
        for row in results:
            if row.get('measured_at'):
                row['measured_at'] = row['measured_at'].strftime("%Y-%m-%d %H:%M:%S")
                
            score = 0
            if row.get('final_level'):
                level = int(row['final_level'])
                if level == 1: score = random.randint(90, 99)
                elif level == 2: score = random.randint(75, 89)
                elif level == 3: score = random.randint(40, 74)
                else: score = random.randint(10, 39)
            
            if row.get('spo2') and int(row['spo2']) < 95:
                score = min(99, score + 15)
                
            row['risk_score'] = score

        return results
    except Exception as e:
        print("資料庫連線錯誤:", str(e))
        return {"error": str(e)}
# ---------------------------------------------------------
# 新增：讀取醫生 AI 預測結果數據的 API (對應 ai_triage_predictions 表)
# ---------------------------------------------------------
@app.get("/api/predictions")
def get_predictions():
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            # 按重症風險機率高至低排序
            sql = "SELECT * FROM ai_triage_predictions ORDER BY serious_risk_pct DESC"
            cursor.execute(sql)
            results = cursor.fetchall()
        connection.close()

        # 處理日期時間格式與 JSON 解析
        for row in results:
            # ★ 讀取資料庫中的 arrival_time 並格式化為 HH:MM (例如 10:25)
            if row.get('arrival_time'):
                row['arrivalTime'] = row['arrival_time'].strftime("%H:%M")
            else:
                row['arrivalTime'] = "10:00"

            if row.get('admit_distribution'):
                try:
                    row['admit_distribution'] = json.loads(row['admit_distribution'])
                except Exception:
                    pass
            # ★ 確保前端可以直接讀取 complaint（對應資料庫的 complaint 欄位）
            # 如果資料庫欄位名稱大小寫或拼寫不同，也可以在這裡做統一對應
            if row.get('complaint'):
                row['complaint'] = row['complaint']
            else:
                row['complaint'] = "無特殊主訴紀錄"


        return results
    except Exception as e:
        print("資料庫連線錯誤:", str(e))
        return {"error": str(e)}