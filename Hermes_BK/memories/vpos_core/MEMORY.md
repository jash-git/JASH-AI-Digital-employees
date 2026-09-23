## vpos_core 專屬記憶 — C# 後端/硬體/同步/ORM 工程師

### 工作範圍
- 僅限修改：VPOS_Avalonia/DBLib/, VPOS_Avalonia/WebAPI/, VPOS_Avalonia/WinAPI/, VPOS_Avalonia/ToolLib/, VPOS_Avalonia/Thread/, VPOS_Avalonia/Models/, VPOS_Avalonia/Json2Class/
- 禁止修改：Views/, ViewModels/, UserControl/（這些是 vpos_ui 的範圍）

### 開發約束條款
1. 嚴禁在 Code-Behind (.axaml.cs) 中編寫商業邏輯
2. 所有非同步/背景作業必須注意 UI 執行緒切換（Dispatcher.UIThread.InvokeAsync）
3. 硬體 (WinAPI) 與 WebAPI 通訊必須包含異常捕捉與 Retry 機制，嚴禁阻塞 UI 主執行緒
4. SQL 查詢必須使用 Dapper 參數化 (@param)，嚴禁 string.Format 拼接 SQL
5. 使用共享 SQLiteConnection 時，所有 _sharedConnection.Query 必須改為 GetSharedConnection().Query
6. HttpClient 必須使用 HttpRequestMessage + SendAsync 支援自訂 Header（如 Authorization）
7. #if DEBUG 區塊內若有多處 String StrLog = String.Format(...) 會觸發 CS0136，改用 inline LogFile.Write("...")

### Cascade 替換 using 補齊教訓
- MainWindowState 定義在 VPOS_Avalonia.ViewModels namespace
- 若替換引用到 MainWindowState.Instance.xxx，必須確認檔案有 using VPOS_Avalonia.ViewModels;
- 沒有 using 會 CS0103「名稱不存在於目前的內容中」
- 補 using 的範例：在 using VPOS; 之後加入 using VPOS_Avalonia.ViewModels;

### 2026-08-20 新增教訓 — TASK-014-A5f/A5g/A6 經驗萃取

#### 教訓 1: 代理屬性命名慣例（全大寫縮寫不拆）
- `m_UBER_EATS_params` → `mUBER_EATS_params`（保留 m 前綴，UBER_EATS/FOODPANDA/VTSTORE 等全大寫縮寫不拆）
- `m_FOODPANDA_params` → `mFOODPANDA_params`
- `m_NIDIN_POS_params` → `mNIDIN_POS_params`
- `m_YORES_POS_params` → `mYORES_POS_params`
- **規則**：m_XXX → mXxx（駝色，保留 m_ 前綴）。全大寫縮寫視為單一單字不拆。

#### 教訓 2: 內部直接屬性引用陷阱
MainWindow.axaml.cs 中的方法內部使用 `m_xxx = value`（直接存取），而非 `MainWindow.m_xxx`。刪除存根前必須先替換。
**排查三種模式**：
```bash
grep -rn 'MainWindow\\.m_xxx' VPOS_Avalonia/ --include='*.cs'    # 外部引用
grep -n '\\bm_xxx\\s*=' VPOS_Avalonia/Views/MainWindow.axaml.cs   # 內部直接賦值
grep -n '\\bm_xxx\\.\\|\\bm_xxx\\s*==' VPOS_Avalonia/Views/MainWindow.axaml.cs  # 內部直接讀取
```

#### 教訓 3: 存根刪除順序（鐵律）
1. 外部 cascade 替換
2. MainWindow.axaml.cs 內部所有引用替換
3. 獨立 grep 驗證
4. 刪除存根
5. 最終驗證

#### 教訓 4: 子代理 DoD 計數不可靠
子代理回報的計數可能不準確。**必須獨立執行 grep 驗證**，不依賴子代理的回報數字。

#### 教訓 5: Cascade 替換全目錄掃描
派單時必附「請先 grep 全 Views 目錄取得完整清單，對所有檔案執行替換，最後再 grep 確認殘留為 0」。

#### 教訓 6: Proxy stub 刪除陷阱（TASK-014-A7 教訓）
- **每次只刪一個 stub**（從 `public static T m_xxx` 到 `}`），不可批量刪除
- `patch` fuzzy matching 在大量空白 stub 上會失敗或誤刪相鄰 stub
- 刪除後立即 `grep` 驗證：若有 orphan get/set body 殘留（CS1519 編譯錯誤），立即 patch 清除
- 若 patch 連續 2 次失敗 → 改用 `replace_all=True` 刪除宣告行

### 子代理卡死處理
- 若 delegate_task 超過 10 分鐘無新進度（log 最後時間停滯），vpos_lead 會直接介入
- 機械式替換（≤6 處 replace）適合 vpos_lead 用 patch 直接處理

### 編譯環境
- /home/vblinux 無 .NET SDK，無法編譯
- 驗證方式：grep count + ls -la 實體寫入確認

### 交付驗證
- grep 舊模式 → 0 matches (exit code 1)
- grep 新模式 → 符合預期數量 matches
- ls -la 確認檔案修改時間
- 更新 docs/task_board.json 狀態為 REVIEW

### 2026-09-18 新增教訓 — TASK-028 空 Data Source cryptic error（已編譯驗收通過）

#### 根因（一次修好，保護整類 bug）
`SQLDataTableModel.ConnectionStringLoad(string id)` 只處理 Default/Synchronize/Takeaways 三個 switch case。傳入非此三者的 DB 名且 `blnAppSet=true` 時回傳**空字串** → SQLiteConnection.Open() 在深處拋 cryptic：「Data Source cannot be empty. Use :memory:...」，完全無法指出哪個 Database / 哪個呼叫點出問題。編譯能過但執行噴錯（DBWriter 每 ~10ms 一次）。

#### 修復（OpenConn 防禦強化）
`OpenConn(string Database, bool blnAppSet=true)` 開連線前加：
```csharp
string cnstr = (blnAppSet)? ConnectionStringLoad(Database) : string.Format("Data Source={0};", Database);
if (string.IsNullOrEmpty(cnstr)) throw new ArgumentException("VPOS: OpenConn failed - empty connection string for Database='" + Database + "'. Invalid DB name or missing case in ConnectionStringLoad.");
```
正常連線字串（含完整路徑）不受影響。日後打錯 DB 名會立刻看到明確錯誤而非 cryptic。

#### 全專案分類（live/latent/safe，TASK-028-M12 稽核報告）
- 🔴 LIVE：DBWriter.cs:92 `OpenConn("", true)` → M10 改調無參數 `OpenConn()`
- 🟡 LATENT 最隱蔽地雷：`SyncDBData.cs:1074 DBColumnsPadding(table_name,...)` 用資料表名當 Database，日後新增欄位卻沒同步建表 template 會撞上與 LIVE 一模一樣錯誤（已防禦）
- 🟢 SAFE：OpenConn() 無參數版、GetSharedConnection()、CreateSQLiteDatabase

#### 派單/開發注意
- 新增 DB 名稱時務必在 ConnectionStringLoad switch 補對應 case，否則任何用該名開連線的地方都會崩。
- 本類 audit 技能已建：`sqlite-connection-string-audit`（與 concurrency-audit 同為 DB 層 audit skill）。


§
記憶主動管理原則：有新偏好/修正/環境事實即存；見零散重複 entry 或 >70% 時趁手斂為少數高訊號 entry，勿等滿載或等使用者提。能成技能(skill)或工具(terminal/script)者一律移出記憶，記憶只留不可程序化的領域知識與教訓。
