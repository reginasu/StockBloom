<div align="center">

# 🌸 Bloomstx 繁花策略雷達
### TWStock Automated Strategy & Data Radar System

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Supabase](https://img.shields.io/badge/Supabase-Cloud_DB-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<p align="center">
  <b>「數據如籽，策略如水；於波動之中，繁花盛開。」</b><br>
  全自動市場指標掃描、技術與籌碼面多重過濾系統，即時同步選股結果至 Supabase 雲端資料庫。
</p>

</div>

---

## 📌 系統簡介 (Overview)

**Bloomstx 繁花策略雷達** 是一個整合全台股（TWSE/TPEx）上市上櫃個股的即時策略掃描系統。系統透握自動化 API 擷取每日行情與籌碼數據，針對全市場成交量前 300 大及特定股價區間之標的，進行**均線多頭防追高回檔**與**布林頻寬極致壓縮量縮**的雙核心篩選，並將每日觸發訊號無縫寫入 **Supabase 雲端資料庫**。

---

## 🎯 核心篩選機制 (Selection Criteria)

系統採用多重架構進行嚴格的標的過濾：

```text
 [全市場每日行情] ➔ [成交量前300大標的池] ➔ [技術/籌碼策略運算] ➔ [雲端DB自動紀錄]
(TWSE/TPEx API)    (流動性初篩/價位過濾)   (多頭回檔/布林壓縮)   (Supabase Upsert)# StockBloom
