from concurrent.futures import ThreadPoolExecutor
import datetime
import os
import time

import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from dotenv import load_dotenv

try:
    from FinMind.data import DataLoader
except Exception:
    DataLoader = None

try:
    from supabase import create_client, Client
except Exception:
    create_client = None
    Client = None

load_dotenv()


def get_app_secret(key: str):
    try:
        value = st.secrets.get(key)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(key)

# ==========================================
# 讀取 st.secrets
SUPABASE_URL = st.secrets["SUPABASE_URL"] if "SUPABASE_URL" in st.secrets else os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets["SUPABASE_KEY"] if "SUPABASE_KEY" in st.secrets else os.getenv("SUPABASE_KEY")

@st.cache_resource
def init_supabase():
    """初始化並快取 Supabase 客戶端連線"""
    if not SUPABASE_URL or not SUPABASE_KEY or create_client is None:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_supabase()
except Exception:
    supabase = None

# ==========================================
# 1. 共用參數與設定
# ==========================================
PRICE_MIN = 100
PRICE_MAX = 250
TOP_VOLUME_LIMIT = 300
SCAN_WORKERS = 8
FINMIND_INTERVAL_SECONDS = 0.5

STOCK_NAMES = {
    "2303.TW": "聯電", "2317.TW": "鴻海", "3702.TW": "大聯大", "4938.TW": "和碩",
    "3231.TW": "緯創", "2344.TW": "華邦電", "2337.TW": "旺宏", "8033.TW": "雷虎",
    "2481.TW": "強茂", "6669.TW": "緯穎", "3481.TW": "群創", "3515.TW": "華擘",
    "5483.TWO": "中美晶", "1815.TWO": "富喬", "2385.TW": "群光", "2885.TW": "元大金",
    "2912.TW": "統一超", "2882.TW": "國泰金", "2881.TW": "富邦金", "2886.TW": "兆豐金",
    "6757.TW": "虎航", "2377.TW": "微星", "2548.TW": "華固", "8926.TW": "台汽電",
    "2375.TW": "凱美", "2330.TW": "台積電", "2313.TW": "華通", "2449.TW": "京元",
    "2855.TW": "統一證", "2884.TW": "玉山金", "5386.TWO": "青雲", "8112.TW": "至上",
    "8086.TWO": "宏捷科", "8042.TWO": "金山電", "5522.TW": "遠雄", "5534.TW": "長虹",
    "2324.TW": "仁寶", "6719.TW": "力智",
}

finmind_loader = DataLoader() if DataLoader is not None else None

