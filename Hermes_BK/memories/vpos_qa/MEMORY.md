## vpos_qa 專屬記憶 — 資深審查與測試/打包工程師

### 工作範圍
- 僅限修改：FlaUI_Test/, NSIS_Project/, review-reports/
- 禁止修改：VPOS_Avalonia/ 下的任何 .cs/.axaml 檔案（這些是開發者的範圍）
- 禁止修改：docs/task_board.json（Lead 的範圍）

### QA 審查流程
1. 讀取 task_board.json 確認任務描述與 Definition of Done
2. 讀取 review-reports/ 下的任務暫存檔（若有）
3. 執行 grep 驗證：
   - 舊模式引用是否為 0
   - 新模式引用是否符合預期
   - 存根宣告是否已刪除
4. 檢查結構完整性：
   - 檔案是否有 orphaned braces（孤立括號）
   - 是否有 orphaned identifiers（裸方法名）
   - 是否有 missing field declarations（遺漏欄位宣告）
5. 產出 review-reports/review-TASK-XXX-*.md 報告
6. 更新 task_board.json 的 qa_review 欄位

### QA 鐵律
1. QA 報告只能由 vpos_qa 修改，Lead/開發者不可碰
2. 球員兼裁判是嚴重違規
3. 若任務失敗（CS0103/CS0122 等編譯錯誤），標記 REJECTED 並寫入具體錯誤行號
4. 若任務通過，標記 PASS 並寫入 qa_review_file 路徑

### 常見審查陷阱
- CS0103: 名稱不存在 → 檢查 using 是否已補上
- CS0122: 保護層級 → 檢查 private 是否改為 internal
- CS0136: 重複宣告 → 檢查 #if DEBUG 區塊
- Orphaned braces: 提取方法後留下孤立括號
- Missing field: 遷移方法但遺漏欄位宣告

### 2026-08-20 新增教訓 — TASK-014-A5f/A5g 經驗萃取

#### 教訓 1: 內部直接屬性引用審查（CRITICAL）
審查 proxy property 刪除任務時，必須檢查 **三種引用模式**：
```bash
grep -rn 'MainWindow\\.m_xxx' VPOS_Avalonia/ --include='*.cs'    # 外部引用
grep -n '\\bm_xxx\\s*=' VPOS_Avalonia/Views/MainWindow.axaml.cs   # 內部直接賦值
grep -n '\\bm_xxx\\.\\|\\bm_xxx\\s*==' VPOS_Avalonia/Views/MainWindow.axaml.cs  # 內部直接讀取
```
若發現內部直接引用未替換 → **REJECTED**，附具體行號。

#### 教訓 2: 命名慣例審查
- `m_UBER_EATS_params` → 必須是 `mUBER_EATS_params`（UBER_EATS 不拆）
- `m_FOODPANDA_params` → 必須是 `mFOODPANDA_params`
- `m_VTSTORE_params` → 必須是 `mVTSTORE_params`
- 全大寫縮寫視為單一單字，駝色轉換時不拆
- 若發現扁平連接（如 `uberEatsParams` 或 `uber_eats_params`）→ **REJECTED**

#### 教訓 3: 全目錄殘留審查
- 子代理完成 cascade 替換後，**必須獨立執行全目錄 grep**
- `grep -r 'MainWindow\\.m_xxx' VPOS_Avalonia/Views/ | wc -l` → 應為 0
- 若子代理只處理了派單清單中的檔案而遺漏其他 → **REJECTED**

#### 教訓 4: 存根刪除驗證
- `grep 'public static.*m_xxx' VPOS_Avalonia/Views/MainWindow.axaml.cs` → 應為 0（WinAPI 方法除外）
- WinAPI 方法（FindTrayButtonWindow, ShowTouchKeyboard, ShowSoftKeyboard, SoftKeyboard_OSK, CloseVTCD）應保留

#### 教訓 5: 子代理 DoD 計數不可靠
- 子代理回報的計數可能不準確（如 TASK-014-A5f 回報 9 處但實際 7 處）
- **QA 必須獨立 grep 驗證，不依賴子代理的回報數字**
- 若子代理計數與獨立驗證不一致 → 標記需要二次確認

#### 教訓 6: Orphan get/set body 審查陷阱（TASK-014-A7 教訓）
- 刪除 proxy stub 時，若 fuzzy matching 誤刪相鄰 stub 的宣告行，會留下 orphan get/set body
- 審查時必須檢查：`grep -n 'get => MainWindowState.Instance' VPOS_Avalonia/Views/MainWindow.axaml.cs`
- 若 get/set body 前沒有 `public static T m_xxx` 宣告行 → **REJECTED**（CS1519 編譯錯誤）
- 正確做法：每次只刪一個 stub，刪除後立即 grep 驗證

### 交付驗證
- review-reports/review-TASK-XXX-*.md 報告已產出
- task_board.json 已更新 qa_review 欄位

### 2026-09-18 新增教訓 — TASK-028 空 Data Source cryptic error（QA 審查重點）

#### 本類 audit 技能：`sqlite-connection-string-audit`
與 `concurrency-audit` 同為 DB 層 audit skill，已分發給 core + qa。審查此類任務時先載入該技能。

#### QA 審查重點（TASK-028-M12 同類清查）
1. **根因防禦是否一次保護整類**：OpenConn(Database,...) 加 `string.IsNullOrEmpty(cnstr)` 檢查，必須同時確認無參數版 OpenConn() 未改、原三處呼叫點 (L145/L268/L430) 仍在。
2. **live/latent/safe 三分類是否完整**：不能只修已爆的 LIVE（DBWriter），要標出 LATENT 最隱蔽地雷（SyncDBData DBColumnsPadding 用資料表名當 Database）並確認已防禦。
3. **DoD grep 驗證**：`IsNullOrEmpty(cnstr)` ≥1、明確錯誤訊息含 Database 名、OpenConn() 無參數版簽名行號不變、三處 OpenConn(Database,blnAppSet) 仍在。
4. cryptic error 的審查陷阱：錯誤訊息完全無法指出哪個 Database，QA 必須靠 grep `ConnectionStringLoad` / `OpenConn(Database` 反推呼叫點，不能只看 log。


§
記憶主動管理原則：有新偏好/修正/環境事實即存；見零散重複 entry 或 >70% 時趁手斂為少數高訊號 entry，勿等滿載或等使用者提。能成技能(skill)或工具(terminal/script)者一律移出記憶，記憶只留不可程序化的領域知識與教訓。
