---
name: jl-delegation-workflow
description: JL Lead (PHP/MySQL/Layui) 任務委派、Cron 監控與 QA 閉環標準作業程序 — 降低下屬委派失敗率
---

# JL Lead Delegation Workflow（PHP 8 / MySQL 8 / Layui v2.9+）

## 核心原則（遷移自 VPOS，已改寫為 PHP/Layui 情境）

1. **全面下放**：除「最終佈署至測試環境」由 jl_lead 親自執行外，所有需求分析、開發、審查任務必須委派給對應下屬（`jl_php`、`jl_ui`、`jl_qa`）。
2. **強制 Cron 監控**：每次 `delegate_task` 送出後，**必須立即**建立 Cron watchdog（`schedule: every 3m`），repeat 依任務規模調整。Cron 是防呆機制，不可依賴系統自動通知而跳過。
3. **閉環審查（Dev→QA 嚴格依序，鐵則, 2026-09-21 借鏡 vpos TASK-030）**：下屬完成 → jl_lead 獨立 grep 初步驗證 → 才指派 `jl_qa` 正式審查。**嚴禁把 dev 與 qa 並行派出**——qa 若讀到 dev 尚未寫入的過時檔案，會產出假陽性 REJECTED（TASK-030 首份報告就是因為并行委派、qa 在 dev 寫入前就 grep → 讀到 stale file）。並行委派不是中性的工程選擇，它就是 race condition 的根因之一。正確做法：(a) dev 完成 → (b) jl_lead 獨立 grep 初步驗證 → (c) 才派 qa 正式審查；或 dev+qa 同一子代理依序執行。**例外**：只有當 dev 與 qa 審查的是「完全互不相干的兩個檔案/任務」時才可並行。
4. **Lead 不親手改 code（角色鐵律）**：QA REJECTED 時，必須退回開發者重修，不可自己 patch 了事、也不可修改 QA 報告。球員兼裁判是嚴重違規。
5. **微步切割（Cron-Ready）**：單一 Task 必須能在約 10 分鐘內完成（2~3 次 Cron 週期）。涉及 >3 個檔案或 >5 處修改點，必須繼續拆分。
6. **強制 Profile 載入**：派單時嚴禁在 context 寫「你現在是 jl_php」角色扮演；必須透過 `delegate_task`（子代理自動載入其 profile）或 CLI `--profile <target>` 實體啟動下屬。
7. **主動推進**：dispatch 後 5 分鐘內必須主動檢查 `delegate_task(action='list')`，不可只等 Cron。每輪開頭先檢查是否有 pending delegate / 缺 Cron 的任務。
8. **同時下屬不超過 2 個（鐵則）**：**每次委派當下，除了 jl_lead 之外，活躍的子代理（running status）最多 2 個**。這是防卡死與上下文爆炸的硬上限——超過就表示派太開、監控會失焦。達上限時：(a) 先等現有子代理完成/停止，或 (b) 把多個小任務合併成「一個聚焦 goal」用單一子代理處理。**換專案（新工作目錄）也適用此鐵則**——它跟 jl_lead profile 綁定、存在 `~/.hermes/skills/jl-delegation-workflow`（global），不隨 suanming/ 目錄變動，因此任何專案都自動生效。

## 微步切割標準（Cron-Ready Rule）

| 任務規模 | 修改點數 | 檔案數 | Cron repeat | 預估完成時間 |
|---------|---------|-------|-------------|------------|
| 簡單修復 | ≤5 處 | ≤1 個 | 3 | <5 分鐘 |
| 中等修復 | 5~20 處 | ≤3 個 | 6 | 10~20 分鐘 |
| 大型重構 | >20 處 | >3 個 | 10 | 30+ 分鐘（需繼續拆分）|

**切割範例**：
- ❌ 「重寫整個 `user.php`」→ 太大，會卡死
- ✅ 「為 `user.php` 新增 `apiUserDelete()` 方法處理 DELETE /user?id=」（單一方法）
- ✅ 「修復 `login.php` L30-L50 的 SQL 注入（2 處：WHERE 拼接 → PDO 預處理）」

## 標準流程

### Step 0: 工作區檢查與圖譜分析（派單前強制）
1. **環境檢查**：確認 `docs/`、`review-reports/`、`src/api/`、`src/config/`、`src/public/` 存在；`task_board.json`、`issue-log.md`、`.env` 已初始化（見 SOUL.md Step 0）。
2. **Graphify 優先**：分析跨檔案依賴時，先 `graphify query "<功能>"` 釐清呼叫鏈。**grep 僅用於最終驗證**。若 graphify 無結果，改用 `graphify query "<符號> 引用"`。

### Step 0.1: Gateway Bootstrap（每次新 session 開頭強制步驟, TASK-030 教訓）

cron watchdog 只有在 `hermes-gateway-jl_lead.service` 執行時才會觸發。**每次新 session 開頭**都應先確認該 service 存在且 active，否則 watchdog 形同虛設（gateway 若於兩次 session 之間死亡，派單後才發現就太晚了）：

```bash
systemctl --user is-active hermes-gateway-jl_lead.service   # 應回傳 active
```

- **active** → 通過，繼續。
- **inactive / not-found（unit 找不到）** → 一次性修復：`hermes gateway install && hermes gateway start`（install 會啟用 systemd linger，登出後仍存活），再 `systemctl --user is-active ...` 交叉確認回傳 active。**不可只信 cronjob create/list 回傳的 `gateway_running` 欄位**——它可能因 service unit 未安裝而永遠 false。
- **⚠️ 資源提醒**：每個 gateway ~126MB RAM；jl_lead / vpos_lead / default 三個可並存。保持 jl_lead gateway 常駐是委派流程的合理需求（watchdog 依賴它），除非使用者要求省資源，否則維持常駐。
- **與 Step 3 的關係**：Step 0.1 是「session 開頭主動偵測」（從源頭避免 watchdog 不觸發）；Step 3 的 `gateway_running` 交叉確認是「派單當下二次驗證」。兩層都做，缺一不可。

