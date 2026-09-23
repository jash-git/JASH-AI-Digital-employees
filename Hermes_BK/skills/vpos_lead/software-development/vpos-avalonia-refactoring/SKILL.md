---
name: vpos-avalonia-refactoring
description: Extract UI initialization methods from MainWindow.axaml.cs into MainWindowState.cs singleton, then delegate via MainWindowState.Instance.MethodName(this).
---

# VPOS Avalonia Refactoring Patterns

Procedures for refactoring the VPOS Avalonia codebase, especially moving UI initialization from MainWindow.axaml.cs into MainWindowState.cs.

## When to Use

- MainWindow.axaml.cs grows beyond ~10,000 lines and becomes hard to navigate
- Need to extract UI setup/initialization methods that access controls but don't depend on complex event logic
- Want to centralize state while keeping UI manipulation in a dedicated location

## Core Pattern: Extract → Delegate

### Step 1: Identify Methods to Move

Look for `private void` / `public void` methods in MainWindow.axaml.cs that:
- Start with "Init", "Create", "Show", "Set" (UI initialization verbs)
- Access UI controls directly but don't have complex async/event logic
- Are called from `Window_Loaded` or constructor

Use grep to find candidates:
```bash
grep -n "private void\|public void" VPOS_Avalonia/Views/MainWindow.axaml.cs | wc -l
```

### Step 2: Add Using Statements to MainWindowState.cs

Before moving methods, ensure MainWindowState.cs has these imports at the top:
```csharp
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.Primitives;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Threading;
using Avalonia.VisualTree;
using VPOS_Avalonia.Views;  // For MainWindow type reference
```

### Step 3: Convert Methods to Take `MainWindow mw` Parameter

Original (implicit this):
```csharp
private void SetFontSize()
{
    Status00TextLabel.FontSize = ...;  // accesses implicit this
}
```

Converted (explicit parameter):
```csharp
public void SetFontSize(MainWindow mw)
{
    mw.Status00TextLabel.Fontise = ...;  // explicit reference
}
```

**Key rule:** Every UI control access must be prefixed with `mw.` instead of implicit `this`.

### Step 4: Append to MainWindowState.cs

Add methods inside a new region:
```csharp
#region UI Initialization Methods (moved from MainWindow.axaml.cs)
// ... moved methods here ...
#endregion
```

### Step 5: Replace Original Bodies with Delegation Calls

In MainWindow.axaml.cs, replace each method body with:
```csharp
private void SetFontSize()//字型大小依照解析度調整
{
    MainWindowState.Instance.SetFontSize(this);
}
```

Keep the original signature and comments — this preserves the public API surface.

### Step 6: Add Missing Fields/Helpers to MainWindowState.cs

If moved code references fields that don't exist in MainWindowState yet, add them:
- `m_strShopcartBtnName` — button name arrays
- `mBlnScrollTo` — scroll flags  
- `mIntOrderState` — order state tracking
- Helper methods like `DiDiMoneyInfoGridSet(MainWindow)`, `GetShopCartVarIndex(...)`

## Verification Checklist (MANDATORY before finishing)

Run these three commands to confirm the refactor succeeded:

1. **File size increased** — confirms methods were appended:
   ```bash
   ls -la VPOS_Avalonia/ViewModels/MainWindowState.cs
   ```
   File should be significantly larger than baseline (~27KB → ~84KB for 15+ methods).

2. **Method count decreased in MainWindow.axaml.cs**:
   ```bash
   grep "private void\|public void" VPOS_Avalonia/Views/MainWindow.axaml.cs | wc -l
   ```
   Count should be lower than before extraction.

3. **Delegation calls present**:
   ```bash
   grep "MainWindowState\.Instance\.\(SetFontSize\|ShowInfoInit\|ShopcartBtnGridInit\)" VPOS_Avalonia/Views/MainWindow.axaml.cs | wc -l
   ```
   Should return > 0 — confirms delegation pattern is in place.

## Pitfalls

### CS0103: Constructor Naming Mismatch (CRITICAL)
When extracting fields from MainWindow.axaml.cs into MainWindowState.cs, the **constructor initialization** must use the same naming convention as the field declarations. A common error is constructor using old underscore naming (`m_ClassLastTime`) while field declarations use PascalCase (`mClassLastTime`).

**Before fix:**
```csharp
private MainWindowState()
{
    m_ClassLastTime = DateTime.Now;  // ❌ underscore between m and capital letter
}
public DateTime mClassLastTime;   // ✅ PascalCase — mismatch!
```

**After fix:**
```csharp
private MainWindowState()
{
    mClassLastTime = DateTime.Now;  // ✅ matches field declaration
}
public DateTime mClassLastTime;
```

**Rule:** Constructor must use the EXACT same identifier as the field. Check lines 39-63 of MainWindowState.cs after any extraction. Also check for old naming in active code (not inside `/* */` comment blocks).

### CS0103: Event Handler Wrappers Missing
When MainWindowState.cs references event handlers defined in MainWindow.axaml.cs (e.g., `TaxIDBtn_Clicked`, `OrderBtn_Click`), add **static wrapper delegates** at the end of MainWindowState.cs that cast `sender` back to `MainWindow`:

```csharp
#region Event Handler Wrappers (delegate to MainWindow.axaml.cs)
public static void TaxIDBtn_Clicked(object sender, PointerPressedEventArgs e) 
    => ((MainWindow)sender).TaxIDBtn_Clicked(sender, e);
public static async void OrderBtn_Click(object sender, RoutedEventArgs e) 
    => await ((MainWindow)sender).OrderBtn_Click(sender, e);
// ... one per event handler referenced from MainWindowState.cs
#endregion
```

