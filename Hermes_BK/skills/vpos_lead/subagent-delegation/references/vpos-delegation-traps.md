# VPOS Delegation Traps & Corrections

Condensed lessons from TASK-014 series (2026-08-21).

## Trap: vpos_lead 不可因子代理遺漏引用就自己 patch 修正

**Problem**: 獨立驗證發現子代理遺漏 4 處內部直接引用時，vpos_lead 沒有退回子代理重修，而是自己用 `patch` 直接修正。違反了 Trap26 (Lead 不可自己動手改 code)。

**Correct flow**:
1. 獨立驗證發現問題 → 標記 QA REJECTED
2. 退回開發者 (vpos_core/vpos_ui) 重修
3. 開發者完成後 → 重新指派 QA 複查
4. QA PASS → 標記 DONE

**Exception**: 只有機械式、無商業邏輯判斷的操作才可以由 vpos_lead 直接 patch（例如：單一 using 補齊、>3 處相同 rename、新增單一欄位）。但「修正引用前綴」涉及商業邏輯判斷（Instance vs static），不屬於機械式操作。

## Trap: 完全忘記建立 Cron 監控

**Problem**: vpos_lead 在派發 delegate_task 後，完全沒有建立 Cron watchdog。QA 子代理跑了 29 分鐘都沒有任何監控回報。

**Fix**:
1. 每次 `delegate_task` 完成後，立即執行 `cronjob(action='create')`
2. 不可因為「系統會自動通知」就跳過 Cron
3. 每輪開頭必須檢查 `cronjob(action='list')` 確認所有進行中任務都有對應 Cron

## Trap: 子代理 DoD 計數不可靠 — 必須獨立 grep 驗證

**Problem**: vpos_core 回報的計數與實際不符。

**Fix**: vpos_lead 必須獨立執行 grep 驗證，不依賴子代理的回報數字。

## Trap: 內部直接屬性引用（非 MainWindow.m_xxx 格式）— proxy 刪除陷阱

**Problem**: MainWindow.axaml.cs 中的方法內部使用直接屬性存取（如 `m_xxx = value`），而非 `MainWindow.m_xxx`。當刪除 proxy property 存根時，這些內部直接引用會斷裂。

**Fix**: 分析 proxy property 時，必須同時 grep 兩種模式：
- `grep -rn 'MainWindow\\.m_xxx' VPOS_Avalonia/` — 外部檔案引用
- `grep -n '\\bm_xxx\\s*=' VPOS_Avalonia/Views/MainWindow.axaml.cs` — 內部直接賦值
- `grep -n '\\bm_xxx\\.\\|\\bm_xxx\\s*==' VPOS_Avalonia/Views/MainWindow.axaml.cs` — 內部直接讀取

全部替換為 `MainWindowState.Instance.mXxx`，最後才刪除存根。

## Trap: Cascade 替換後必須刪除代理屬性存根

**Problem**: 即使所有引用都已替換，若未刪除存根會導致編譯警告和違反 MVVM 解耦目標。

**Fix**: 完成所有引用替換後，必須刪除 MainWindow.axaml.cs 中的代理屬性存根宣告。

## Trap: Cascade 類型替換可能需新增 using 宣告

**Problem**: 將 `MainWindow.m_dblZoom` 替換為 `MainWindowState.Instance.mDblZoom` 後，部分檔案編譯錯誤 CS0103（MainWindowState 未定義）。

**Fix**: 替換前檢查所有受影響檔案是否有 `using VPOS_Avalonia.ViewModels;`。若沒有，必須先 patch 加入 using，再做 replace。