### Step 0.1.1: Gateway 常駐韌性驗證（2026-09-21 新增——確認 gateway 在對話結束 / 登出 / 重啟後仍存活）
`is-active` 只證明「現在在跑」，不保證「下次開 session 或電腦重啟後還在」。委派流程的 watchdog 依賴 gateway 常駐，所以**每次新 session 開頭（Step 0.1）應連同以下四項一起檢查**，缺一不可：

```bash
systemctl --user is-active hermes-gateway-jl_lead.service   # 1. active（現在在跑）
loginctl show-user vblinux -p Linger                          # 2. Linger=yes（登出後仍活的关键）
systemctl --user is-enabled hermes-gateway-jl_lead.service    # 3. enabled（開機自動起）
pgrep -af "hermes_cli.main.*jl_lead.*gateway"                 # 4. 實際 process + PID
```

- **Linger=yes**：user systemd 服務跟帳號綁定，有 linger 時登出/登入都不會被清理。這是「對話結束後仍活」的關鍵開關——沒有 linger，帳號完全登出很長時間後 user manager 會隨之停止、gateway 被殺。
- **enabled**：重啟電腦後開機自動啟動。
- **Restart=always**（查 `systemctl --user cat hermes-gateway-jl_lead.service`）：萬一它崩了，systemd 5 秒後自動拉起（Exit 78 除外）。
- **實際 process / PID**：`is-active` 回傳 active 代表一定有 process 在跑；用 `pgrep -af "hermes_cli.main.*jl_lead.*gateway"` 抓到真實 PID（command line 是 `python -m hermes_cli.main --profile jl_lead gateway run`）。

**四項全過 = gateway 真正常駐**：對話結束、你登出登入都不影響；唯一會讓它停的是手動 `systemctl --user stop`、整台關機/重啟（enabled 會幫它在下次開機自動回來）、或 linger 被關閉且帳號完全登出很長時間。

### Step 0.1.2: Gateway 閒置時不消耗 GPU（2026-09-21 新增——澄清常見誤解）
gateway process **本身不做任何 LLM 推理**，只是一個「守門哨兵」：閒置時單純監聽、等任務進來，佔用的 ~126MB RAM 是「待命的記憶體」而非「正在算」。GPU 運算（模型推理）**只在有任務要處理時才發生**——即（a）你正在跟 jl_lead 對話、或（b）cron job 觸發且 agent 真的跑了一輪。其他所有時間（包括沒對話、沒 cron、甚至繪畫 app 開著）→ hermes **零 GPU 運算**。

⚠️ 「繪畫 / 任何應用程式開著」與「hermes 會不會定時動 GPU」**完全無關**——hermes 的 GPU 活動只跟「有沒有任務在處理」綁定，跟你開了什麼軟體無關。唯一例外：若同時開著多個 profile（vpos_lead、default）且各有 cron 在觸發，那間隙中仍可能偶有運算。

### Step 0.5: Hermes_BK 備份觸發條件鐵律（2026-09-23 借鏡 vpos TASK-037 使用者修正——糾正 jl 既有「task_board 更新就要備份」的錯誤敘述）

**背景**：原流程把「task_board / issue-log 這類被程式讀取的資料檔更新後，依 Hermes_BK 備份鐵律執行備份（與 skill/memory 同級優先）」當成紀律。這是錯的——task_board.json、issue-log.md、所有 `.cs/.php/.html/js` 原始碼、`docs/`、`review-reports/` 都是**專案可重生成物**（在 git 或程式下都能重建），QA PASS / 更新 task_board 後**一律不執行備份**。把「改專案產物」當成觸發條件，會導致每次微步都跑整批備份、徒增 I/O 與噪音。

> ⚠️ **只在「系統重灌後無法自動生成」的資料發生異動時才執行 `bash /home/vblinux/Hermes_BK/backup.sh`**：
> - ✅ **觸發備份（持久化系統資料異動）**: 新增／修改 skill（SKILL.md）、寫入／更新 memory、跨 profile 分發或同步技能、借鏡其他 profile 後回補、改 SOUL.md / config.yaml / cron。
> - ❌ **不觸發備份（專案可重生成物）**: `docs/task_board.json`、`review-reports/issue-log.md`、所有原始碼（`.cs/.php/.html/js`）、`src/` 下任何檔案。這些在 git 或程式下都能重建，**QA PASS / 更新 task_board 後一律不執行備份**。
> - **判斷口訣：「改的是專案產物就別備，改的是系統記憶才要備」。**

### Step 1: 歷程檢查（防重工）
讀取 `docs/task_board.json` 與 `review-reports/issue-log.md`：
- **已完成且 DONE** → 直接告知使用者已實作，嚴禁盲目重複。
- **未完成（TODO/IN_PROGRESS/REVIEW/REJECTED）** → 接續既有工單，不重建。
- **全新需求** → 寫入 `docs/api-spec.json` → 建立工單（status=TODO）→ 派單。
- **「還有哪些未完成」類問題**：不得只信 task_board 或單一 checklist——至少交叉比對 task_board / gap-analysis.md（勾選框常過時）/ issue-log.md（REJECTED 可能已被親自重做標 DONE）。細節見 `references/task-board-lifecycle.md` Step 1b。

### Step 2: 任務委派與 Context 預載
- **後端/DB/API** → `jl_php`（工作目錄：`src/api/`、`src/config/`）
- **前端/Layui/表格/Ajax** → `jl_ui`（工作目錄：`src/public/`）
- **審查/QA/資安** → `jl_qa`（工作目錄：`review-reports/`）

派單時**必須在 goal 中附帶團隊架構約束條款**（見下方「派單必附條款」），並直接附上目標檔案行號範圍與修改前後預期 Snippet，避免子代理讀整份大檔。

### Step 3: 建立 Cron 監控（派單後立即）
```
cronjob(action='create', schedule='every 3m', repeat=<依規模>, prompt='檢查子代理是否仍在工作、檔案是否有更新痕跡；若連續 2 次無進展回報卡死')
```
**每次 delegate_task 完成後，回應中必須包含**：
```
✅ delegate_task 已派出 (delegation_id: ...)
📋 Cron watchdog 已建立 (job_id: ..., schedule: every 3m)
⏰ 5 分鐘後主動檢查子代理狀態
```

