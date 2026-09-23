# VPOS_Avalonia MainWindowState.cs Refactoring Pitfalls

## Session: 2026-08-18 (TASK-024a QA Review — Round 2)

### QA Status: REJECTED

#### 1. Missing field `m_intTimerCount` (BLOCKING — NOT FIXED)
- **Symptom**: 6 usages in MainWindowState.cs (L2277, L2279, L2284, L2289, L2317, L2387) but 0 declarations in either file
- **Verification**: `search_files(pattern='int m_intTimerCount', path='MainWindowState.cs')` → 0 matches
- **Also checked**: `search_files(pattern='m_intTimerCount', path='MainWindow.axaml.cs')` → 0 matches
- **Status**: Field still missing after previous fix attempt. Must add `private int m_intTimerCount = 0;` to MainWindowState.cs
- **Impact**: CS0103 compilation error — code will not build

#### 2. `m_strClosingHandoverCheckMsg` cross-file ownership issue
- **Symptom**: Field declared in MainWindow.axaml.cs L5829 but used in MainWindowState.cs L2260-2261
- **Status**: Needs resolution — either move field to MainWindowState.cs or use `mw.m_strClosingHandoverCheckMsg`
- **Impact**: CS0103 compilation error if MainWindowState.cs cannot access MainWindow instance field

### Previously Fixed Issues (confirmed PASS)

#### 3. Orphaned `{` `}` around method definitions — FIXED
- All extra braces removed from SpecifyScreen, OnWindowLoaded, InitTimmer, etc.
- Methods now directly follow `#region` without intervening `{` or `}`

#### 4. Orphaned `Window_Loaded` identifier — FIXED
- L2035 naked `Window_Loaded` text removed

#### 5. Bare method calls without `this` parameter — FIXED
- All 7 internal calls updated: `syncthreadCreate(this)`, `printthreadCreate(this)`, `InitTimmer(this)`, `DeleteTimmer(this)`, `syncthreadStop(this, 0)`, `syncthreadStop(this)`, `printthreadStop(this)`

### QA Checklist for Future Reviews
When QA-reviewing method extraction tasks, always verify:
1. [ ] No orphaned braces around method definitions (Pitfall A)
2. [ ] No orphaned identifiers between methods (Pitfall B)
3. [ ] All internal method calls include `this` parameter (Pitfall C)
4. [ ] Every field used in moved methods is declared in the target file — check BOTH files (Pitfall D)
5. [ ] Cross-file field ownership: fields used in target but declared only in source need accessor pattern
6. [ ] Build verification via `dotnet build`
