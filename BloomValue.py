import datetime
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

try:
    from supabase import create_client
except Exception:
    create_client = None

SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

STOCK_NAME_MAP = {
    "1303.TW": "南亞",
    "1605.TW": "華新",
    "1815.TWO": "富喬",
    "2303.TW": "聯電",
    "2317.TW": "鴻海",
    "2330.TW": "台積電",
    "2337.TW": "旺宏",
    "2344.TW": "華邦電",
    "2351.TW": "順德",
    "2377.TW": "微星",
    "2426.TW": "鼎元",
    "2454.TW": "聯發科",
    "2481.TW": "強茂",
    "2603.TW": "長榮",
    "2609.TW": "陽明",
    "2884.TW": "玉山金",
    "2891.TW": "中信金",
    "3008.TW": "大立光",
    "3042.TW": "晶技",
    "5483.TW": "中美晶",
    "6271.TW": "考量",
    "8042.TWO": "金山電",
    "8069.TWO": "元太",
}


def get_stock_display_name(symbol):
    symbol = str(symbol).strip()
    if not symbol:
        return "標的"
    if symbol in STOCK_NAME_MAP:
        return STOCK_NAME_MAP[symbol]

    if symbol.endswith((".TW", ".TWO")):
        return symbol

    try:
        info = yf.Ticker(symbol).info
        name = info.get("longName") or info.get("shortName")
        if name:
            return name
    except Exception:
        pass
    return symbol


def get_latest_signal_symbols():
    if not SUPABASE_URL or not SUPABASE_KEY or create_client is None:
        return []

    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        response = client.table("stock_selection_log").select(
            "date, ticker, pre_breakout_signal, final_pullback_signal"
        ).execute()
        rows = getattr(response, "data", []) or []
        if not rows:
            return []

        valid_rows = []
        for row in rows:
            ticker = str(row.get("ticker", "")).strip()
            if not ticker:
                continue
            if bool(row.get("pre_breakout_signal")) or bool(
                row.get("final_pullback_signal")
            ):
                valid_rows.append(row)

        if not valid_rows:
            return []

        latest_date = max(
            row.get("date") for row in valid_rows if row.get("date") is not None
        )
        latest_rows = [
            row for row in valid_rows if str(row.get("date")) == str(latest_date)
        ]

        symbols = []
        for row in latest_rows:
            ticker = str(row.get("ticker", "")).strip()
            if ticker and ticker not in symbols:
                symbols.append(ticker)
        return symbols
    except Exception:
        return []