#### ⚠️ 強制前置條件與豁免禁令（2026-09-19 新增，因 T-37/T-38 漏建 watchdog + gateway 未跑而補強）
1. **Gateway 必須在跑**：cron job 只有在 gateway 服務執行時才會觸發。派單前先確認 `systemctl --user status hermes-gateway-jl_lead.service`（或 `hermes gateway status`）顯示 `active (running)`；若未跑，先 `hermes gateway install && hermes gateway start`。cron job 已建立但 gateway 沒跑 = 不會觸發 = 形同虛設。**🔥 Gateway 狀態交叉確認（2026-09-21 借鏡 vpos TASK-030）**: cronjob create/list 回傳的 `gateway_running` 欄位是「cron 會不會觸發」的權威來源，但**不可只信一個欄位就下結論**。當它回報 false 時，必須再直接跑一次 `hermes gateway status`（或 `systemctl --user status hermes-gateway-jl_lead.service`）交叉確認——工具欄位可能因服務尚未完全就緒、已退出、或與 cron 子系統檢查的 service unit 不同步而誤報。回報 false = 先 `hermes gateway start`，再重新建立 watchdog。**重派 qa 複查時也要為新委派建立 watchdog**（TASK-030 漏洞③：重派 re-verification qa 只手動 tail transcript、漏建 watchdog）。
2. **零豁免**：任何委派（含「只改一個檔案、機械式批量替換」的任務）都必須在送出 delegate_task 當下立即建立 watchdog，不得以「任務太小/太快完成」為由跳過。漏建 watchdog 視為流程違規。
3. **回應必報**：每次委派後的回覆中，必須明確列出 watchdog job_id 與 schedule；沒有就代表沒建。
4. **清理過期**：舊任務（如 T-35）的 watchdog repeat 到點後會自動結束，若清單堆積已到期、無對應進行中任務的 watchdog，應主動 `cronjob action='remove'` 刪除，避免垃圾累積。

### Step 4: QA 審查（jl_qa）
- 優先 `delegate_task` 給 jl_qa；若卡死 >15 分鐘或 review-reports/ 無報告 → jl_lead 手動 grep 驗證並更新 task_board。
- **手動驗證範例**：`grep -c "PDO::prepare" src/api/user.php`、`grep -rn "form.render('select')" src/public/*.js`。

### Step 5: 通知使用者驗收
QA PASS → status=DONE + `qa_review="PASS"` + `qa_review_file`。**通知使用者後進入待命**，除非說「繼續」否則不主動派新任務、不更新 task_board。

## 派單必附條款（寫入每個 delegate_task 的 goal）

> ⚠️ **團隊目錄與架構約束（主管禁令）**：
> 1. 嚴格在指定目錄產出檔案（`jl_ui` 僅限 `src/public/`；`jl_php` 僅限 `src/api/` 與 `src/config/`）。
> 2. **獨立頁面 + 獨立 API 模組化**：每組功能（如人員管理含增改刪查）前端建立獨立頁面（如 `user.html`），後端建立對應一組 PHP 統一處理 CRUD，輸出相容 layui 的 JSON：`{"code":0,"msg":"success","count":100,"data":[...]}`。
> 3. `jl_php` 連線一律解析 `src/config/.env`，**嚴禁 Hardcode 帳密**。
> 4. 🚫 **純帳密驗證（Session/Cookie）**。**嚴禁引入 JWT**，禁止在 `.env` 或程式碼中產生 JWT 相關參數。
> 5. 開發前先用 `graphify query "<關鍵字>"` 查詢既有元件連接方式。
> 6. 嚴禁隨意建立非必要的子目錄或臨時檔。
> 7. 完成後將 `docs/task_board.json` 該 Task 狀態更新為 `REVIEW`，並附 `ls -la` + grep 驗證結果。

## PHP/Layui 委派失敗高頻陷阱（我的真實教訓）

### 陷阱1: Layui form.render() 洗掉動態選項
**問題**：頁面用 `layui.use(['form',...])` 載入時，Layui 會自動渲染所有 `<select>`，建立「假下拉」（`.layui-form-select dl dd, ddCount=1`）。若 JS 後段才手動填原生 `<select>`（如 fillMonths/fillDays），假下拉的 dd 仍是空的 → 使用者看到空下拉。
**派單必附**：「動態填充 `<select>` 後，必須再呼叫 `form.render('select')` 同步；不能只填原生 option。Layui 先建空的假下拉，ddCount=1 ≠ 能用。」

### 陷阱2: 子代理耗在自測框架而非任務本身
**問題**：連續多個子代理卡在「自己寫的 Node vm sandbox 驗證腳本」（mock document.createElement、mock layui.use、innerHTML='' 不清空 children 導致 option 累加）。這與實際任務無關，是內耗。
**對策（主管應做）**：以簡化 mock 獨立驗證核心邏輯即可（如 window.X 可正常載入 + innerHTML setter 清空 children），不讓子代理耗時除錯自測框架。若發現子代理卡在同一個自測工具 >9 分鐘，立即刪除重派並給更聚焦的 goal。
**可執行工具**：UMD 包裝的瀏覽器風格 JS（bazi.js/lunar.js）在 Node 直接 require/eval 會因 `window is not defined` / module.exports 分支失敗。**主管獨立驗證標準解法見 `references/browser-js-verification.md`**——核心是 `vm.createContext` + `sandbox.window = sandbox` 強制走 UMD else 分支，然後只 eval lunar.js+bazi.js 取得 res、獨立複製渲染邏輯做非空驗證（不 eval IIFE），搭配 `node --check` 語法檢查與 CDP Chrome 實測。此解法是 jl_lead 親身試 ~10 次後確立，子代理普遍在此栽跟頭。

