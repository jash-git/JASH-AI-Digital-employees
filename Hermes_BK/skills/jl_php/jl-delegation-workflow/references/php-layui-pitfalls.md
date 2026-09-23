# PHP + Layui 委派失敗高頻陷阱對照表

本文件是 `jl-delegation-workflow` 的實戰補充，收錄 jl_lead 親身經歷、可驗證的真問題。派單給 jl_php / jl_ui 時，視任務性質挑對應陷阱附在 goal 裡。

---

## A. PHP 後端（jl_php）陷阱

### A1. SQL 注入：WHERE 字串拼接 → PDO 預處理
**症狀**：`$sql = "SELECT * FROM users WHERE id=" . $_GET['id']; $stmt = $conn->query($sql);`
**修正**：一律 `PDO::prepare()` + `bindValue()` / `execute([...])`，參數用 `?` 或 `:name`。
**驗證腳本**：
```bash
grep -n "query(" src/api/*.php        # 應為 0（除建表/DDL）
grep -c "PDO::prepare" src/api/*.php  # 每檔 CRUD ≥ 1
grep -rn "\$_GET\|\$_POST" src/api/*.php | grep -i "select\|insert\|update\|delete"  # 應為 0（參數不得直接拼 SQL）
```

### A2. .env 連線模組化，嚴禁 Hardcode
**要求**：`jl_php` 一律讀 `src/config/.env`（DB_HOST/DB_NAME/DB_USER/DB_PASS）。建一個統一的 `db.php` / `Database.php` 連接池，其他 API 檔 require 它。
**驗證**：`grep -rn "mysql_connect\|new PDO(\"" src/api/*.php | grep -v "require\|include" → 應只出現在連線模組`；全目錄不得有明文字符帳密。

### A3. JSON 輸出相容 layui
layui table 需要 `{"code":0,"msg":"","count":N,"data":[...]}`；一般 Ajax 需要統一結構。
**要求**：每個 API 檔用同一個 `json_response($code, $msg, $data)` 封裝，禁止各檔各自 echo array（會漏 count 欄位導致表格顯示 0 筆）。
**驗證**：`grep -c "json_response\|\"code\":0" src/api/*.php`；確認每個 endpoint 都有 code/msg/count/data。

### A4. 單一 PHP 檔統一處理一組 CRUD
人員管理 = 一個 `user.php` 內含 list/create/update/delete 五個 method，用 `$_GET['action']` 或 HTTP method 分流。禁止把增改刪拆到三個不同 URL（難維護、QA 審查困難）。

### A5. 🚫 嚴禁 JWT
系統純帳密驗證（Session/Cookie）。`.env` 與程式碼不得出現 `JWT`、`jwt_decode`、`HS256` 等字眼。發現即退回。

---

## B. Layui 前端（jl_ui）陷阱

### B1. form.render() 洗掉動態選項（最常見）
**機制**：`layui.use(['form'])` 載入時自動渲染所有 `<select>`，建立「假下拉」（`.layui-form-select dl dd, ddCount=1`）。JS 後段才填原生 option 時，假下拉的 dd 仍是空的。
**修正**：填完原生 `<select>` 後必須 `form.render('select')` 同步。
**驗證**：瀏覽器 DevTools → 選單點下去看 dd 實際有幾個選項（optCount=12 ≠ 能用）。

### B2. 月份選單載入後為空（optCount=0）
**症狀**：日期型工具頁（chepai/yinyuan/ziwei/hehun/lunar 等）`<select id="*Month">` 載入後空空，因 JS 只有 fillDays()、從未 fillMonths()。calc 收 NaN。
**修正**：load 時同時填充 month（12 option）與 day。
**驗證**：選 1981/05/02 午時實算，結果應正確（辛酉壬辰庚辰壬午）。

### B3. JS 引用路徑斷裂
內頁引用 `../js/blog/data.js` 失敗 → ReferenceError → 全頁空白。首頁與內頁的 `../` 層級不同，派單時要確認相對路徑。
**驗證**：瀏覽器 Network 看 JS 是否 200（不是只看 curl）。

### B4. TOC 錨點計算方式不一致
renderToc 的錨點必須用標題文字算 `#sec-{text}`（與 renderBody 一致），不能用索引 `#sec-{i}`，否則點擊跳轉對不上。

### B5. 獨立頁面 + iframe 嵌入
每組功能建立獨立頁面（`user.html`），透過 iframe 或動態載入嵌進 `index.html`。禁止把所有功能塞在一個大 html。

### B6. 原生元件重構後 CSS 無效
radio/select 改成自訂 DOM（`.layui-form-radio.layui-form-radioed` / `.layui-form-select`）後，對原生 input 寫 CSS 無效，要改自訂 DOM 的樣式。

---

## C. 農曆/日期運算陷阱（跨前後端）

### C1. lunar.js bit mapping
`LUNAR_INFO` 月份由 Dec→Jan 存在 bits 15-4。月份 m 對應 bit `(m+3)`，公式 `((info >> (m+3)) & 1) ? 30 : 29`。
**常見錯**：用 `(12-m)` 或 `(m-1)` → 所有農曆轉換全錯。
**對策**：涉及農曆的任務先 `graphify query "LUNAR_INFO"` 確認既有 mapping，不要重造輪子。

---

## D. 部署/巡檢陷阱（jl_lead 親自佈署時）

### D1. curl HTTP 巡檢有盲區
curl 只能證明檔案存在、Apache 回 200，**無法偵測瀏覽器實際點擊跳轉/路由崩潰**。全站連結巡检曾誤報「0 broken」，但無痕實測全 404（根因：.htaccess 把非檔案請求重寫到不存在的 index.php）。
**對策**：巡檢必須搭配真實瀏覽器實測或至少查 Apache error log，不得只用 curl、不得虛報成果。

### D2. 部署鐵律
專注伺服器設定與檔案佈署（.htaccess、index.php、權限），嚴禁大量改程式碼當變通。若需改程式碼才能跑，回頭檢查：(1) mod_rewrite 是否啟用 (2) AllowOverride (3) .htaccess 是否正確。

---

## QA 手動驗證速查（jl_qa 卡死時 jl_lead 用）

```bash
# PHP SQLi
grep -c "PDO::prepare" src/api/<file>.php          # ≥1
grep -rn "\$_GET\|\$_POST" src/api/*.php | grep -iE "select|insert|update|delete"   # =0

# Layui form
grep -n "form.render('select')" src/public/*.js     # 有動態 select 的頁必須有

# JS 引用
curl -sI http://localhost/js/blog/data.js | head -1 # 應 200（部署後）

# JSON 結構
grep -c "\"code\":0" src/api/<file>.php             # 每 endpoint ≥1
```
