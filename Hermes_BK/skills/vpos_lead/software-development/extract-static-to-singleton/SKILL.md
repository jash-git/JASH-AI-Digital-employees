---
name: extract-static-to-singleton
description: "Extract public static members from large code-behind files (Avalonia/WPF) into a centralized singleton state class, enabling MVVM-friendly access and sibling-subagent-safe property forwarding."
version: 1.0.0
author: Hermes Agent
tags: [refactor, avalonia, wpf, mvvm, static-members, singleton, code-behind]
---

# Extract Static Members to Singleton State Class

Extract all `public static` fields and methods from a large code-behind file (typically `.axaml.cs` or `.xaml.cs`) into a dedicated singleton state class. This enables MVVM-friendly access patterns and avoids sibling-subagent naming conflicts.

## When to Use

- Code-behind has 30+ public static members scattered across the file
- Multiple subagents need to modify different parts of the same code-behind simultaneously
- The project follows MVVM but UI-layer static fields are hard to test or access from ViewModels
- User says "extract statics", "centralize state", "move static members", "create a state class"

## Steps

### 1. Discover all public static members

```bash
grep -n '^\s*public static ' path/to/CodeBehind.cs | head -80
```

Read the full file to capture method bodies (not just signatures). Note:
- Distinguish `public static` fields from `public static extern` P/Invoke declarations (keep externs in place)
- Note XML comments and inline comments on each member
- Record the exact type names for every field

### 2. Create the singleton state class

Create at `ViewModels/<OriginalName>State.cs`:

```csharp
namespace Project.ViewModels
{
    public sealed class OriginalNameState
    {
        private static readonly OriginalNameState _instance = new();
        public static OriginalNameState Instance => _instance;
        private OriginalNameState() { /* DateTime defaults, runtime-computed values */ }

        // Fields → properties (camelCase: m_XXX → xxx)
        public int someField = defaultValue;
        public String someString = "";

        // Methods → instance methods with same body
        public void SomeMethod(String param) { /* exact original body */ }
    }
}
```

**VPOS 專案命名慣例**: `m_XXX` → `mXxx`（保留 m 前綴，後接 camelCase）。例如：
- `m_StrVersion` → `mStrVersion` ✅（非 `StrVersion`）
- `m_ShopCart` → `mShopCart` ✅（非 `ShopCart`）
- `m_intOrderTypeIdSelected` → `mIntOrderTypeIdSelected` ✅

**其他專案慣例**: 若專案無此慣例，則直接去 m_：`m_StrVersion` → `StrVersion`。派單時請確認目標專案的命名風格。

**DateTime defaults:** Initialize in the private constructor with `DateTime.Now`.

**Runtime-computed values:** Compute `FileVersionInfo.GetVersionInfo(...)` and similar one-time values in the constructor, wrapped in try/catch.

### 3. Forward from code-behind — PROPERTY ACCESSORS (NOT expression-bodied)

For each public static field in the original file, replace with a **full property** that forwards to Instance:

```csharp
// BEFORE (original):
public static int m_intOrderTypeIdSelected = 0;

// AFTER (forwarding property):
public static int m_intOrderTypeIdSelected
{
    get => OriginalNameState.Instance.StrOrderTypeNameSelected;
    set => OriginalNameState.Instance.StrOrderTypeNameSelected = value;
}
```

**CRITICAL:** Use full `{ get; set; }` properties, NOT expression-bodied (`=>`). Expression-bodied properties cause issues when sibling subagents modify the file because:
- The type name in `public static TYPE NAME` must match exactly (e.g., `terminal_panel_styles`, not `m_terminal_panel_styles`)
- Full property blocks are easier to patch with fuzzy matching

### 4. Forward methods — keep as static method wrappers

For public static methods, replace the body with a call through Instance:

```csharp
// BEFORE:
public static void SomeMethod(String param) { /* long body */ }

// AFTER (wrapper):
public static void SomeMethod(String param) => OriginalNameState.Instance.SomeMethod(param);
```

**Exception:** If the method references other public static members that are also forwarded, keep the original body and let it resolve through the forwarding properties. This avoids breaking cross-references.

### 5. Verify consistency

After writing both files:
1. `grep -oP "OriginalNameState\.Instance\.\K[a-zA-Z]+" file.cs | sort -u` — list all accessor names used in code-behind
2. Compare against the property/method names declared in the state class
3. Fix any mismatches (common error: sibling subagent uses wrong type names like `m_terminal_panel_styles` instead of `terminal_panel_styles`)