### 陷阱3: curl HTTP 巡檢有盲區（不得虛報）
**問題**：curl 只能證明檔案存在、Apache 回 200，無法偵測瀏覽器實際點擊跳轉/路由崩潰。全站連結巡检曾誤報「0 broken」，但無痕實測全 404（根因：.htaccess 把非檔案請求重寫到不存在的 index.php）。
**對策**：巡檢必須搭配真實瀏覽器實測或至少查 Apache error log，不得只用 curl、不得虛報成果。

### 陷阱4: 前端 JS 引用路徑斷裂
**問題**：內頁（如 `blog/detail.html`）引用 `../js/blog/data.js` 失敗時，`getBlogById` 拋 ReferenceError，所有內頁空白（連原有資料都受影響）。
**對策**：派單檢查「相對路徑是否正確」（內頁 vs 首頁的 `../` 層級不同），完成後用瀏覽器實測各頁面能載入所需 JS。

### 陷阱5: TOC 錨點計算方式不一致
**問題**：renderToc 的 TOC 錨點必須用標題文字計算 `#sec-{text}`（與 renderBody 一致），不能用索引 `#sec-{i}`，否則點擊跳轉對不上。
**對策**：涉及多頁共用渲染邏輯時，要求子代理確認「锚點計算方式在所有頁面一致」。

### 陷阱6: lunar.js 月份 bit mapping 易錯
**問題**：`LUNAR_INFO` 月份由 Dec→Jan 存在 bits 15-4。月份 m 對應 bit `(m+3)`，公式 `((info >> (m+3)) & 1) ? 30 : 29`。常見錯誤用 `(12-m)` 或 `(m-1)` → 所有農曆轉換全錯。
**對策**：涉及農曆/日期運算的任務，提醒子代理先 `graphify query "LUNAR_INFO"` 確認既有 bit mapping，不要重造輪子寫錯位移。

### 陷阱7: 月份選單載入後為空（optCount=0）
**問題**：多個日期型工具頁（chepai/yinyuan/ziwei/hehun/lunar 等）的 `<select id="*Month">` 載入後為空，因各 JS 只有 fillDays() 填「日」、從未填充「月」。calc 收 NaN 無法運算。
**對策**：涉及日期選擇的工具頁，要求「load 時必須同時填充 month（12 option）與 day 選單」，完成後用真實日期實測運算結果正確。

### 陷阱8: 共用 JS 資料檔的相對路徑連結——子目錄頁面點擊崩潰（curl-only 巡檢必漏）
**問題**：`js/cate/articles.js`、`js/app.js` 等「共用資料檔」內的文章卡片連結若用**相對路徑**（如 `url:'blog/detail.html?id=1420'`），瀏覽器會相對於「點擊時所在頁面的目錄」解析。從根目錄 `/blog/index.html` 點 OK，但從子目錄 `/cate/changshi.html`、`/type/dianji.html` 點就變成 `/cate/blog/detail.html` → **404**。全站曾誤報「0 broken」（curl 把相對路徑解析到網站根目錄回 200），無痕實測全崩。
**對策**：共用資料檔內的文章連結一律用**絕對路徑**（根相對 `/blog/detail.html`、`/blog/thumb_...webp`）。派單時明訂「articles.js/app.js 的 url/img 欄位必須 `/` 開頭」。完成後用 `scripts/site-link-audit.py`（CDP 逐頁載入並點擊每個相對連結）實測，exit=0 才算過。此工具是陷阱3（curl 盲區）的執行版。

### 陷阱9: CDP Chrome 快取陷阱——Apache 交付新檔但瀏覽器載入舊 JS（本次 T-37/T-38 親身教訓）
**問題**：`src/public/js/cate/articles.js` 已改好、Apache `curl` 交付的也是 md5 一致的新檔，但 browser_exec 實測時卡片 href **仍是舊的相對路徑**（`http://localhost/cate/blog/detail.html`）。根因是 browser_exec 依賴的 Chrome（port 9222，profile `/tmp/chrome-suanming-profile`）快取載入了舊版 JS。
**為什麼 grep/curl 抓不出來**：grep 核對的是 `src/` 源碼、curl 驗證的是 Apache 交付內容——兩者都是新檔，但**瀏覽器快取是第三份狀態**，完全不在檢查範圍內。
**對策（主管必做）**：遇到「Apache 交付正確但瀏覽器結果不對」時，不要懷疑程式碼，直接重啟 Chrome：
```bash
# 1. kill 現有除錯 Chrome（注意：browser_exec 依賴 port 9222 的 Chrome）
pkill -f "remote-debugging-port=9222"; sleep 2
# 2. 用全新空 profile + --remote-allow-origins=* 重啟（避免快取污染）
rm -rf /tmp/chrome-suanming-profile
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-suanming-profile \
  --no-first-run --disable-gpu --headless=new --remote-allow-origins=* &
# 3. browser_exec 重連後再實測，結果即為真象
```
**注意**：browser_exec 內建的 CDP 包裝器對 `Network.setCacheDisabled` / `Page.navigate` 有已知限制（sessionId 錯誤、參數格式報 -32601/-32602），手寫原始 websocket 腳本也常因 `/json/new` 需 POST、`--remote-allow-origins` 未加而失敗。**最穩解法就是 kill + rm profile + 重啟**，不要耗時在 CDP 參數除錯上。

### 陷阱10: 「改 src ≠ 已部署」——grep 核對源碼抓不出「下屬漏部署」（本次 T-37/T-38 親身教訓）
**問題**：jl_ui 完成 T-37 後回報「articles.js 全部改為絕對路徑、node --check 通過」，但實際只改了 `src/public/js/cate/articles.js`（源碼），**沒部署到 `/var/www/html/`**。grep 核對 src 完全正確（相對=0、絕對=31），卻看不出來測試機上是舊檔。
**為什麼 DoD grep 抓不出來**：DoD 的「實質內容 grep」檢查的是 `src/`，而部署是另一份狀態。下屬改完源碼就標 REVIEW，主管若只 grep src 就會誤判完成。
**對策（主管必做）**：任何委派任務回報完成後，DoD 驗證必須同時檢查**兩份 md5 一致**——
```bash
md5sum src/public/js/cate/articles.js /var/www/html/js/cate/articles.js   # 必須相同
# 若不同 = 下屬漏部署，主管親自 sudo cp + chown www-data:www-data + chmod 644
```
**延伸（本次 T-38）**：即使部署了，也要看**實際渲染結果**。jl_ui 把 `img:'blog/thumb_...'` 改成 `/blog/thumb_...`，但 line 156 渲染用 `src="img/'+a.img+'"` → 拼出 `img//blog/thumb_...`（雙斜線骯髒寫法），grep 數得出「6 個絕對路徑」卻看不出來拼接錯誤。必須用瀏覽器實測 `getAttribute('src')` 確認渲染正確、圖片 HTTP 200，不能只信 grep 計數。