st.set_page_config(
    page_title="Bloomstx 台股策略雷達",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 注入美化 CSS 樣式
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@400;600;900&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');

    body {
        font-family: 'Plus Jakarta Sans', 'Noto Serif TC', sans-serif;
    }
    .hero-header {
        background: linear-gradient(135deg, rgba(16, 37, 28, 0.9) 0%, rgba(26, 54, 42, 0.85) 100%);
        border: 1px solid rgba(82, 183, 136, 0.25);
        border-radius: 16px;
        padding: 32px 28px;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
        position: relative;
        overflow: hidden;
    }
    .hero-header::after {
        content: "🌸";
        position: absolute;
        right: -10px;
        bottom: -20px;
        font-size: 110px;
        opacity: 0.12;
        pointer-events: none;
    }
    .brand-title {
        font-size: 2.2rem;
        font-weight: 900;
        letter-spacing: -0.5px;
        background: linear-gradient(90deg, #74c69d, #d8f3dc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
    }
    .brand-slogan {
        font-family: 'Noto Serif TC', serif;
        font-size: 1.15rem;
        font-weight: 600;
        color: #b7e4c7;
        letter-spacing: 2px;
        margin-bottom: 12px;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .hero-subtext {
        font-size: 0.9rem;
        color: #95d5b2;
        margin: 0;
        opacity: 0.9;
    }
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 12px 16px;
        transition: all 0.3s ease;
    }
    [data-testid="stMetric"]:hover {
        border-color: rgba(116, 198, 157, 0.4);
        transform: translateY(-2px);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 8px;
        padding: 0 18px;
        font-weight: 600;
    }
    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 20, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. 表格渲染與 Config 函式 (需放在 main 之前)
# ==========================================
def render_table(frame):
    columns = [
        "Ticker", "Name", "Close", "MA5", "MA10", "MA20", "BIAS5",
        "K", "D", "BB_Width", "PullbackSignal", "FinalPullbackSignal",
        "PreBreakoutSignal", "ComboSignal",
    ]
    display_columns = {
        "Ticker": "股票代號", "Name": "股票名稱", "Close": "收盤價",
        "MA5": "5日均線", "MA10": "10日均線", "MA20": "20日均線",
        "BIAS5": "5日乖離率(%)", "K": "KD-K值", "D": "KD-D值",
        "BB_Width": "布林寬度", "PullbackSignal": "回檔訊號",
        "FinalPullbackSignal": "外資連買回檔", "PreBreakoutSignal": "突破前兆",
        "ComboSignal": "🔥強棒交集",
    }
    # 確保所需欄位皆存在
    existing_cols = [col for col in columns if col in frame.columns]
    shown = frame[existing_cols].rename(columns=display_columns).copy()
    
    if "股票代號" in shown.columns:
        tickers = shown["股票代號"].copy()
        shown["股票代號"] = tickers.map(lambda ticker: f"https://tw.stock.yahoo.com/quote/{ticker}/technical-analysis")
        if "股票名稱" in shown.columns:
            shown["股票名稱"] = [
                f"https://tw.stock.yahoo.com/quote/{ticker}/profile?name={name}"
                for ticker, name in zip(tickers, shown["股票名稱"])
            ]
    return shown

def table_config():
    return {
        "股票代號": st.column_config.LinkColumn("股票代號", display_text=r".*/quote/([^/]+)/technical-analysis"),
        "股票名稱": st.column_config.LinkColumn("股票名稱", display_text=r".*/profile\?name=(.*)"),
        "收盤價": st.column_config.NumberColumn("收盤價", format="%.2f"),
        "5日均線": st.column_config.NumberColumn("5日均線", format="%.2f"),
        "10日均線": st.column_config.NumberColumn("10日均線", format="%.2f"),
        "20日均線": st.column_config.NumberColumn("20日均線", format="%.2f"),
        "5日乖離率(%)": st.column_config.NumberColumn("5日乖離率(%)", format="%.2f"),
        "KD-K值": st.column_config.NumberColumn("KD-K值", format="%.2f"),
        "KD-D值": st.column_config.NumberColumn("KD-D值", format="%.2f"),
        "布林寬度": st.column_config.NumberColumn("布林寬度", format="%.2f"),
        "🔥強棒交集": st.column_config.CheckboxColumn("🔥強棒交集"),
    }


# ==========================================
# 3. 資料處理與計算函式
# ==========================================
def to_number(series):
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")

def normalize_market_date(value):
    text = str(value).strip().replace("/", "").replace("-", "")
    if len(text) == 7 and text.isdigit():
        try:
            return pd.Timestamp(year=int(text[:3]) + 1911, month=int(text[3:5]), day=int(text[5:7]))
        except ValueError:
            return pd.NaT
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return pd.NaT
    parsed = pd.Timestamp(parsed)
    if parsed.tzinfo is not None:
        parsed = parsed.tz_localize(None)
    return parsed.normalize()

def is_support_near_ma(close, ma, tolerance=3.5):
    if pd.isna(close) or pd.isna(ma) or ma == 0:
        return False
    offset = (close - ma) / ma * 100
    return bool(0 <= offset <= tolerance)

def is_bb_width_new_low(history, current, window=60):
    values = pd.Series(history, dtype="float64").dropna()
    if values.empty:
        return False
    prior = values.tail(window)
    if prior.empty:
        return False
    return bool(float(current) < float(prior.min()))

def fetch_market_quotes():
    endpoints = [
        ("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", ".TW", "Code", "Name", "ClosingPrice", "TradeVolume", "OpeningPrice", "HighestPrice", "LowestPrice"),
        ("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes", ".TWO", "SecuritiesCompanyCode", "CompanyName", "Close", "TradingShares", "Open", "High", "Low"),
    ]
    rows = []
    for url, suffix, code_col, name_col, close_col, volume_col, open_col, high_col, low_col in endpoints:
        try:
            data = pd.DataFrame(requests.get(url, timeout=15).json())
            required = {code_col, close_col, volume_col, open_col, high_col, low_col}
            if not required.issubset(data.columns):
                continue
            data["Code"] = data[code_col].astype(str).str.strip()
            data["Name"] = data[name_col].astype(str).str.strip() if name_col in data else ""
            data["Close"] = to_number(data[close_col])
            data["Volume"] = to_number(data[volume_col])
            data["Open"] = to_number(data[open_col])
            data["High"] = to_number(data[high_col])
            data["Low"] = to_number(data[low_col])
            data["QuoteDate"] = data["Date"].map(normalize_market_date)
            data = data[data["Code"].str.fullmatch(r"\d+", na=False)]
            for row in data.itertuples():
                ticker = f"{row.Code}{suffix}"
                rows.append({
                    "Ticker": ticker,
                    "Name": "" if str(row.Name).lower() in {"nan", "none"} else str(row.Name).strip(),
                    "Close": row.Close,
                    "Volume": row.Volume,
                    "Open": row.Open,
                    "High": row.High,
                    "Low": row.Low,
                    "QuoteDate": row.QuoteDate,
                })
        except Exception as error:
            print(f"市場 API 失敗：{error}")
    return {row["Ticker"]: row for row in rows}

def build_candidates(quotes):
    volume_pool = sorted(
        quotes,
        key=lambda ticker: quotes[ticker]["Volume"] if pd.notna(quotes[ticker]["Volume"]) else -1,
        reverse=True,
    )[:TOP_VOLUME_LIMIT]
    price_pool = {ticker for ticker in volume_pool if PRICE_MIN <= quotes[ticker]["Close"] <= PRICE_MAX}
    return sorted(set(volume_pool)), price_pool, set(volume_pool)

def normalize_history(df, ticker, quote):
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        if ticker in df.columns.get_level_values(-1):
            df = df.xs(ticker, axis=1, level=-1)
        else:
            df.columns = df.columns.get_level_values(0)
    required = ["Open", "High", "Low", "Close", "Volume"]
    if not set(required).issubset(df.columns):
        return None
    df = df.dropna(subset=required).copy()
    if quote and len(df) > 0:
        quote_date = normalize_market_date(quote.get("QuoteDate"))
        latest_date = normalize_market_date(df.index[-1])
        if pd.notna(quote_date) and pd.notna(latest_date):
            if quote_date > latest_date:
                df.loc[quote_date, required] = [quote.get(column) for column in required]
                df = df.sort_index()
            elif quote_date == latest_date:
                for column in required:
                    if pd.notna(quote.get(column)):
                        df.loc[df.index[-1], column] = quote[column]
    return df

def calculate_metrics(ticker, quote):
    try:
        df = yf.download(ticker, period="90d", interval="1d", auto_adjust=False, progress=False, timeout=15)
        df = normalize_history(df, ticker, quote)
        if df is None or len(df) < 30:
            return None

        df["MA5"] = df["Close"].rolling(5).mean()
        df["MA10"] = df["Close"].rolling(10).mean()
        df["MA20"] = df["Close"].rolling(20).mean()
        df["Vol_MA5"] = df["Volume"].rolling(5).mean()
        df["Vol_MA20"] = df["Volume"].rolling(20).mean()
        df["BIAS5"] = (df["Close"] - df["MA5"]) / df["MA5"] * 100
        low9 = df["Low"].rolling(9).min()
        high9 = df["High"].rolling(9).max()
        rsv = (df["Close"] - low9) / (high9 - low9) * 100
        df["K"] = rsv.ewm(com=2, adjust=False).mean()
        df["D"] = df["K"].ewm(com=2, adjust=False).mean()
        std20 = df["Close"].rolling(20).std()
        df["BB_Width"] = (4 * std20) / df["MA20"]

        latest = df.iloc[-1]
        if latest[["MA5", "MA10", "MA20", "BIAS5", "K", "D", "BB_Width", "Vol_MA5", "Vol_MA20"]].isna().any():
            return None

        bb_values = df["BB_Width"].dropna().astype(float).tolist()
        current_bb_width = float(latest["BB_Width"])
        prior_60 = bb_values[-61:-1] if len(bb_values) >= 61 else bb_values[:-1]
        prior_120 = bb_values[-121:-1] if len(bb_values) >= 121 else bb_values[:-1]

        return {
            "Ticker": ticker,
            "Name": STOCK_NAMES.get(ticker) or quote.get("Name", "") or ticker.rsplit(".", 1)[0],
            "Open": float(latest["Open"]),
            "Close": float(latest["Close"]),
            "MA5": float(latest["MA5"]),
            "MA10": float(latest["MA10"]),
            "MA20": float(latest["MA20"]),
            "BIAS5": float(latest["BIAS5"]),
            "K": float(latest["K"]),
            "D": float(latest["D"]),
            "Vol_Ratio": float(latest["Volume"] / latest["Vol_MA5"]),
            "BB_Width": current_bb_width,
            "Volume": float(latest["Volume"]),
            "Vol_MA20": float(latest["Vol_MA20"]),
            "BB_Width_60dNewLow": is_bb_width_new_low(prior_60, current_bb_width, 60),
            "BB_Width_120dNewLow": is_bb_width_new_low(prior_120, current_bb_width, 120),
        }
    except Exception:
        return None

def evaluate_signals(metrics, price_pool, volume_pool):
    close = metrics["Close"]
    open_price = metrics.get("Open", close)
    ma_trend = metrics["MA5"] > metrics["MA10"] > metrics["MA20"]
    support_near = is_support_near_ma(close, metrics["MA5"]) or is_support_near_ma(close, metrics["MA10"])

    pullback_optimized = ma_trend and close >= open_price and support_near and metrics["K"] <= 70
    pullback_100_250 = (
        metrics["Ticker"] in price_pool
        and ma_trend
        and abs((close - metrics["MA5"]) / metrics["MA5"] * 100) <= 5
        and 0 <= metrics["BIAS5"] <= 3.5
        and metrics["K"] <= 70
    )
    bb_width_new_low = metrics.get("BB_Width_60dNewLow", False) or metrics.get("BB_Width_120dNewLow", False)
    prebreakout = (
        metrics["Ticker"] in volume_pool
        and PRICE_MIN <= close <= PRICE_MAX
        and close > metrics["MA5"]
        and bb_width_new_low
        and metrics["Volume"] / metrics["Vol_MA20"] < 0.90
    )
    
    combo_signal = pullback_optimized and prebreakout

    metrics.update({
        "PullbackSignal": pullback_optimized,
        "Pullback100250": pullback_100_250,
        "PreBreakoutSignal": prebreakout,
        "ComboSignal": combo_signal,
    })
    return metrics

def foreign_buy_two_days(stock_id):
    if finmind_loader is None:
        return False
    try:
        today = pd.Timestamp.today()
        data = finmind_loader.taiwan_stock_institutional_investors(
            stock_id=stock_id,
            start_date=(today - pd.Timedelta(days=14)).strftime("%Y-%m-%d"),
            end_date=today.strftime("%Y-%m-%d"),
        )
        if data is None or data.empty:
            return False

        data.columns = [str(c).lower().strip() for c in data.columns]
        if not {"date", "name", "buy", "sell"}.issubset(data.columns):
            return False

        data["name"] = data["name"].astype(str).str.strip().str.lower()
        foreign_df = data[data["name"] == "foreign_investor"].copy()
        if foreign_df.empty:
            return False

        foreign_df["buy"] = pd.to_numeric(foreign_df["buy"], errors="coerce").fillna(0)
        foreign_df["sell"] = pd.to_numeric(foreign_df["sell"], errors="coerce").fillna(0)
        foreign_df["net_buy"] = foreign_df["buy"] - foreign_df["sell"]

        daily_net = foreign_df.groupby("date")["net_buy"].sum().sort_index(ascending=False)

        if len(daily_net) < 2:
            return False

        return bool(daily_net.iloc[0] > 0 and daily_net.iloc[1] > 0 and daily_net.head(2).sum() > 500)
    except Exception as e:
        print(f"FinMind 外資連買查詢失敗 [{stock_id}]: {e}")
        return False

# ==========================================
# 4. 寫入 Supabase 資料庫邏輯
# ==========================================
def save_results_to_supabase(df: pd.DataFrame):
    if supabase is None or df is None or df.empty:
        return False, "Supabase 未連線或資料為空 (請檢查 Secrets 設定)"

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    # 篩選出觸發任意訊號的標的
    signal_mask = (
        df.get("PullbackSignal", False) |
        df.get("PreBreakoutSignal", False) |
        df.get("FinalPullbackSignal", False) |
        df.get("ComboSignal", False)
    )
    signal_df = df[signal_mask].copy()
    
    if signal_df.empty:
        return True, "今日無觸發訊號的股票，無需寫入"

    records = []
    for _, row in signal_df.iterrows():
        records.append({
            "date": today_str,
            "ticker": str(row["Ticker"]),
            "stock_name": str(row["Name"]),
            # 四捨五入至小數點後 1 位
            "close_price": round(float(row["Close"]), 1),
            "ma5": round(float(row["MA5"]), 1),
            "ma10": round(float(row["MA10"]), 1),
            "ma20": round(float(row["MA20"]), 1),
            "bias5": round(float(row["BIAS5"]), 1),
            # 四捨五入至小數點後 2 位
            "k_value": round(float(row["K"]), 2),
            "d_value": round(float(row["D"]), 2),
            "bb_width": round(float(row["BB_Width"]), 2),
            # 訊號狀態
            "pullback_signal": bool(row.get("PullbackSignal", False)),
            "final_pullback_signal": bool(row.get("FinalPullbackSignal", False)),
            "pre_breakout_signal": bool(row.get("PreBreakoutSignal", False)),
        })

    try:
        # 使用 upsert 並指定衝突鍵為 date, ticker
        supabase.table("stock_selection_log").upsert(
            records,
            on_conflict="date, ticker"
        ).execute()
        return True, f"成功同步 {len(records)} 筆觸發訊號至 Supabase 資料庫 (已完成格式化與防重複處置)！"
    except Exception as error:
        return False, f"寫入 Supabase 失敗: {error}"

# ==========================================
# 5. 掃描流程控制
# ==========================================
def scan_market():
    quotes = fetch_market_quotes()
    if not quotes:
        return None, 0, 0, 0
    candidates, price_pool, volume_pool = build_candidates(quotes)

    with ThreadPoolExecutor(max_workers=SCAN_WORKERS) as executor:
        metric_rows = list(executor.map(lambda ticker: calculate_metrics(ticker, quotes.get(ticker, {})), candidates))
    metric_rows = [row for row in metric_rows if row]
    results = [evaluate_signals(row, price_pool, volume_pool) for row in metric_rows]

    for row in results:
        row["ForeignBuy2Days"] = False
        if row.get("Pullback100250", False):
            time.sleep(FINMIND_INTERVAL_SECONDS)
            row["ForeignBuy2Days"] = foreign_buy_two_days(row["Ticker"].rsplit(".", 1)[0])
        row["FinalPullbackSignal"] = row.get("Pullback100250", False) and row["ForeignBuy2Days"]

    if not results:
        return None, len(candidates), len(price_pool), len(volume_pool)
        
    output = pd.DataFrame(results)
    
    required_signals = [
        "PullbackSignal", "Pullback100250", "PreBreakoutSignal", 
        "ComboSignal", "FinalPullbackSignal", "ForeignBuy2Days"
    ]
    for col in required_signals:
        if col not in output.columns:
            output[col] = False

    output["Name"] = output["Name"].replace({"": "中文名稱未取得", "nan": "中文名稱未取得"})
    
    success, msg = save_results_to_supabase(output)
    if success:
        st.toast(msg, icon="✅")
    else:
        st.toast(msg, icon="⚠️")

    return output, len(candidates), len(price_pool), len(volume_pool)

# ==========================================
# 6. UI 與主程式 (Streamlit)
# ==========================================
def main():
    st.markdown("""
    <div class="hero-header">
        <div class="brand-title">Bloomstx 台股策略雷達</div>
        <div class="brand-slogan">「數據如籽，策略如水；於波動之間，繁花盛開。」</div>
        <div class="hero-subtext">全自動市場指標掃描與條件過濾系統，即時同步選股成果至雲端資料庫。</div>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚡ 掃描控制")
        st.caption("資料來源：TWSE、TPEx、Yahoo Finance、FinMind")
        scan_requested = st.button("🚀 重新掃描市場並記錄", type="primary", use_container_width=True)
        st.divider()
        st.markdown("**Supabase 雲端資料庫**")
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("Secrets 未讀取到 (URL 或 Key 為空)")
    elif create_client is None:
        st.error("Supabase 套件匯入失敗 (請檢查 requirements.txt)")
    else:
        try:
            test_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            st.success("Cloud DB 連線正常")
        except Exception as e:
            st.error(f"連線失敗: {e}")

    if scan_requested or "scan_result" not in st.session_state:
        with st.spinner("正在抓取最新市場行情、計算策略技術指標並同步至 Supabase..."):
            st.session_state.scan_result = scan_market()

    output, candidate_count, price_count, volume_count = st.session_state.scan_result
    
    if output is None or output.empty:
        st.warning("⚠️ 目前無有效市場資料或未掃描到符合條件的標的，請點擊「重新掃描市場」。")
        return

    signal_mask = (
        output.get("PullbackSignal", pd.Series(False, index=output.index)) |
        output.get("PreBreakoutSignal", pd.Series(False, index=output.index)) |
        output.get("FinalPullbackSignal", pd.Series(False, index=output.index)) |
        output.get("ComboSignal", pd.Series(False, index=output.index))
    )
    
    metric_columns = st.columns(6)
    metric_columns[0].metric("有效標的", f"{len(output)} / {candidate_count}")
    metric_columns[1].metric("價格池", f"{price_count} 檔")
    metric_columns[2].metric("成交量池", f"{volume_count} 檔")
    metric_columns[3].metric("100~250 回檔", f"{int(output['Pullback100250'].sum())} 檔")
    metric_columns[4].metric("突破前兆", f"{int(output['PreBreakoutSignal'].sum())} 檔")
    metric_columns[5].metric("🔥強棒交集", f"{int(output['ComboSignal'].sum())} 檔")

    st.write("")

    tabs = st.tabs(["🔥 強棒交集", "🎯 今日策略總覽", "📉 多頭回檔", "⚡ 突破前兆", "📊 全部資料"])
    
    with tabs[0]:
        st.subheader("🔥 強棒交集標的（同時符合多頭回檔 + 突破前兆）")
        combo_df = output[output["ComboSignal"]].sort_values("Close", ascending=False)
        if not combo_df.empty:
            st.dataframe(render_table(combo_df), column_config=table_config(), width="stretch", hide_index=True)
        else:
            st.info("目前無同時符合兩種策略的強棒標的。")

    with tabs[1]:
        st.subheader("今日觸發策略標的 (已同步記錄至 Supabase)")
        if not output[signal_mask].empty:
            st.dataframe(render_table(output[signal_mask].sort_values("Close", ascending=False)), column_config=table_config(), width="stretch", hide_index=True)
        else:
            st.info("目前無符合任何策略條件的標的。")

    with tabs[2]:
        st.subheader("均線多頭回檔與外資連買回檔")
        pullback = output[output["FinalPullbackSignal"] | output["PullbackSignal"]].sort_values("K")
        if not pullback.empty:
            st.dataframe(render_table(pullback), column_config=table_config(), width="stretch", hide_index=True)
        else:
            st.info("目前無符合回檔策略條件的標的。")

    with tabs[3]:
        st.subheader("布林壓縮與量縮突破前兆")
        breakout = output[output["PreBreakoutSignal"]].sort_values("BB_Width")
        if not breakout.empty:
            st.dataframe(render_table(breakout), column_config=table_config(), width="stretch", hide_index=True)
        else:
            st.info("目前無符合突破前兆條件的標的。")

    with tabs[4]:
        st.subheader("全部有效技術指標資料")
        st.dataframe(render_table(output.sort_values("Ticker")), column_config=table_config(), width="stretch", hide_index=True)

if __name__ == "__main__":
    main()