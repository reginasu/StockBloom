<div align="center">

# 🌸 StockBloom 台股策略雷達
### Taiwan Stock Strategy Radar

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://stockbloom.streamlit.app/)
[![Supabase](https://img.shields.io/badge/Supabase-Cloud_DB-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<p align="center">
  <b>「數據如籽，策略如水；於波動之間，繁花盛開。」</b><br>
  由自動化資料抓取、技術面篩選與雲端同步組成的台股策略掃描系統。
</p>

</div>

---

## 📌 專案簡介

StockBloom 是一個以台股市場為核心的策略掃描與數據管理系統，整合上市上櫃個股行情、技術指標與籌碼面資料，透過自動化流程持續篩選具潛力的交易標的。

系統會定期抓取 TWSE / TPEx 市場資料，篩選高流動性與適當價位的股票，並搭配多項技術條件進行策略判斷；最後將符合條件的結果自動同步至 Supabase 雲端資料庫，方便後續觀察、回測與追蹤。

---

## 🎯 核心流程

```text
[全市場行情資料] → [成交量前 300 大標的池] → [技術 / 籌碼策略判斷] → [雲端資料儲存]
(TWSE / TPEx API)      (流動性與價位初篩)          (均線、布林、回檔條件)         (Supabase Upsert)
```

這個流程讓系統兼顧效率與可擴充性：
- 先依市場資料建立候選池
- 再用策略邏輯過濾高風險與低勝率標的
- 最後將結果寫入資料庫，支援後續分析與可視化

---

## ⚙️ 系統特色

- ⚡ 多執行緒高效率運算：利用 ThreadPoolExecutor 並行處理多個資料任務，縮短全市場指標計算時間。
- ☁️ 雲端資料同步：直接整合 Supabase，將每日符合條件的個股與技術資料寫入資料庫，避免重複紀錄與資料缺失。
- 📊 動態儀表板：基於 Streamlit 建構互動式看板，提供指標分頁、即時 KPI 卡片與便利的 Yahoo Finance 快速連結。
- 🛠️ 強健資料補齊機制：自動標準化 TWSE / TPEx 交易日期與 yfinance 歷史資料，提升資料一致性與系統穩定性。
- 🧠 策略導向篩選：整合均線多頭、回檔防守與布林帶壓縮等條件，依市場狀況進行更有邏輯的標的判斷。

---

## 🧩 技術棧

- Python 3.10+
- Streamlit
- yfinance
- Pandas / NumPy
- Supabase
- ThreadPoolExecutor

---

## 🚀 使用場景

StockBloom 適合用於：
- 台股日常市場掃描
- 策略觀察與候選股發掘
- 資料自動收集與雲端存檔
- 儀表板化呈現市場機會

---

## 📌 備註

此專案提供的是市場觀測與策略篩選框架，適合用於研究、開發與持續優化交易邏輯。實際投資決策仍需結合風險管理與個人判斷。