### 陷阱11: HTML `<tr>`/`</tr>` grep 全檔計數會因「資料字串」誤判（F-04 line 101 教訓）
**問題**：修完 bazi-report.js line 101 的 `</tr>` 錯位 bug，用 `grep -c '</tr>'` vs `grep -c '<tr'` 比對，得到 `<tr`=16、`</tr`=20（淨 +4），誤以為還有懸空標籤。實際該表格區塊已平衡（5 `<tr>` = 5 `</tr>`）。
**為什麼誤判**：line 73-76 的 `.split('</tr>')`、`.replace('<tr>','')` 等，把 `</tr>`/`<tr>` 當成**資料字串**而非 HTML 結構。全檔 grep 會把这些「資料」也算進去 → 計數失衡是假訊號。
**對策（主管必做）**：驗證表格結構時，**限定到該表格的行號範圍**再計數（如 `sed -n '97,108p'` 後 grep），不要全檔 grep。或更穩：用 Node vm sandbox 跑 renderReport()、dump dyHtml 實際數 `<tr>`/`</tr>` 是否成對。

### 陷阱12: file-mutation verifier「檔案未改」假警報不可盡信（F-04 line 101 教訓）
**問題**：jl_ui 回報修完 line 101，但它的 patch 工具回傳 `File-mutation verifier: NOT modified`、`Could not find a match for old_string`。若照此假設「沒改成功」就重派或自己 patch，會破壞已正確的下檔。
**為什麼假警報**：子代理可能用 terminal sed/heredoc 而非 patch 工具落地修改，patch 工具的 old_string 比對失敗（例如字串含特殊字元、行內有多個 `</tr>` 導致模糊匹配）→ verifier 誤判「未改」，但實際檔案已正確。
**對策（主管必做）**：子代理自報完成 + verifier 警告同時出現時，**親自讀原碼 + md5 src=deploy 核對實質內容**，不要信 verifier 的「NOT modified」。本例 line 101 實際已是 `'+d.zhi+'</td>'`（無多餘 `</tr>`），md5 兩邊一致 → 已完成。

## 跨領域借鏡：通用委派流程陷阱（借鏡 VPOS，2026-09-22 整合）

以下教訓源自 VPOS Avalonia 專案的真實任務（TASK-014~034），**與語言/框架無關**，是「多檔案委派 + Cron 監控 + QA 閉環」的通用缺陷。已驗證可套用到 PHP/Layui 情境，收進本流程。（C#-specific 陷阱如 CS0122、ImageSharp migration、proxy property 不適用，刻意不搬。）

### 陷阱13: cron watchdog 不可用 delegate_task 第二項建立（混淆工具）
**問題**: 需要「dev 子代理 + cron watchdog」時，把兩者當成 `delegate_task(tasks=[...])` 的兩個項目並行送出。第二個 item（「建立 TASK-XXX 的 cron watchdog」**不是真正的 cron**——它變成一個假的、被立即停止的子代理，因為 cron watchdog 必須用獨立的 `cronjob_manage(action='create')` 建立。**根因**: 混淆了「委派子代理」（`delegate_task`）與「排程 cron」（`cronjob_manage`）兩個不同工具。
**修正（鐵律）**:
- `delegate_task(tasks=[...])` 的每個 item **都是「一個子代理」**。若同一輪需要 dev + watchdog，用**一次 delegate_task（只放 dev goal）**＋**一次獨立的 cronjob_manage(action='create')**。兩者分開呼叫，絕不塞進同一個 fan-out。
- 送出後回應必報兩個不同來源的 ID：`✅ delegate_task delegation_id: deleg_XXXXX` ＋ `📋 Cron watchdog job_id: XXXXX, schedule: every 3m`。任一缺失 = 漏建。

### 陷阱14: 委派週期收尾必須做 watchdog 對帳（無訊號盲區）
**問題**: 「任務太小、完全沒建 watchdog」是另一種失敗模式——它**沒有任何紅燈訊號**：任務小而快，跑完直接回傳 PASS，Lead 順手就進 board 或通知使用者。既有「零豁免」規則剛好斷裂在這個無訊號盲區。**根因**: 「漏建 watchdog」不會產生即時失敗；它只在任務完成後才顯現為 orphan（active delegation 沒有對應 cron job_id）。
**修正（鐵律 — 委派週期收尾檢查）**:
- **每輪結束、在宣告完成或通知使用者驗收之前**，一律先跑一次 `cronjob action=list` ＋ `delegate_task action=list`，執行對帳：
  1. 列出所有 active delegation。
  2. 每個 active delegation 都必須有且僅有一個 watchdog job_id。
  3. 已完成的任務，其 watchdog 必須已被移除；若還在 = orphan，立即 `cronjob action='remove'`。
- **回應格式**：每輪委派週期結束時明確標註：`📋 Cron watchdog 對帳: active delegations=0, orphan jobs=0 ✅`。發現 orphan → 立即 remove 再標註已清理。
- **每輪開頭也檢查**：若上輪有委派但回應裡沒有 watchdog 對帳行，這輪開頭立即補跑 `cronjob action=list` 並對帳。

