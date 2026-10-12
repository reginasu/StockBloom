import datetime
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo

import streamlit as st
import pandas as pd
import yfinance as yf
import requests

try:
    from supabase import create_client
except Exception:
    create_client = None

#台股爆量突破 + 均線糾結 飆股篩選器
# --- 頁面配置 ---
st.set_page_config(
    page_title="台股飆股起漲訊號篩選器",
    page_icon="🚀",
    layout="wide"
)


def get_app_secret(key):
    try:
        value = st.secrets.get(key)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(key)


@st.cache_resource
def init_supabase():
    supabase_url = get_app_secret("SUPABASE_URL")
    supabase_key = get_app_secret("SUPABASE_KEY")
    if not supabase_url or not supabase_key or create_client is None:
        return None
    return create_client(supabase_url, supabase_key)


def save_results_to_supabase(df):
    if df is None or df.empty:
        return True, "沒有符合條件的資料需要記錄。"

    try:
        supabase = init_supabase()
        if supabase is None:
            return False, "Supabase 未設定，請檢查 SUPABASE_URL 與 SUPABASE_KEY。"

        now_taipei = datetime.datetime.now(ZoneInfo("Asia/Taipei"))
        today = now_taipei.date().isoformat()
        created_at = now_taipei.astimezone(datetime.timezone.utc).isoformat()
        records = []
        for _, row in df.iterrows():
            market_suffix = ".TW" if row["市場類型"] == "上市" else ".TWO"
            records.append({
                "date": today,
                "ticker": f"{row['股票代碼']}{market_suffix}",
                "stock_name": str(row["股票名稱"]),
                "close_price": float(row["收盤價"]),
                "price_change_pct": float(row["今日漲幅(%)"]),
                "volume_multiplier": float(row["爆量倍數"]),
                "volume_lots": int(row["成交量(張)"]),
                "created_at": created_at,
            })

        supabase.table("stock_breakout_scan_log").upsert(
            records, on_conflict="date,ticker"
        ).execute()
        return True, f"已記錄 {len(records)} 筆結果至 Supabase。"
    except Exception as error:
        return False, f"Supabase 寫入失敗：{error}"


@st.cache_data(ttl=86400)
def get_taiwan_stock_list():
    """
    從證交所 API 抓取最新「上市」股票清單 (快取 24 小時)
    上櫃 API 目前失效，因此暫時只保留上市資料。
    """
    def safe_json_fetch(url, source_name):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception:
            return []

    url_twse = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"
    data_twse = safe_json_fetch(url_twse, "上市")

    stock_list = []
    stock_name_map = {}

    for item in data_twse if isinstance(data_twse, list) else []:
        code = item.get('Code', '')
        name = item.get('Name', '')
        if len(code) == 4 and code.isdigit():
            stock_list.append(f"{code}.TW")
            if name:
                stock_name_map[f"{code}.TW"] = name

    return stock_list, stock_name_map