## Phase 2: Proxy Property Removal & Reference Migration

After the extraction (Phase 1) is complete and all references have been updated to `Instance.Xxx`, the forwarding proxy properties in the code-behind become dead code. This phase removes them.

### Step 1: Identify proxy properties to remove

A proxy property is one where **both** getter and setter forward to the singleton:
```csharp
public static T m_xxx
{
    get => OriginalNameState.Instance.mXxx;
    set => OriginalNameState.Instance.mXxx = value;
}
```

**What to keep** (do NOT remove):
- WinAPI / P/Invoke wrappers (e.g., `FindTrayButtonWindow`, `ShowTouchKeyboard`, `ShowSoftKeyboard`, `SoftKeyboard_OSK`, `CloseVTCD`) — external callers may depend on them
- Methods that have actual logic (not just forwarding)

### Step 2: Update ALL references BEFORE removing proxies

**CRITICAL ORDER**: Update references first, then remove proxies. If you remove proxies before updating references, the code breaks mid-refactor.

**Reference update rules**:
| Location | Pattern | Example |
|----------|---------|---------|
| **External files** (Views/, WebAPI/, etc.) | `MainWindow.m_xxx` → `MainWindowState.Instance.mXxx` | `MainWindow.m_terminal_panel_styles` → `MainWindowState.Instance.mTerminalPanelStyles` |
| **MainWindow.axaml.cs internal methods** | `m_xxx =` / `m_xxx.` / `m_xxx ==` → `MainWindowState.Instance.mXxx` | `m_StrPosExpenseNumber = ""` → `MainWindowState.Instance.mStrPosExpenseNumber = ""` |
| **MainWindowState.cs internal** | `MainWindow.m_xxx` → `mXxx` (bare field, no Instance) | `MainWindow.m_terminal_panel_styles` → `mTerminalPanelStyles` |
| **Commented-out code** | No change needed | `// MainWindow.m_xxx` stays as-is |

**⚠️ 2026-08-20 新增 — 內部直接屬性引用陷阱**:
MainWindow.axaml.cs 中的方法內部（如 takeaways_params2Var()）可能使用直接屬性存取 `m_xxx = value`，而非 `MainWindow.m_xxx`。這些是「同一類別的 static member」，所以方法內直接寫 `m_xxx = value` 即可。但一旦刪除存根，這些引用就斷裂了。

**必須 grep 三種模式**：
```bash
# 外部檔案引用
grep -rn 'MainWindow\\.m_xxx' VPOS_Avalonia/ --include='*.cs'

# 內部直接賦值
grep -n '\\bm_xxx\\s*=' VPOS_Avalonia/Views/MainWindow.axaml.cs

# 內部直接讀取
grep -n '\\bm_xxx\\.\\|\\bm_xxx\\s*==' VPOS_Avalonia/Views/MainWindow.axaml.cs
```

**修復順序（鐵律）**：
1. 外部檔案 cascade 替換
2. MainWindow.axaml.cs 內部所有引用替換（含直接存取）
3. 獨立 grep 驗證
4. 刪除存根
5. 最終驗證

### Step 3: Remove proxy properties

Delete the entire property block (including `{ get; set; }`). Use `patch` with the full block as old_string, empty string as new_string.

### Step 4: Verify

1. `grep 'public static' MainWindow.axaml.cs` → should only show WinAPI methods + keyboard methods (~5 total)
2. `grep -r 'MainWindow\.m_xxx' VPOS_Avalonia/` → only commented-out lines should remain
3. `ls -la` → confirm file modification timestamps

### Pitfalls for Phase 2

- **內部直接屬性引用（CRITICAL, 2026-08-20 新增）**：MainWindow.axaml.cs 內部方法使用 `m_xxx = value`（直接存取），而非 `MainWindow.m_xxx`。這些引用在刪除存根後會斷裂。必須先替換為 `MainWindowState.Instance.mXxx` 再刪除存根。

  **排查方法**：
  ```bash
  # 三種模式都要 grep
  grep -n '\\bm_xxx\\s*=' VPOS_Avalonia/Views/MainWindow.axaml.cs    # 直接賦值
  grep -n '\\bm_xxx\\.\\|\\bm_xxx\\s*==' VPOS_Avalonia/Views/MainWindow.axaml.cs  # 直接讀取
  grep -n 'MainWindow\\.m_xxx' VPOS_Avalonia/Views/MainWindow.axaml.cs  # 間接引用
  ```

