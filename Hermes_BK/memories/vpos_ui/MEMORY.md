## vpos_ui 專屬記憶 — 資深 Avalonia / UI 工程師

### 工作範圍
- 僅限修改：VPOS_Avalonia/Views/, VPOS_Avalonia/ViewModels/, VPOS_Avalonia/UserControl/, VPOS_Avalonia/Assets/
- 禁止修改：DBLib/, WebAPI/, WinAPI/, ToolLib/, Thread/, Models/, Json2Class/（這些是 vpos_core 的範圍）

### 開發約束條款
1. 嚴禁在 Code-Behind (.axaml.cs) 中編寫商業邏輯，UI 邏輯必須透過 CommunityToolkit.Mvvm 綁定至 ViewModel
2. 所有非同步/背景作業必須注意 UI 執行緒切換（Dispatcher.UIThread.InvokeAsync）
3. MainWindowState 定義在 VPOS_Avalonia.ViewModels namespace
4. 若檔案需要引用 MainWindowState，必須有 using VPOS_Avalonia.ViewModels;
5. 沒有 using 會 CS0103「名稱不存在於目前的內容中」
6. 補 using 的範例：在 using VPOS; 之後加入 using VPOS_Avalonia.ViewModels;

### MainWindow.axaml.cs 重構教訓
- 大量 public static 成員已遷移至 MainWindowState.cs singleton
- 引用模式：MainWindow.m_xxx → MainWindowState.Instance.mXxx
- 命名慣例：m_XXX → mXxx（保留 m 前綴，後接 camelCase）
- 例如：m_StrVersion → mStrVersion, m_intOrderTypeIdSelected → mIntOrderTypeIdSelected

### 2026-08-20 新增教訓 — TASK-014-A5f/A5g 經驗萃取

#### 教訓 1: 全大寫縮寫命名不拆
- `m_UBER_EATS_params` → `mUBER_EATS_params`（UBER_EATS 視為單一單字）
- `m_FOODPANDA_params` → `mFOODPANDA_params`
- `m_VTSTORE_params` → `mVTSTORE_params`
- **規則**：m_XXX → mXxx，全大寫縮寫（UBER_EATS、FOODPANDA、VTSTORE、NIDIN_POS、YORES_POS）視為單一單字不拆。

#### 教訓 2: Cascade 替換全目錄掃描（最重要！）
- **不要只處理派單清單中的檔案**，子代理容易陷入「管窺效應」
- 完成前必須執行 `grep -r 'MainWindow\\.m_xxx' VPOS_Avalonia/Views/ | wc -l` 確認全目錄已無殘留
- 若 grep 結果顯示 >10 個檔案，全部都要處理
- **Definition of Done 必須包含：全目錄 grep 殘留為 0**

#### 教訓 3: 存根刪除順序（鐵律）
1. 外部 cascade 替換（所有 Views/ 檔案）
2. MainWindow.axaml.cs 內部所有引用替換（含直接存取 `m_xxx =`、`m_xxx.`、`m_xxx ==`）
3. 獨立 grep 驗證
4. 刪除存根
5. 最終驗證 — `grep 'public static.*m_xxx'` 應為 0

#### 教訓 4: 內部直接屬性引用陷阱
MainWindow.axaml.cs 中的方法內部使用 `m_xxx = value`（直接存取）。刪除存根前必須先替換為 `MainWindowState.Instance.mXxx`。
```bash
grep -n '\\bm_xxx\\s*=' VPOS_Avalonia/Views/MainWindow.axaml.cs    # 直接賦值
grep -n '\\bm_xxx\\.\\|\\bm_xxx\\s*==' VPOS_Avalonia/Views/MainWindow.axaml.cs  # 直接讀取
```

#### 教訓 5: 遺漏檔案是常見錯誤
- TASK-014-A2 遺漏了 9 個檔案（ClosingHandover、DiDiEats、Loading、Login、ModifyCart 等）
- **每次 cascade 替換，必須先 grep 全目錄取得完整清單，再逐檔案處理**

#### 教訓 6: Proxy stub 刪除陷阱（TASK-014-A7 教訓）
- **每次只刪一個 stub**（從 `public static T m_xxx` 到 `}`），不可批量刪除
- `patch` fuzzy matching 在大量空白 stub 上會失敗或誤刪相鄰 stub
- 刪除後立即 `grep` 驗證：若有 orphan get/set body 殘留（CS1519 編譯錯誤），立即 patch 清除
- 若 patch 連續 2 次失敗 → 改用 `replace_all=True` 刪除宣告行

### Cascade 替換 using 補齊教訓
- 替換引用到 MainWindowState 後，必須檢查檔案是否有 using VPOS_Avalonia.ViewModels;
- 若沒有，先 patch 加入 using，再做 replace
- 完成後驗證所有檔案都有此 using

### 編譯環境
- /home/vblinux 無 .NET SDK，無法編譯
- 驗證方式：grep count + ls -la 實體寫入確認

### 交付驗證
- grep 舊模式 → 0 matches (exit code 1)
- grep 新模式 → 符合預期數量 matches
- ls -la 確認檔案修改時間
- 更新 docs/task_board.json 狀態為 REVIEW

§
記憶主動管理原則：有新偏好/修正/環境事實即存；見零散重複 entry 或 >70% 時趁手斂為少數高訊號 entry，勿等滿載或等使用者提。能成技能(skill)或工具(terminal/script)者一律移出記憶，記憶只留不可程序化的領域知識與教訓。
