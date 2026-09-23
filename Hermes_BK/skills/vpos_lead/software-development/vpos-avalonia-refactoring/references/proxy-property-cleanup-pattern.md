# Proxy Property Cleanup Pattern

Use when MainWindow.axaml.cs has ~30+ `public static T xxx { get => MainWindowState.Instance.xxx; set => MainWindowState.Instance.xxx = value; }` forwarding properties that need to be removed in favor of direct `MainWindowState.Instance.xxx` access.

## Analysis Workflow

### Step 1: List all public static declarations
```bash
grep -n 'public static' VPOS_Avalonia/Views/MainWindow.axaml.cs
```

### Step 2: Categorize each declaration
Three categories:

| Category | Criteria | Action |
|----------|----------|--------|
| **Proxy properties** | `{ get => MainWindowState.Instance.xxx; set => ... }` | Plan cleanup — replace callers with `MainWindowState.Instance.xxx`, then delete proxy |
| **Static methods** | `public static void/Type MethodName(...)` | Check if already migrated to MainWindowState.cs. If yes → keep forwarding stub or delete. If no → may need migration or keep as-is |
| **WinAPI/system methods** | `FindTrayButtonWindow()`, `ShowTouchKeyboard()`, `ShowSoftKeyboard()`, `SoftKeyboard_OSK()` | **Keep in MainWindow** — these are system-level helpers that other code may call via `MainWindow.MethodName()` |

### Step 3: Cross-reference with MainWindowState.cs
```bash
# List all fields in MainWindowState.cs
grep 'public.*m[A-Z]' VPOS_Avalonia/ViewModels/MainWindowState.cs
```
Match each proxy property to its MainWindowState counterpart. Properties already present in MainWindowState.cs are candidates for proxy removal.

### Step 4: Plan micro-tasks by grouping
Group related proxy properties:
- **Order type group**: m_intOrderTypeIdSelected, m_StrOrderTypeNameSelected, m_StrOrderTypeCodeSelected, m_intOrderTypeInvoiceState, m_intVTS_TOGOInvoiceState, m_intFOODPANDAInvoiceState, m_intUBER_EATSInvoiceState
- **Screen group**: m_dblScreenWidth, m_dblScreenHeight, m_dblScreenDensity, m_dblZoom, m_dblnum
- **Takeaway params group**: m_VTSTORE_params, m_NIDIN_POS_params, m_UBER_EATS_params, m_FOODPANDA_params, m_YORES_POS_params
- **Time tracking group**: m_ClassLastTime, m_DailyLastTime, m_ClassOrderFirstTime, m_ClassOrderLastTime, m_DailyOrderFirstTime, m_DailyOrderLastTime
- **Flag group**: m_blnInvoiceState, m_blnMainReady, m_blnHttpTest
- **Number group**: m_StrPosExpenseNumber, m_StrPosReportNumber, m_StrHasDaily

### Step 5: For each group — find all callers
```bash
grep -rn 'MainWindow\.\(m_xxx\|m_Field\)' VPOS_Avalonia/ --include='*.cs'
```
Replace `MainWindow.m_xxx` with `MainWindowState.Instance.mXxx` (note: camelCase, not snake_case).

### Step 6: Delete proxy properties
After all callers are updated, delete the forwarding property blocks from MainWindow.axaml.cs.

## Important Notes

- **~36 proxy properties** already forward to MainWindowState.cs — the actual migration work is done
- **~14 static methods** already migrated to MainWindowState.cs
- **4 WinAPI methods** (FindTrayButtonWindow, ShowTouchKeyboard, ShowSoftKeyboard, SoftKeyboard_OSK) should remain in MainWindow
- **DataTable members** (m_DTFoodMeal, m_DTTempContentData) — check if declared in MainWindowState.cs or still in MainWindow.axaml.cs

## Naming Convention Reminder

`m_FieldName` → `mFieldName` (camelCase, keep `m_` prefix):
- `m_intOrderTypeIdSelected` → `mIntOrderTypeIdSelected`
- `m_terminal_panel_styles` → `mTerminalPanelStyles`
- `m_VTSTORE_params` → `mVTSTORE_params` (VTSTORE all-caps, don't split)

## Expected Outcome

After cleanup:
- MainWindow.axaml.cs: 0 public static fields (only 4 WinAPI methods)
- All state centralized in MainWindowState.cs singleton
- Cleaner codebase, improved thread safety