### 陷阱15: jl_qa delegate_task 完成審查卻不寫報告檔（交付物缺失）
**問題**: QA 子代理連續三次完成審查、給出合理 PASS verdict，但每次都沒把報告寫入 `review-reports/`。它以為「回覆 verdict JSON」就是完成，實際漏了 write_file + ls 確認。**根因**: 子代理對「完成」的定義與 DoD 不符——產出了結論但沒產生交付物（報告檔）。
**修正**:
- 派 jl_qa 時 DoD 明確寫入：「完成 = 用 write_file 把報告寫入 `review-reports/review-TASK-XXX-*.md`，並用 `ls -la` 確認檔案存在」。只回 JSON verdict 不算完成。
- jl_qa 回報 completed 後，jl_lead **必須** `ls review-reports/ | grep TASK-XXX` 獨立確認報告檔存在。不存在 = 未完成。
- 連續 2 次（約 7~9 分鐘）仍不寫 → jl_lead 接管：用實質內容 + 一致的 verdict，手動撰寫報告並標 DONE。**code 是下屬改的、報告只是記錄已驗證事實 ≠ 球員兼裁判**（角色鐵律）。

### 陷阱16: cascade / 多檔案任務必須先全目錄掃描，不得依賴派單清單
**問題**: 子代理收到一份「已分析好的檔案清單」後，將其視為完整範圍，沒有自行執行 `grep -r` 驗證是否還有遺漏 → 遺漏檔案（管窺效應）。這是陷阱5（graphify/grep）在「多檔案委派」情境的具體化。
**修正（Lead 派單前必做）**:
- **❌ 禁止**：不 grep 全目錄就派單多檔案替換/新增任務。
- **✅ 強制**：每次委派涉及多檔案的任務前，**必須先執行** `grep -r '舊模式' src/api/ src/public/`（依任務範圍選目錄）取得完整清單，並把完整清單放入 goal。
- **✅ 強制**：goal 中明訂「完成後必須自行 grep 全相關目錄確認無殘留，不要只檢查派單提供的檔案」。
- 若 grep 結果 >10 個檔案，考慮拆成多個 subtask（避免子代理認知負載過高）。

> ⚠️ 與既有規則的關係：陷阱13/14 強化「建立監控」段（每次新委派必建 cron + **收尾對帳**）；陷阱15 強化 Step 4 QA 審查（報告檔是交付物，非可選）；陷阱16 把 graphify/grep 原則延伸到「派單前全目錄掃描」。這四條與既有「零豁免 watchdog」「Dev→QA 依序」「DoD 獨立驗證」互補，不重複。

### 陷阱17: sibling subagent 同時改 task_board.json → patch fuzzy matching 匹配舊行號（JSON 語法錯誤）
**問題**: vpos_qa 的 delegate_task 子代理嘗試更新 `task_board.json`，同時 vpos_lead 也對同一檔案執行 `patch`。由於 sibling subagent 可能已修改內容，vpos_lead 的 patch fuzzy matching 會匹配到舊行號 → JSON 語法錯誤（JSONDecodeError: Expecting ',' delimiter）。
**根因**: JSON 對格式/行號極度敏感，fuzzy matching 在「檔案已被他人改過」時必然失準。
**修正（Lead 必守）**:
- 派發任何會寫 `task_board.json` 的子代理後，若 lead 自己也該檔動手 → **先 `read_file` 取得當前內容**，確認 sibling 是否可能已改。
- **若 sibling 可能已修改 → 用 `write_file` 完整重寫而非 `patch`**。不要依賴 patch 的 fuzzy matching 處理 JSON（JSON 對格式敏感）。
- 派單時必附提醒：「若 sibling subagent 可能已修改 `task_board.json`，請用 `write_file` 完整重寫而非 `patch`。」

### 陷阱18: CRLF↔LF 行尾混淆地獄（cosmetic diff 被當成實質錯誤，越修越糟）
**問題**: 子代理用 patch/write_file 寫入檔案後，可能把整檔從 CRLF 轉成 LF → `git diff --stat` 顯示「539 insertions / 539 deletions」全檔異動。子代理嚇到，瘋狂用 sed/python 還原 CRLF：(a) `sed -i 's/$/\r/'` 會把已 CRLF 的行變成 CR+CR（行尾翻倍），(b) `git checkout` 會把實際修改也還回去 → 內容一度翻倍、卡死 16+ 分鐘。
**根因**: 子代理把「行尾轉換的 cosmetic diff」當成「實質錯誤」來修，越修越糟。
**修正（派單時必附）**:
- `git diff --stat` 顯示全檔異動 = 99% 是 CRLF↔LF 行尾噪音，不是真出錯。**用 `git diff`（看實質內容）+ python 檢查確認無損毀即可**：
  ```bash
  git --no-pager diff <檔案>            # 實質內容只有一行變更 = DONE
  python3 -c "d=open('<檔案>','rb').read(); print('null:',d.count(b'\x00'),'CRLF:',d.count(b'\r\n'))"  # 無 null bytes、行數未翻倍
  ```
- **不要**讓子代理去「還原 CRLF」。只要 git diff 實質內容符合預期就過。
- 若真的要統一行尾，用 python binary mode（先全轉 LF 再全轉 CRLF），絕不用 `sed 's/$/\r/'`：
  ```python
  d=open(f,'rb').read(); d=d.replace(b'\r\n',b'\n').replace(b'\r',b'\n').replace(b'\n',b'\r\n'); open(f,'wb').write(d)
  ```

### 陷阱19: task_board.json / 流程檔更新後未做 JSON 驗證 + 未備份（流程紀律缺口）
**問題**: vpos 教訓——子代理或 lead 改完 `task_board.json`、`issue-log.md` 等流程檔後直接跳下一步，沒有執行 JSON 語法驗證；若 JSON 壞掉，後續所有讀取 task_board 的邏輯（含防重工檢查）全部失效且難以察覺。
**根因**: 「更新 task_board」被當成機械動作，忽略了「它也是會被程式解析的資料檔」。
**修正（Lead 必守）**:
- **每次寫入 `task_board.json`（Phase 1 建立 / Phase 2 REVIEW / Phase 3 DONE）後，必須立即執行 JSON 驗證**：
  ```bash
  python3 -c "import json;json.load(open('docs/task_board.json'));print('JSON OK')"
  ```
