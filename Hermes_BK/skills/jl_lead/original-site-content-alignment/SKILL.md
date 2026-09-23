---
name: original-site-content-alignment
description: 原站文章型頁面對齊：搬移 suanming 教學文章進本地互動頁（CDP抽取、difflib驗證）。
---

# 原站文章型頁面對齊開發流程

## 適用情境
把原站（如 `suanming.com.tw/tool/xxx`）的「純靜態教學文章」搬移進本地互動頁面（`src/public/tool/ziwei.html`、`lunar.html` 等），使本地頁面與原站在**文章結構上完全對齊**。

本質差異：原站是「**文章型頁面**」（教學长文 + TOC + 搜尋表單 + 評論區），本地是「**互動排盤工具**」（四柱 + 十二宮位 + JS 計算）。補齊方向＝純前端 HTML 內容搬移（L2 難度），不碰 JS/PHP。

## ⚠️ 四個致命陷阱（T-35 實戰教訓）

### 陷阱 1：子代理自報 `failed` 多為假陽性
`delegate_task` 回報 `status=failed` 常是因為 **output_schema 不符**，而非實質失敗。子代理可能已正確完成工作。
→ **主管絕不能信任自報**。每次都要用驗證腳本獨立確認（grep id、difflib 比對）。M5/M7/M9 都出現此模式。

### 陷阱 2：簡繁字元錯誤
子代理會把繁體誤寫成簡體，例如 `餘`(U+9918)→`余`(U+4F59)、`構`(U+6784)→`构`(U+69CB)。
→ 每次搬移後**必須用 Python 逐字比對** reference 檔。difflib whitespace-insensitive 比對能一次抓出所有簡繁差異（char-by-char）。

### 陷阱 3：邊界抽取陷阱
reference 檔內容幾乎**全在單一行**。用「`id=X` 之前」作邊界，會落在下一節開頭標籤**內部**，造成懸空 `<h2 ` / `<h3 `（M4/M5 各留一個）。
→ **主管預先抽出乾淨區塊**：Python 以「下一節完整開頭標籤」（如 `<h3 id="dsg">`）為界，結尾無懸空標籤。子代理只需整檔搬移，不用猜邊界。

### 陷阱 4：資料完整性漏洞（最危險）
grep `id=` 檢查**會漏掉整段內容缺失**。T-35 發現 dsg（定身宮）整段遺失、rhtgzwdsjddxg 內段落遺失、三個 `<hr>` 分隔線中兩個遺失。
→ **整合階段必須做 difflib whitespace-insensitive 比對**，而非只 grep id。這是唯一能抓出整段缺失的方法。

## 標準流程（Step by Step）

### Step 1: gap analysis
1. `browser_exec` + CDP Chrome 實測原站，抓取 `<article>` outerHTML → `docs/reference-xxx-original.html`
2. 與本地頁面逐節對照，寫入 `docs/gap-analysis.md`（含優先級 L0-L4、已完成/待執行狀態）

### Step 2: 抽取乾淨區塊
Python 精確抽出每個 micro-step 的 HTML 區塊 → `docs/extracted/M*.html`。邊界以「下一節完整開頭標籤」為界。

### Step 3: 微步委派 jl_ui
- 每節一份工單：`docs/workorder-T-XX-M*.md`
- **主管禁令條款**（必須寫進 prompt）：只准改一個檔案 `src/public/tool/xxx.html`、純前端 HTML 搬移不碰 JS/PHP、改碼前務必先讀取本地檔 + extracted/M*.html、簡繁字元鐵律、保留互動排盤工具區與所有 JS 邏輯、TOC 锚點 id 必須與 reference 一致。
- 完成後狀態更新為 `REVIEW`，派單後立即建 Cron watchdog（every 3m）。

### Step 4: 獨立驗證（主管親自，每次）
執行 `docs/tools/verify_article_alignment.py <target> [reference]`：所有 section id 各==1、TOC 锚點全解析、無懸空 h2/h3、article content difflib 逐字一致、`<hr>` count 與 reference 一致。發現简繁错误或资料缺失：**主管直接 patch**（資料完整性修復，非創意性工作）。

### Step 5: 整合 + 部署（M10，主管親自）
footer nav 檢查 → 整頁整合驗證 → `sudo cp src/public/tool/xxx.html /var/www/html/tool/` → `chown www-data:www-data` + `chmod 644` → 瀏覽器實測（CDP port 9222，0 console errors）→ `graphify . --code-only` + `cluster-only`。

## 驗證工具
`docs/tools/verify_article_alignment.py <target> [reference]` — 可重用的整合驗證腳本。