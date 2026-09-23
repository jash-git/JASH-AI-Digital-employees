---
name: financial-feasibility-analysis
category: research
description: 分析「某投資/存股/退休宣稱能否達成」——先量化數字、再用真實市場數據驗證，做多情境比較並製表。
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [research, finance, feasibility, analysis, report]
related_skills: [multi-dimensional-analysis, investigative-research-quantify-and-verify, taiwan-stock-query]
---

# 投資可行性量化分析法（Financial Feasibility Analysis）

## When to Use / 何時使用
當用戶貼出一則「存股/投資/退休」新聞或宣稱，要求判斷「能不能達到文中結果、要投入多少、比例如何」。典型觸發：年領百萬股息、X 年退休、月領 X 萬所需本金。本技能把模糊宣稱轉成可驗證的數字，並做多情境比較。

## 核心原則（用戶偏好）
1. **先量化，再驗證**：把每個文字宣稱轉成數字（年息→所需本金→時間），再用真實市場數據（配息、殖利率、股價）逐項查證，不憑印象下結論。參考 investigative-research-quantify-and-verify。
2. **區分「結果」與「達成結果的路徑」**：結果可能可行，但 5 年達標這種時間表常依賴變數（卖房、槓桿），不可照抄。
3. **多情境對照**：至少給「純靠薪水」「文中真實路徑」「保守可複製版本」三種，做成對照表。
4. **誠實標風險與條件**：殖利率會變、槓桿有追繳、稅負、過熱估值——都要寫進報告。
5. **報告格式**：參考資料集中放最後一章（附原始連結）；數據密集時補圖/PDF。見 multi-dimensional-analysis。

## 執行步驟
1. **抓原文全文**：businesstoday/businessweekly 等站用 curl + python 去標籤可解析（JS/Cloudflare 保護的換 FinLab/Yahoo）。
2. **提取宣稱數字**：目標年息、年份、投入金額、投資標的。
3. **查證市場數據**：各標的歷年配息 + 現價 + 殖利率。一手來源見 `references/etf-data-sources.md`（FinLab/Yahoo 最可靠）。
4. **量化反推**：
   - 達成目標年息所需本金 = 目標年股息 ÷ 平均殖利率
   - 反推文中隐含資產軌跡 = 各年度股息 ÷ 假設殖利率（常用 6%）
5. **做多情境比較**：
   - A. 純靠薪水存股（不卖房、無槓桿）→ 看 5 年後年息
   - B. 文中真實路徑（資產重配置 + 再投資 + 槓桿）→ 驗證能否達標
   - C. 保守可複製版（純存股拉到 X 年）→ 最接近的可行結果
6. **給出達標配置**：以目標本金反推各標配息率，排出比例表（高息 ETF 為主 + 少量市值型成長）。
7. **寫報告**：摘要一句話結論 → 原始數據表 → 可行性分析 → 達標配置 → 最佳替代結果比較 → 風險 → 附錄資料來源。

## 關鍵公式（見 references/etf-data-sources.md）
- 殖利率 = 年度配息 ÷ 收盤價 × 100%
- 所需本金 = 目標年股息 ÷ 平均殖利率
- 複利達標年數：while 累積本金 < 目標，每期投入 ×(1+r)^n 迭代求 n

## 常見陷阱
- 把「結果可行」誤當「時間表可複製」。文中 5 年達標常靠卖房/槓桿，純薪水做不到。
- 只驗證「人/書是真的」就斷言數字可信——要轉成數字查市場數據（如 12-14%/yr 要對照實際殖利率）。
- ETF 配息非固定、且正往減少配息走；現價過熱會壓縮殖利率，達標本金需上修。
- wantgoo/goodinfo/pocket 多為 JS/Cloudflare 保護，curl 抓不到數據，改用 FinLab/Yahoo。

## 支援檔案
- `references/etf-data-sources.md`：台股 ETF/個股配息一手來源、各標歷史配息與現價、公式、陷阱、達標配置範例。