- 驗證通過才算完成該步；壞掉 → 用 `write_file` 重寫成合法結構，不得帶著坏檔進入 QA。
- **流程紀律**：task_board / issue-log 這類檔案是**專案可重生成物**（git/程式下都能重建），更新後**不觸發 Hermes_BK 備份**（依 Step 0.5 備份觸發鐵律）。只有 skill/SOUL/config/cron/memory 等「系統持久化資料」異動才需備份。
- 派單時必附提醒：「改完 `docs/task_board.json` 後必須 `python3 -c \"import json;json.load(open('docs/task_board.json'))\"` 驗證，壞檔不得進入 QA。」

> ⚠️ 與既有規則的關係：陷阱17 補強 DoD「實質內容 grep」之後的 JSON 安全寫入（sibling 並發情境）；陷阱18 是跨語言通用的行尾防呆，避免子代理在 cosmetic diff 上內耗卡死；陷阱19 把 task_board 當「資料檔」對待、補上 JSON 驗證紀律。**但「備份」面向已依 vpos TASK-037（2026-09-23）修正**：task_board/issue-log 是專案可重生成物，更新後不觸發 Hermes_BK 備份（見 Step 0.5）。這三條與 DoD 第2條（實質 grep）、Step 0.5 備份觸發鐵律互補。

### 陷阱20: 盲目信任委派回傳 status 字串，未查 disk artifact（借鏡 vpos TASK-037 G3 Part A, 2026-09-23）
**問題**: 收到子代理 `status=failed`（context window overflow）或 `status=blocked`（output_schema 為空），據此斷言「審查失敗、沒有任何成果」，並準備自己重寫一份品質較差的報告。實際上第 2 輪子代理在 context overflow **之前**已把完整 QA 報告寫入 `review-reports/`（後來 write_file 因檔案已存在而拒絕覆寫，才揭露真相）。
**根因**: 把「委派回傳的狀態字串」當成「成果是否存在」的權威來源。狀態字串只是線索（line clue），disk 上的實際 artifact（報告檔、git diff、transcript）才是事實（fact）。子代理在 context overflow / blocked 前可能已寫入部分或全部交付物，直接放棄會遺失這些成果。
**修正（鐵律 — failed/blocked 後的第一動作）**：
- 任何委派回傳 `failed` / `blocked` / `incomplete` / 非預期狀態時，**第一時間先查 artifact，不要先下結論**：
  ```bash
  ls -la review-reports/ | grep TASK-XXX          # 報告檔是否已存在
  git --no-pager diff --stat <target_file>         # dev 檔案實質變更
  tail -50 <live_transcript_path>                  # transcript 最後痕跡
  ```
- 若 artifact 顯示成果已寫入（例如報告檔存在且內容完整），即使 status=failed，也**視為已完成**、直接推進下一步（更新 task_board + 通知驗收），不要重做或丟棄。
- 只有當 artifact 確認「真的沒有產出」時，才判定為需要重派/接管。
- **判斷順序**：artifact 存在且完整 → PASS；artifact 部分存在 → 視情況補強；artifact 完全不存在 → failed，重派。

> ⚠️ 與陷阱12（file-mutation verifier「未改」假警報）、子代理卡死處理段（status=failed 讀 last_output tail）互補：三者都強調「以 disk artifact 為準，不以 status/verifier 字串為準」。狀態字串和 verifier 回傳都只是線索，disk 上的實際交付物才是事實。

## Lead 角色鐵律（最嚴重違規）

- **❌ 禁止**：QA REJECTED 時 jl_lead 自己 patch 改 code（下屬失去學習機會、流程斷裂）。
- **❌ 禁止**：jl_lead 修改 `review-reports/review-TASK-*.md`（球員兼裁判）。
- **✅ 強制**：REJECTED → 退回開發者重修 → 完成後重新指派 QA 複查 → PASS → DONE。

## 子代理卡死處理

**先診斷再動手**：派單後若 watchdog（cron）或 `delegate_task(action='list')` 顯示某子代理疑似卡死，**先用 `scripts/monitor_subagent.py` 讀出它停在哪、為什麼卡**，再決定是等、重派還是刪除。這比直接盲派新任務更精準：

```bash
# 單一子代理（含 manifest.json 權威 status + log tail）
python3 scripts/monitor_subagent.py <delegation_id>

# 一次列出所有 live 子代理狀態（快速找出 running+stuck=true 的）
python3 scripts/monitor_subagent.py --all
```

**輸出欄位解讀**：`status`（running/completed/failed）、`manifest_status`（manifest.json 權威來源）、`exit_reason`、`stuck`（log 停更 >10 分鐘 = 疑似卡死）、`recommendation`。

判定與處置：
- `status=completed` + `stuck=false` → 已完成，進入 DoD 驗證（grep / md5 / ls）。
- `status=failed` / `exit_reason=error|interrupted` → **第一動作先查 disk artifact**（報告檔是否存在、git diff 實質變更），不要直接下結論——見陷阱20「盲目信任 status 字串」。artifact 確認無成果後，才讀 `last_output` tail 看錯誤原因；商業邏輯錯退回重修，環境/工具錯可考慮重派。
- `status=running` + `stuck=true`（log 停更 >10 分鐘）→ 卡死。連續兩次委派 >9 分鐘無產出時：
  1. 刪除該卡死子代理，重建全新子代理，重派聚焦 goal（縮小到單一方法/單一行號範圍）。
  2. 或改用 `execute_code`（Python + regex）進行機械式批量替換（如統一 rename、批量補 using），但**商業邏輯判斷仍要委派**。

> ⚠️ **工具定位**：`monitor_subagent.py` 是「輔助診斷」，不取代權威來源。即時狀態以 `cronjob_manage(action='list')` ＋ `delegate_task(action='list')` 為準；本腳本用於「卡死當下讀出停在哪、log tail 是什麼」，幫助判斷該等/重派/刪除。它只讀 jl_lead profile 的 delegation cache（`cache/delegation/live/<id>/manifest.json + task-N.log`），跨 profile 不適用。

## 每輪開頭檢查清單

