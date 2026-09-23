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

## Pitfalls

- **Type name mismatch:** The type before the field name must be the ORIGINAL type, not prefixed with `m_`. Common error: `public static m_StrVersion m_StrVersion` instead of `public static String m_StrVersion`.
- **Accessor reference mismatch:** Ensure every `get => OriginalNameState.Instance.XXX` references an actual property on the state class. Sibling subagents often use wrong casing (e.g., `VTSTOREparams` vs `VtstoreParams`).
- **Cross-reference breaking:** Methods that read other public static members must still resolve correctly after forwarding. Test by checking that all internal references use the same field names.
- **DateTime.Now in constructor:** If multiple DateTime fields default to `DateTime.Now`, they'll all get the same timestamp. This is usually fine (they represent "at startup"), but note it.
- **Static readonly initialization order:** The `_instance` field initializer runs before any static members are accessed, so the singleton is fully constructed on first use. No race condition in single-threaded scenarios.

## Related

- `simplify-code` — general code cleanup after extraction
- `writing-plans` — plan this refactoring before executing
- `subagent-driven-development` — delegate to subagents for parallel file modifications
