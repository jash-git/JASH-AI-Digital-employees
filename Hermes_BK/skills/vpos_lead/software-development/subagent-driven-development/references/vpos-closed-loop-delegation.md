# VPOS Closed-Loop Delegation Workflow

## Overview

VPOS project uses a strict 3-step closed-loop for every task:

1. **Implementer** (`vpos_core` or `vpos_ui`) → fixes code
2. **QA Reviewer** (`vpos_qa`) → validates fix, writes report to `review-reports/`
3. **User Verification** → user runs `dotnet build` and final acceptance

## Mandatory Steps

### 1. Dispatch Implementer

```
delegate_task → vpos_core (backend/hardware) or vpos_ui (UI/ViewModel)
```

**Always include:**
- Full file path and line numbers
- Original broken code snippet
- Target fixed code pattern
- Constraints (MVVM purity, no string.Format SQL, etc.)

### 2. Dispatch QA Reviewer (IMMEDIATELY after implementer completes)

```
delegate_task → vpos_qa
```

QA must verify:
- All fixes applied correctly
- No regressions or missed spots
- Business logic unchanged
- Attempt `dotnet build` if possible

QA writes report to `review-reports/` with verdict: **PASS** or **REJECTED**.

### 3. Cron Monitoring (for EVERY delegation)

```
cronjob → every 3m, repeat 10, monitor sub-agent status
```

If sub-agent is dead/stuck for >9 minutes:
- Report status
- Suggest termination and re-dispatch

## User Preferences

- User types "進度？" to check progress → respond with honest status
- User handles final compilation and verification themselves
- QA review is MANDATORY — never skip it
- User calls closed-loop workflow "鐵律" (iron rule)

## Common Pitfalls

- **Forgetting to dispatch QA reviewer** → always dispatch immediately after implementer
- **Forgetting cron monitoring** → always create cron job for every delegation
- **Skipping re-review** → if QA REJECTED, implementer fixes, then QA reviews again
- **Assuming sub-agent completed** → always verify via file modification timestamps or search

## File Paths

| Role | Workspace |
|------|-----------|
| vpos_ui | `VPOS_Avalonia/Views/`, `ViewModels/`, `UserControl/`, `Assets/` |
| vpos_core | `VPOS_Avalonia/DBLib/`, `WebAPI/`, `WinAPI/`, `ToolLib/`, `Thread/`, `Models/`, `Json2Class/` |
| vpos_qa | `FlaUI_Test/`, `NSIS_Project/`, `review-reports/` |