- **子代理 DoD 計數不可靠（CRITICAL, 2026-08-20 新增）**：子代理回報的計數可能不準確。vpos_lead 必須獨立執行 grep 驗證，不依賴子代理的回報數字。

- **Sibling subagent race**: If multiple subagents work on the same file simultaneously, use `write_file` instead of `patch` for the final cleanup.
- **Don't remove WinAPI methods**: Methods like `ShowTouchKeyboard`, `ShowSoftKeyboard`, `SoftKeyboard_OSK`, `CloseVTCD`, `FindTrayButtonWindow` are external-facing. Verify against the task_board.json Definition of Done.

## Pitfalls

- **Type name mismatch:** The type before the field name must be the ORIGINAL type, not prefixed with `m_`. Common error: `public static m_StrVersion m_StrVersion` instead of `public static String m_StrVersion`.
- **Accessor reference mismatch:** Ensure every `get => OriginalNameState.Instance.XXX` references an actual property on the state class. Sibling subagents often use wrong casing (e.g., `VTSTOREparams` vs `VtstoreParams`).
- **Cross-reference breaking:** Methods that read other public static members must still resolve correctly after forwarding. Test by checking that all internal references use the same field names.
- **DateTime.Now in constructor:** If multiple DateTime fields default to `DateTime.Now`, they'll all get the same timestamp. This is usually fine (they represent "at startup"), but note it.
- **Static readonly initialization order:** The `_instance` field initializer runs before any static members are accessed, so the singleton is fully constructed on first use. No race condition in single-threaded scenarios.

## 2026-08-20 新增教訓 — TASK-014-A5f/A5g 經驗萃取

### 教訓 1: 內部直接屬性引用（CRITICAL）
MainWindow.axaml.cs 中的方法內部（如 `takeaways_params2Var()`）使用 `m_xxx = value`（直接存取），而非 `MainWindow.m_xxx`。這些是「同一類別的 static member」，所以方法內直接寫 `m_xxx = value` 即可。但一旦刪除存根，這些引用就斷裂了。

**必須 grep 三種模式**：
```bash
# 外部檔案引用
grep -rn 'MainWindow\\.m_xxx' VPOS_Avalonia/ --include='*.cs'

# 內部直接賦值
grep -n '\\bm_xxx\\s*=' VPOS_Avalonia/Views/MainWindow.axaml.cs

# 內部直接讀取
grep -n '\\bm_xxx\\.\\|\\bm_xxx\\s*==' VPOS_Avalonia/Views/MainWindow.axaml.cs
```

### 教訓 2: 存根刪除順序（鐵律）
1. 外部 cascade 替換（所有 Views/, WebAPI/, Thread/ 等）
2. MainWindow.axaml.cs 內部所有引用替換（含直接存取 `m_xxx =`、`m_xxx.`、`m_xxx ==`）
3. 獨立 grep 驗證 — `grep 'MainWindow\\.m_xxx'` 應為 0
4. 刪除存根
5. 最終驗證 — `grep 'public static.*m_xxx'` 應為 0

**⚠️ 不可跳過任何步驟，否則會產生 CS0103 編譯錯誤。**

### 教訓 3: 子代理 DoD 計數不可靠
子代理回報的計數可能不準確（如 TASK-014-A5f 回報 9 處但實際 7 處）。**vpos_lead 必須獨立執行 grep 驗證**，不依賴子代理的回報數字。

### 教訓 4: Cascade 替換後的命名慣例
- `m_UBER_EATS_params` → `mUBER_EATS_params`（保留 m 前綴，VTSTORE/UBER_EATS/FOODPANDA 等全大寫縮寫不拆）
- `m_FOODPANDA_params` → `mFOODPANDA_params`
- **派單時必附提醒**: "屬性命名慣例：m_XXX → mXxx（駝色，保留 m_ 前綴）。全大寫縮寫如 UBER_EATS、FOODPANDA、VTSTORE 不拆。"

## Related

- `simplify-code` — general code cleanup after extraction
- `writing-plans` — plan this refactoring before executing
- `subagent-driven-development` — delegate to subagents for parallel file modifications
