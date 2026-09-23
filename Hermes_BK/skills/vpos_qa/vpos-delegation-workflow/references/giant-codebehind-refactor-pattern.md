# Giant Code-Behind Refactor Pattern (MainWindow.axaml.cs 重構模式)

## 適用場景
單一 .axaml.cs 檔案超過 10,000 行，包含大量 `public static` 成員（變數 + 方法），違反 MVVM 原則。

## 實例：TASK-013 (2026-08-10)
- **檔案**: VPOS_Avalonia/Views/MainWindow.axaml.cs — 12,368 行 (~750KB)
- **成員數**: 54 個 public static（47 變數 + 7 方法）
- **拆解策略**: Micro-Tasks (TASK-013a ~ TASK-013d)，每次只處理一個關注點

## 微步拆分模板

| Micro-Task | 關注點 | 難度 |
|------------|--------|------|
| a | 清理無用 using / dead code | ⭐ |
| b | 建立 Singleton ViewModel 集中管理 public static 成員 | ⭐⭐⭐ |
| c | 提取 DllImport / WinAPI 至獨立 ToolLib | ⭐⭐ |
| d | 將 UI 初始化方法移至 ViewModel | ⭐⭐⭐ |

## TASK-013b: MainWindowState Singleton 模式

### 目標類別結構 (VPOS_Avalonia/ViewModels/MainWindowState.cs)
```csharp
using CommunityToolkit.Mvvm.ComponentModel;

namespace VPOS_Avalonia.ViewModels
{
    public sealed class MainWindowState : ObservableObject
    {
        private static readonly Lazy<MainWindowState> _instance = new(() => new MainWindowState());
        public static MainWindowState Instance => _instance.Value;

        // 私有建構子 — singleton pattern
        private MainWindowState()
        {
            // DateTime 預設值在此設定 (DateTime.Now)
            m_ClassLastTime = DateTime.Now;
            m_DailyLastTime = DateTime.Now;
            // ... etc.
        }

        // 變數轉為 property — 使用 [ObservableProperty] 或普通 property
        private terminal_panel_styles _mTerminalPanelStyles;
        public terminal_panel_styles m_terminal_panel_styles
        {
            get => _mTerminalPanelStyles;
            set => SetProperty(ref _mTerminalPanelStyles, value);
        }

        // 或使用 CommunityToolkit.Mvvm 簡寫:
        [ObservableProperty]
        private int _mIntOrderTypeIdSelected = 0;
    }
}
```

### MainWindow.axaml.cs 修改方式
將所有 `public static` 宣告改為 expression-bodied property 回傳 Instance：
```csharp
// Before (分散在各處):
public static terminal_panel_styles m_terminal_panel_styles = null;
public static int m_intOrderTypeIdSelected = 0;

// After (集中在類別開頭，指向 Instance):
public static terminal_panel_styles m_terminal_panel_styles => MainWindowState.Instance.m_terminal_panel_styles;
public static int m_intOrderTypeIdSelected => MainWindowState.Instance.m_intOrderTypeIdSelected;
```

### 方法搬移方式
```csharp
// Before:
public static String PosOrderNumberCreate(String StrGUID) { ... }

// After:
public static String PosOrderNumberCreate(String StrGUID) => MainWindowState.Instance.PosOrderNumberCreate(StrGUID);
```

## 交付前強制驗證 (Definition of Done)
1. `grep "public static" <file>.axaml.cs | wc -l` → 應從 ~50+ 降到只剩 extern DllImport + 保留的 helper methods
2. `ls -la VPOS_Avalonia/ViewModels/<StateClass>.cs` → 確認檔案存在且有內容
3. `grep "<StateClass>.Instance" <file>.axaml.cs | wc -l` → 應 > 40 (所有變數都改用 Instance)

## 注意事項
- DateTime.Now 預設值需在 Singleton 建構子中設定（不能在 property 宣告時用 DateTime.Now）
- FileVersionInfo.GetVersionInfo() 等需要 Assembly 的初始值也需在建構子中計算
- 保留原有的行尾註解 (comments)
- 不改變任何商業邏輯，只是搬移位置

## TASK-013b 實戰教訓 (2026-08-10)

### 屬性名稱必須作為 source of truth
**問題**: vpos_core 產出的 MainWindowState.cs 有實際的屬性名稱（如 `mTerminalPanelStyles`），但 MainWindow.axaml.cs 中的 forwarding property 引用了錯誤的名稱（如 `Instance.mterminalpanelstyles`）。直接 patch MainWindow.axaml.cs 會因為找不到 match 而失敗。

**修復流程**:
1. **先讀取 MainWindowState.cs** — 用 `grep 'public.*\w\+\s\+\w\+' VPOS_Avalonia/ViewModels/MainWindowState.cs` 取得所有實際屬性名稱
2. **再 grep MainWindow.axaml.cs** — 找出所有 `MainWindowState.Instance.XXX` 引用，比對哪些是錯誤的
3. **建立 wrong→correct mapping table** — 用 Python regex 批量替換（而非 patch）

### 何時該用 execute_code vs delegate_task
- **delegate_task**: 需要理解商業邏輯、跨檔案關聯、設計決策（如 SQL 注入修復）
- **execute_code**: 機械式批量替換、grep/count/verify、regex 全文搜尋替換、屬性名稱映射

### 派單時必附提醒
"完成後請先 `read_file` MainWindowState.cs 確認實際屬性名稱，再修改 MainWindow.axaml.cs 的引用。"