**When to add:** After every extraction that introduces references like `+= TaxIDBtn_Clicked` or method calls to handlers not yet in MainWindowState. Check by grepping for `_Clicked\|_Click(` in MainWindowState.cs and verifying each has a corresponding wrapper.

- **Event handler subscriptions**: Methods that subscribe to events (e.g., `btn.ExternalClicked += Handler`) need the event handler methods to also be moved or accessible from MainWindowState. If handlers reference MainWindow-specific state, they may need to stay behind or take `MainWindow` as parameter too.
  
- **Static vs instance access**: Some methods modify static fields on MainWindow (e.g., `m_OrderBtn`). These should use `mw.m_OrderBtn` in the moved code, and the field should exist on the MainWindow instance.

- **Nested method dependencies**: If Method A calls Method B internally, both need to be moved or A needs to call via `MainWindowState.Instance.MethodB(this)`.

- **Using statements**: Don't forget `using VPOS_Avalonia.Views;` in MainWindowState.cs — without it, the `MainWindow` type is unknown.

### Pitfall: Cross-file field ownership (NEW, added 2026-08-18)
When moving methods from MainWindow.axaml.cs to MainWindowState.cs, fields referenced in those methods may be declared in **either** file. The extraction may move the method but leave the field behind.

**Always verify every field used in moved methods:**
1. `search_files(pattern='<field_name>', path='MainWindowState.cs')` — is it used in target?
2. `search_files(pattern='private.*<field_name>|public.*<field_name>', path='MainWindowState.cs')` — is it declared in target?
3. `search_files(pattern='<field_name>', path='MainWindow.axaml.cs')` — is it declared in source?
4. If used in target but declared in source → either move the field to MainWindowState.cs, or change references to `mw.<field>` or `MainWindowState.Instance.<field>`

**Example**: `m_intTimerCount` was used in MainWindowState.cs MainTimmer_Tick but declared nowhere — caused CS0103. Must add `private int m_intTimerCount = 0;` to MainWindowState.cs.

**Example**: `m_strClosingHandoverCheckMsg` was declared in MainWindow.axaml.cs but used in MainWindowState.cs — needs accessor pattern or field migration.

## Support Files
- `references/method-extraction-brace-counting-fix.md` — 方法提取時 { } 計數失準的修復模式與檢查清單

### 陷阱: 代理屬性清理 — 區分 proxy 屬性 vs WinAPI 方法 (TASK-014)
**問題**: MainWindow.axaml.cs 有 ~36 個 `public static T xxx { get => MainWindowState.Instance.xxx; set => ... }` 代理屬性，但還有 ~14 個靜態方法（已遷移至 MainWindowState.cs）和 ~4 個 WinAPI 方法（必須保留）。盲目刪除會破壞外部呼叫。

**分類規則**：
- **代理屬性** (可刪除): getter/setter 都指向 `MainWindowState.Instance.xxx`
- **已遷移方法** (檢查後決定): 已搬至 MainWindowState.cs，可刪除或保留 forwarding stub
- **WinAPI 方法** (保留): FindTrayButtonWindow, ShowTouchKeyboard, ShowSoftKeyboard, SoftKeyboard_OSK — 外部可能透過 `MainWindow.MethodName()` 呼叫

**⚠️ 2026-08-20 新增陷阱 — 內部直接屬性引用**：
代理屬性存根被刪除前，**必須先替換所有內部直接屬性引用**。這些引用在 MainWindow.axaml.cs 的方法內部使用 `m_xxx = value` 格式（直接存取，非 `MainWindow.m_xxx`）。

**排查三種引用模式**：
```bash
# 外部檔案引用
grep -rn 'MainWindow\\.m_xxx' VPOS_Avalonia/ --include='*.cs'

# MainWindow.axaml.cs 內部直接賦值
grep -n '\\bm_xxx\\s*=' VPOS_Avalonia/Views/MainWindow.axaml.cs

# MainWindow.axaml.cs 內部直接讀取
grep -n '\\bm_xxx\\.\\|\\bm_xxx\\s*==' VPOS_Avalonia/Views/MainWindow.axaml.cs
```

**修復順序（鐵律）**：
1. 外部 cascade 替換
2. MainWindow.axaml.cs 內部所有引用替換（含直接存取）
3. 獨立 grep 驗證
4. 刪除存根
5. 最終驗證

**詳細流程**: `references/proxy-property-cleanup-pattern.md`

### 陷阱: 方法提取時 { } 計數失準 → 孤立括號包裹方法定義 (TASK-024a)
**問題**: 用 Python regex 提取方法時，用 `{` `}` 計數來定位方法範圍會出錯：
- 方法簽章行本身有 `{`（如 `public void Method() {`）
- 方法內部有巢狀 `{` `}`（如 if/for/while 區塊）
- 這會導致提取不完整，留下孤立的 `{` 和 `}` 包裹方法定義

**後果**: 連鎖編譯錯誤 — CS0106（修飾元無效）、CS1022（必須是類型定義）、CS1513（必須是 }）、CS8803（最上層陳述式錯誤）

**修復方式**:
1. **提取後必須驗證結構** — 檢查方法定義前面是否有孤立的 `{` 或 `}`
2. **批量移除多餘括號的模式**:
   ```python
   for i in range(1, len(lines) - 1):
       if lines[i-1].strip() == '}' and lines[i].strip() == '{':
           if re.match(r'(public|private|internal)\s+(async\s+)?void\s+\w+\(', lines[i+1]):
               del lines[i]
               del lines[i-1]
   ```
3. **同時移除孤立文字**（如孤立的 `Window_Loaded` 單行）
4. **修正內部裸方法呼叫**（如 `syncthreadCreate();` → `syncthreadCreate(this);`）