def check_breakout_signal(ticker_symbol, vol_mult, price_change_min, stock_name_map=None):
    """
    單一股票診斷邏輯
    """
    try:
        df = yf.download(ticker_symbol, period="100d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if len(df) < 60:
            return None

        # 指標計算
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['V_MA5'] = df['Volume'].rolling(window=5).mean()

        today = df.iloc[-1]
        yesterday = df.iloc[-2]
        highest_20d = df['Close'].iloc[-21:-1].max()

        # 核心判斷
        cond_volume = today['Volume'] >= (yesterday['V_MA5'] * vol_mult)
        cond_price_high = today['Close'] > highest_20d
        pct_change = ((today['Close'] - yesterday['Close']) / yesterday['Close']) * 100
        cond_strong_k = pct_change >= price_change_min
        
        # 前日均線糾結
        ma_list = [yesterday['MA5'], yesterday['MA10'], yesterday['MA20']]
        ma_max, ma_min = max(ma_list), min(ma_list)
        cond_ma_tangled = ((ma_max - ma_min) / ma_min) <= 0.035

        if cond_volume and cond_price_high and cond_strong_k and cond_ma_tangled:
            volume_multiplier = round(today['Volume'] / yesterday['V_MA5'], 2)
            clean_symbol = ticker_symbol.replace(".TW", "").replace(".TWO", "")
            company_name = (stock_name_map or {}).get(ticker_symbol, "")
            return {
                "股票代碼": clean_symbol,
                "股票名稱": company_name,
                "市場類型": "上市" if ".TW" in ticker_symbol else "上櫃",
                "收盤價": round(float(today['Close']), 2),
                "今日漲幅(%)": round(float(pct_change), 2),
                "爆量倍數": float(volume_multiplier),
                "成交量(張)": int(today['Volume'] // 1000)
            }
    except Exception:
        return None
    return None

# --- UI 介面設計 ---
st.title("🚀 台股爆量突破 + 均線糾結 飆股篩選器")
st.markdown("針對全台股（上市與上櫃）自動進行多線程掃描，篩選近 20 日新高、爆量突破且前日均線糾結之標的。")

# 側邊欄：篩選參數設定
st.sidebar.header("⚙️ 條件參數設定")
max_workers = st.sidebar.slider("平行處理線程數", min_value=10, max_value=40, value=25)
vol_mult = st.sidebar.number_input("成交量放大倍數 (比5日均量)", min_value=1.5, max_value=5.0, value=2.5, step=0.5)
price_change_min = st.sidebar.number_input("今日最低漲幅 (%)", min_value=2.0, max_value=9.0, value=4.5, step=0.5)

# 初始化全市場清單
with st.spinner("正連線至證交所與櫃買中心獲取最新股票清單..."):
    all_stocks, stock_name_map = get_taiwan_stock_list()

st.sidebar.success(f"目前全市場標的：{len(all_stocks)} 檔")

# 執行掃描按鈕
if st.button("🔍 開始全市場飆股掃描", type="primary"):
    total_stocks = len(all_stocks)
    
    # 建立進度條元件
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    completed_count = 0
    
    # 多線程執行
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_stock = {
            executor.submit(check_breakout_signal, stock, vol_mult, price_change_min, stock_name_map): stock
            for stock in all_stocks
        }
        
        for future in as_completed(future_to_stock):
            completed_count += 1
            res = future.result()
            if res:
                results.append(res)
            
            # 更新 Streamlit 進度條
            progress = completed_count / total_stocks
            progress_bar.progress(progress)
            status_text.text(f"掃描進度：{completed_count} / {total_stocks} ({progress*100:.1f}%) | 已命中標的：{len(results)} 檔")

    status_text.success("🎉 掃描完成！")
    progress_bar.empty()
    
    # --- 顯示結果 ---
    if results:
        df_result = pd.DataFrame(results)
        df_result = df_result.sort_values(by="今日漲幅(%)", ascending=False)
        saved, save_message = save_results_to_supabase(df_result)
        if saved:
            st.success(save_message)
        else:
            st.warning(save_message)
        
        # 指標卡片展示
        col1, col2 = st.columns(2)
        col1.metric("符合條件檔數", f"{len(df_result)} 檔")
        col2.metric("最高漲幅標的", f"{df_result.iloc[0]['股票代碼']} {df_result.iloc[0]['股票名稱']} ({df_result.iloc[0]['今日漲幅(%)']}%)")

        st.subheader("🎯 飆股篩選結果清單")
        # 互動式數據表格
        display_df = df_result[["股票代碼", "股票名稱", "市場類型", "收盤價", "今日漲幅(%)", "爆量倍數", "成交量(張)"]].copy()
        st.dataframe(
            display_df,
            use_container_width=True,
            column_config={
                "股票代碼": st.column_config.TextColumn("股票代碼"),
                "股票名稱": st.column_config.TextColumn("股票名稱"),
                "市場類型": st.column_config.TextColumn("市場類型"),
                "今日漲幅(%)": st.column_config.NumberColumn("今日漲幅(%)", format="%.2f%%"),
                "爆量倍數": st.column_config.NumberColumn("爆量倍數", format="%.2f 倍"),
                "收盤價": st.column_config.NumberColumn("收盤價", format="$%.2f"),
                "成交量(張)": st.column_config.NumberColumn("成交量(張)", format="%d 張"),
            },
            hide_index=True
        )
    else:
        st.info("今日全市場無符合設定條件之標的。")
        