# ==========================================
# 1. 頁面配置與標題設定
# ==========================================
st.set_page_config(
    page_title="BloomValue",
    page_icon="✦",
    layout="wide",
)

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@400;600;900&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');

        body {
            background:
                radial-gradient(circle at top left, rgba(82, 160, 255, 0.14), transparent 28%),
                radial-gradient(circle at bottom right, rgba(20, 184, 166, 0.10), transparent 30%),
                linear-gradient(180deg, #07131d 0%, #0b1722 100%);
            color: #e7edf6;
            font-family: 'Plus Jakarta Sans', 'Noto Serif TC', sans-serif;
        }

        div[data-testid="stAppViewContainer"] {
            background: linear-gradient(180deg, rgba(10, 18, 26, 0.82), rgba(13, 25, 35, 0.95));
        }

        .bloom-hero {
            background: linear-gradient(135deg, rgba(8, 24, 31, 0.96), rgba(12, 38, 51, 0.9) 42%, rgba(20, 88, 110, 0.92) 100%);
            border: 1px solid rgba(112, 168, 218, 0.22);
            border-radius: 20px;
            padding: 28px 24px;
            margin-bottom: 18px;
            box-shadow: 0 18px 32px rgba(3, 9, 14, 0.42), inset 0 1px 0 rgba(255,255,255,0.15);
            position: relative;
            overflow: hidden;
        }
        .bloom-hero::before {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(120deg, rgba(255,255,255,0.10), rgba(123, 214, 255, 0.03), rgba(255,255,255,0.12));
            pointer-events: none;
        }
        .bloom-hero::after {
            content: "✦";
            position: absolute;
            right: 20px;
            bottom: 0px;
            font-size: 120px;
            opacity: 0.12;
            color: rgba(148, 214, 255, 0.9);
            pointer-events: none;
        }
        .bloom-brand {
            position: relative;
            z-index: 1;
            font-size: 2.5rem;
            font-weight: 900;
            letter-spacing: -0.5px;
            background: linear-gradient(90deg, #f4fbff 0%, #9fe1ff 28%, #dff9ff 52%, #9fe1ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
            text-shadow: 0 0 25px rgba(125, 207, 255, 0.28);
        }
        .bloom-slogan {
            position: relative;
            z-index: 1;
            font-family: 'Noto Serif TC', serif;
            font-size: 1.1rem;
            font-weight: 600;
            color: #dfeffc;
            letter-spacing: 1.5px;
            margin-top: 8px;
            text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        .bloom-subtitle {
            position: relative;
            z-index: 1;
            font-size: 0.92rem;
            color: #cfe4f8;
            margin-top: 10px;
            opacity: 0.94;
        }

        [data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(14, 28, 36, 0.9), rgba(19, 36, 46, 0.9));
            border: 1px solid rgba(118, 174, 220, 0.18);
            border-radius: 14px;
            padding: 12px 16px;
            box-shadow: 0 10px 24px rgba(2, 10, 16, 0.28);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 14px 26px rgba(22, 95, 140, 0.22);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: rgba(13, 22, 31, 0.7);
            border-radius: 14px;
            padding: 6px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            color: #dfeefd;
            font-weight: 600;
            transition: all 0.25s ease;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #0e3f59 0%, #1d7aa7 100%);
            color: white;
            box-shadow: 0 8px 18px rgba(17, 109, 161, 0.25);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d1720 0%, #101d29 100%);
            border-right: 1px solid rgba(148, 194, 232, 0.12);
        }

        .bloom-footer {
            margin-top: 24px;
            padding: 14px 16px;
            text-align: center;
            border-top: 1px solid rgba(136, 177, 214, 0.18);
            color: #d9ebff;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            background: linear-gradient(90deg, rgba(8,13,19,0.6), rgba(22, 47, 63, 0.7), rgba(8,13,19,0.6));
        }
        .bloom-footer strong { color: #8bd0ff; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="bloom-hero">
        <div class="bloom-brand">BloomValue</div>
        <div class="bloom-slogan">「數據如籽，策略如水；於波動之間，繁花盛開。」</div>
        <div class="bloom-subtitle">專為短線選股後隔日開盤設計：防追高、估量能、看 VWAP 均價支撐。</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# 2. 側邊欄：預設觀察清單與參數調整
# ==========================================
st.sidebar.header("BloomValue")
st.sidebar.caption("觀察標的與參數設定")

# 預設觀察清單（可由使用者自由增減）
latest_signal_symbols = get_latest_signal_symbols()
default_watchlist = (
    ", ".join(latest_signal_symbols)
    if latest_signal_symbols
    else "2344.TW, 2303.TW, 2481.TW, 3042.TW, 5483.TW"
)
watchlist_input = st.sidebar.text_area(
    "輸入昨日篩選出的標的 (用逗號隔開)", value=default_watchlist, height=80
)

# 解析股票代碼
symbols = [s.strip() for s in watchlist_input.split(",") if s.strip()]
unique_symbols = list(dict.fromkeys(symbols))
selected_symbol = st.sidebar.selectbox(
    "🎯 選擇欲監控的標的",
    options=unique_symbols,
    format_func=lambda symbol: f"{get_stock_display_name(symbol)} ({symbol})",
)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ 買進判斷門檻設定")
max_open_pct = st.sidebar.slider(
    "開盤允許最高漲幅 (%) [防追高]", 0.0, 5.0, 3.0, 0.5
)
min_vol_ratio = st.sidebar.slider(
    "預估成交量比 (較昨日放大倍數)", 1.0, 3.0, 1.3, 0.1
)
stop_loss_pct = st.sidebar.slider("停損安全比例 (%)", 2.0, 7.0, 4.0, 0.5)


# ==========================================
# 3. 核心數據抓取與計算邏輯
# ==========================================
@st.cache_data(ttl=60)  # 每 60 秒可刷新數據
def fetch_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        # 抓取近 10 天日 K 線數據 (取得昨日收盤價與量)
        df_daily = ticker.history(period="10d")
        # 抓取今日 1 分鐘 K 線數據 (盤中即時資料)
        df_intra = ticker.history(period="1d", interval="1m")

        if df_daily.empty or len(df_daily) < 2:
            return None, None, "無法取得足夠的歷史日 K 線數據"

        # 處理 MultiIndex 欄位問題
        if isinstance(df_daily.columns, pd.MultiIndex):
            df_daily.columns = df_daily.columns.get_level_values(0)
        if isinstance(df_intra.columns, pd.MultiIndex):
            df_intra.columns = df_intra.columns.get_level_values(0)

        return df_daily, df_intra, None
    except Exception as e:
        return None, None, str(e)


# 執行抓取
df_daily, df_intra, error_msg = fetch_stock_data(selected_symbol)
stock_display_name = get_stock_display_name(selected_symbol)

if error_msg:
    st.error(f"❌ 讀取 {stock_display_name} ({selected_symbol}) 失敗: {error_msg}")
    st.stop()

if df_intra.empty:
    st.warning(
        f"⚠️ 標的 {stock_display_name} ({selected_symbol}) 目前無當日盤中即時交易數據（可能尚未開盤或非交易日）。"
    )
    st.stop()

# --- 指標計算 ---
prev_close = df_daily["Close"].iloc[-2]  # 昨日收盤價
prev_vol = df_daily["Volume"].iloc[-2]  # 昨日成交量

latest_price = df_intra["Close"].iloc[-1]  # 當前最新價
open_price = df_intra["Open"].iloc[0]  # 今日開盤價
cum_volume = df_intra["Volume"].sum()  # 當前累積成交量

# 價格漲跌幅
price_change = latest_price - prev_close
price_change_pct = (price_change / prev_close) * 100

# 盤中均價線 (VWAP = 累積成交金額 ÷ 累積成交股數)
df_intra["Typical_Price"] = (
    df_intra["High"] + df_intra["Low"] + df_intra["Close"]
) / 3
df_intra["VWAP"] = (
    df_intra["Typical_Price"] * df_intra["Volume"]
).cumsum() / df_intra["Volume"].cumsum()
current_vwap = df_intra["VWAP"].iloc[-1]

# 盤中估算全日成交量 (以台股 270 分鐘交易時間估算)
current_time = datetime.datetime.now()
trade_minutes = len(df_intra)  # 當前累積分鐘數
estimated_total_vol = (
    (cum_volume / trade_minutes) * 270 if trade_minutes > 0 else cum_volume
)
vol_ratio = estimated_total_vol / prev_vol if prev_vol > 0 else 0


# ==========================================
# 4. 買進綜合評分與決策邏輯
# ==========================================
score = 0
checklist = []

# 1. 開盤位階檢測 (開平高，且未過度追高)
if 0 <= price_change_pct <= max_open_pct:
    score += 35
    checklist.append(
        (
            "🟢",
            f"**開盤位階適當**：目前漲幅 {price_change_pct:.2f}% (位於 0% ~ {max_open_pct:.1f}% 理想區間)",
        )
    )
elif price_change_pct > max_open_pct:
    checklist.append(
        (
            "🔴",
            f"**注意追高風險**：目前漲幅 {price_change_pct:.2f}% 已高於門檻 {max_open_pct:.1f}%，不宜直接市價追高",
        )
    )
else:
    checklist.append(
        (
            "🔴",
            f"**開低走弱**：當前跌幅 {price_change_pct:.2f}%，價格低於昨日收盤價，動能受阻",
        )
    )

# 2. 均價線 (VWAP) 支撐檢測
if latest_price >= current_vwap:
    score += 40
    checklist.append(
        (
            "🟢",
            f"**站上 VWAP 均價線**：最新價 (${latest_price:.1f}) 高於盤中成本線 (${current_vwap:.1f})，多頭控盤",
        )
    )
else:
    checklist.append(
        (
            "🔴",
            f"**跌破 VWAP 均價線**：最新價 (${latest_price:.1f}) 低於盤中成本線 (${current_vwap:.1f})，上方存在拋壓",
        )
    )

# 3. 預估成交量檢測
if vol_ratio >= min_vol_ratio:
    score += 25
    checklist.append(
        (
            "🟢",
            f"**攻擊量能釋放**：預估全日量為昨日的 {vol_ratio:.2f} 倍 (高於目標 {min_vol_ratio:.1f} 倍)",
        )
    )
else:
    checklist.append(
        (
            "🟡",
            f"**量能相對不足**：預估全日量僅為昨日的 {vol_ratio:.2f} 倍，可能維持狹幅盤整",
        )
    )


# ==========================================
# 5. UI 畫面佈局與即時資訊呈現
# ==========================================

st.subheader(f"📊 {stock_display_name} ({selected_symbol}) 分析")

# 頁首 Metric 卡片
m1, m2, m3, m4 = st.columns(4)
m1.metric(
    "現價 (最新成交)",
    f"${latest_price:.2f}",
    f"{price_change:+.2f} ({price_change_pct:+.2f}%)",
)
m2.metric(
    "盤中均價 (VWAP)",
    f"${current_vwap:.2f}",
    delta=f"價差 ${latest_price - current_vwap:+.2f}",
)
m3.metric("預估今日成交量", f"{int(estimated_total_vol):,} 張", f"昨日 {vol_ratio:.2f} 倍")
m4.metric("開盤價", f"${open_price:.2f}")

st.markdown("---")

col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("🎯 隔日買進決策綜合評估")

    # 燈號提示
    if score >= 75:
        st.success(f"### 🟢 建議買進 (綜合評分：{score} / 100 分)")
        st.info("💡 **進場策略**：位階適中且量價配合良好，可在 VWAP 附近分批掛單建立倉位。")
    elif score >= 40:
        st.warning(f"### 🟡 觀望 / 等待拉回 (綜合評分：{score} / 100 分)")
        st.info(
            "💡 **進場策略**：部分指標未符合，建議等待盤中回測 VWAP 均價線且有撐時再考慮。"
        )
    else:
        st.error(f"### 🔴 放棄操作 (綜合評分：{score} / 100 分)")
        st.info(
            "💡 **進場策略**：今日走勢不符開盤預期，請堅守紀律，放棄進場並關注其他標的。"
        )

    st.markdown("#### 📋 指標檢查清單：")
    for icon, text in checklist:
        st.write(f"{icon} {text}")

    st.markdown("---")
    st.markdown("#### 🛡️ 自動風控與停損計算：")
    stop_loss_price = latest_price * (1 - stop_loss_pct / 100)
    st.write(
        f"* **建議停損價位**：`${stop_loss_price:.2f}` (當前價格的 -{stop_loss_pct}%)"
    )
    st.write(f"* **昨日收盤支撐**：`${prev_close:.2f}`")

with col_right:
    st.subheader("📉 盤中 1 分鐘走勢與 VWAP 均價線")

    # Plotly 互動式圖表
    fig = go.Figure()

    # 股價走勢線
    fig.add_trace(
        go.Scatter(
            x=df_intra.index,
            y=df_intra["Close"],
            mode="lines",
            name="即時價格",
            line=dict(color="#1f77b4", width=2),
        )
    )

    # VWAP 均價線
    fig.add_trace(
        go.Scatter(
            x=df_intra.index,
            y=df_intra["VWAP"],
            mode="lines",
            name="VWAP 均價線",
            line=dict(color="#ff7f0e", width=2, dash="dash"),
        )
    )

    # 畫出昨日收盤參考線
    fig.add_hline(
        y=prev_close,
        line_dash="dot",
        line_color="gray",
        annotation_text="昨收價",
        annotation_position="bottom right",
    )

    fig.update_layout(
        xaxis_title="時間",
        yaxis_title="價格 (TWD)",
        height=450,
        legend=dict(x=0, y=1),
        margin=dict(l=20, r=20, t=30, b=20),
    )

    st.plotly_chart(fig, use_container_width=True)

st.markdown(
    """
    <div class="bloom-footer"><strong>BloomValue</strong> • 數據如籽，策略如水；於波動之間，繁花盛開。</div>
    """,
    unsafe_allow_html=True,
)

# 頁尾自動刷新按鈕
if st.button("🔄 立即手動刷新數據"):
    st.rerun()