- [ ] 是否有 pending 的 delegate_task 未處理？
- [ ] 每個進行中任務都有對應 Cron job 嗎？缺則立即補建。
- [ ] task_board.json 是否有 REVIEW→DONE 跳過開發者重修的情形？有則補發修正任務。
- [ ] 上一輪委派是否附帶「派單必附條款」與行號範圍？

## 跨人格技能／記憶分發（JL 版，2026-09-18 新增）

當我在 lead 端**新增或更新委派/審查類 skill**、或把教訓寫進各 persona MEMORY.md 時，必須按工作範圍同步到對應下屬 profile。

### 關鍵事實：profile skills 是「複製」非 symlink；global skills 自動共用
- **profile `skills/`**（jl_lead / jl_php / jl_ui / jl_qa）是**獨立副本**，不是連結。在 lead 新增 skill **不會**自動出現在下屬。必須手動 `cp -r` 分發，並用 `ls` 驗證。
- **global `skills/`**（`~/.hermes/skills/`）所有 profile **自動共用、零摩擦**。換專案（新工作目錄）也照載——技能存在 profile/global 層級，不在專案目錄（如 `~/suanming/`），故與專案解耦。
- **2026-09-20 更新**：`jl-delegation-workflow` 已升到 global（分布 `Gjjjj` = global + jl_lead/jl_ui/jl_php/jl_qa）。因此委派/QA 流程類技能換專案**自動生效、無需分發**。但 **php-layui-pitfalls、browser-js-verification 仍在 profile 層**，換專案仍需手動 `cp -r` 給下屬。

### 分發矩陣（按下屬工作範圍）
| 技能／記憶類別 | lead | php | ui | qa |
|---|---|---|---|---|
| 委派／QA 流程類（jl-delegation-workflow、refactoring-qa-review） | Y | **Y** | **Y** | **Y** |
| PHP/API 專屬（php-layui-pitfalls） | Y | **Y** | N（無 API 範圍） | **Y** |
| 前端驗證專屬（browser-js-verification） | Y | N | **Y** | **Y** |
| MEMORY.md 教訓 | 寫入對應職責段落 | PHP/DB 根因+修復 | UI 重構教訓 | QA 審查重點 |

### 分發後驗證（必做）
```bash
for s in jl-delegation-workflow php-layui-pitfalls browser-js-verification; do printf "%-38s php=%s ui=%s qa=%s\n" "$s" \
  "$( [ -d /home/vblinux/.hermes/profiles/jl_php/skills/$s ] && echo Y || echo N )" \
  "$( [ -d /home/vblinux/.hermes/profiles/jl_ui/skills/$s ] && echo Y || echo N )" \
  "$( [ -d /home/vblinux/.hermes/profiles/jl_qa/skills/$s ] && echo Y || echo N )"; done
```
PHP 層 skill → php+qa（ui 無 API 範圍故不發）。分發後務必 `ls` 確認存在，再執行 Hermes_BK 備份。

## Definition of Done（DoD）實體寫入驗證 — 鐵律

子代理回報完成後，**必須獨立驗證**，不可信任其自報數字：
1. **檔案痕跡**：`ls -la <target_file>` 比對修改時間與大小是否為最新。
2. **實質內容 grep**：例如 `grep -c "PDO::prepare" src/api/user.php`、`grep -rn "form.render('select')" src/public/*.js`，確認修復點數與預期一致。
3. **DoD 計數不可靠** — vpos 教訓：子代理回報的修改處數常與實際不符，lead 必須自己 grep 核對。
4. **部署一致性（本次 T-37/T-38 教訓，必做）**：委派任務完成後，`md5sum src/... <deploy>/...` 兩邊**必須相同**。不同 = 下屬漏部署，主管親自 `sudo cp` + `chown www-data:www-data` + `chmod 644`。grep src 正確 ≠ 測試機已更新。
5. **渲染驗證（本次 T-38 教訓，必做）**：涉及 DOM 渲染的任務，必須用瀏覽器實測 `getAttribute('src'/'href')` 確認實際輸出正確（例如 `img//blog/...` 雙斜線、拼接錯誤），grep 看不出來。圖片需 HTTP 200。
6. **CDP Chrome 快取陷阱**：Apache curl 交付正確但瀏覽器結果不對時，先重啟 Chrome（kill + rm profile + 重啟）再實測，別懷疑程式碼。
7. 前端任務完成 → 用 CDP/瀏覽器實測頁面能載入所需 JS、無 console error（curl 回 200 ≠ 瀏覽器可用）。

## 參考文件（references/）
- `php-layui-pitfalls.md`：PHP API + Layui 表格/Ajax 的完整陷阱對照與驗證腳本。
- `task-board-lifecycle.md`：task_board.json 三階段生命周期與 JSON 更新注意事項。
- **陷阱8 執行工具**：`scripts/site-link-audit.py`（CDP 全站連結回歸偵測器，逐頁載入並點擊每個相對連結抓 404）。
- **委派完成驗證工具**：`scripts/deploy-check.sh`（主管必用）——掃描 `src/public/js/*.js`，比對 src vs `/var/www/html` md5 + `node --check` 語法檢查。下屬回報完成後先跑這個，exit=0 才算「源碼與部署一致」。排除 tests/、*-test.js、*-xcheck.js（開發除錯檔不上線）。這是 DoD 第4條的機械化執行版。
- **子代理卡死診斷工具**：`scripts/monitor_subagent.py`——讀 jl_lead delegation cache（`cache/delegation/live/<id>/manifest.json + task-N.log`），輸出 `status / manifest_status / exit_reason / stuck / recommendation`。卡死當下用它讀出「停在哪、log tail 是什麼」，判斷該等/重派/刪除；不取代 `cronjob_manage list` ＋ `delegate_task list`（權威即時來源）。`--all` 可一次列出所有 live 子代理。
- **跨 Profile Skill 借鏡方法論**：`references/cross-profile-skill-borrowing.md`——審查其他 profile skill（vpos/jl_php）時，「通用 vs 語言專屬」篩選原則、工具 cp-vs-改良決策、jl_lead delegation cache 結構與執行流程。
