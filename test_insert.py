import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# 載入 .env 環境變數
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 初始化 Supabase 客戶端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 測試寫入資料
sample_data = [
    {
        "date": "2026-09-17",
        "ticker": "2330",
        "close_price": 980.0,
        "bias5": 1.25,
        "k_value": 78.5,
        "d_value": 65.2,
    },
    {
        "date": "2026-09-17",
        "ticker": "2317",
        "close_price": 185.0,
        "bias5": 0.85,
        "k_value": 82.1,
        "d_value": 70.4,
    },
]

try:
    response = (
        supabase.table("stock_selection_log").insert(sample_data).execute()
    )
    print("✅ 成功寫入資料！", response.data)
except Exception as e:
    print("❌ 寫入失敗，請檢查 RLS Policy 或環境變數：", e)