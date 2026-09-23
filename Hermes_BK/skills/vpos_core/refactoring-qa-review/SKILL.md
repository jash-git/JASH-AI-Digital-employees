---
name: refactoring-qa-review
description: Use when QA-reviewing atomic code refactoring tasks (method extraction, field migration, call-site updates, codebase restructure, thread-safety/concurrency synchronization).
---

# Refactoring QA Review

Use when QA-reviewing any atomic code refactoring task — method extraction, field migration, call-site updates, codebase restructure, **or a thread-safety / concurrency synchronization refactor** (volatile flag + `lock(this)` serialization, collection-wrapper synchronization such as BulkObservableCollection). For the latter class, use the checkpoints in `references/thread-safety-refactor-review.md` — the structural pitfalls below do not cover it.

## Workflow

### 1. Identify Review Targets
From the task description, extract the specific files and areas to check. For method-extraction tasks:
- **Source file**: Verify original methods are removed (grep for definitions, not just calls)
- **Target file**: Verify methods added with correct signatures
- **Call sites**: Verify all callers updated to new pattern (e.g., `Instance.Method(this, ...)`)
- **Fields**: Verify all migrated fields declared in target file

### 2. Parallel File Reads
Read ALL review areas in parallel - never read one file at a time. For each target:
- Read the relevant line ranges
- Use `search_files` to verify no residual definitions/calls remain

### 3. Structural Integrity Checks (Critical)
After method extraction/refactoring, check for these common structural pitfalls:

#### Pitfall A: Orphaned braces
Methods may have stray `{` before `public void MethodName` and `}` after the method body, creating invalid syntax. Look for patterns like:
```
}
{
public void SomeMethod(MainWindow mw)
```
This happens when the extraction tool wraps methods in extra braces.

#### Pitfall B: Orphaned identifiers (naked method names as statements)
A method name appears alone on a line between two methods, e.g.:
```
}
Window_Loaded
{
public async void OnWindowLoaded(...)
```
This is a leftover from incomplete deletion.

#### Pitfall C: Bare method calls (missing `this` / `mw` parameter)
Methods changed to require a `MainWindow mw` parameter but internal calls within the same class still use bare calls:
```
// Method signature now requires (MainWindow mw, ...)
// But internal call is still:
syncthreadCreate();        // WRONG - should be syncthreadCreate(this);
InitTimmer();              // WRONG - should be InitTimmer(this);
DeleteTimmer();            // WRONG - should be DeleteTimmer(this);
```

#### Pitfall D: Missing field declarations — the 2-step field audit (CRITICAL)
Fields used in the target file but never declared. **Never skip this step** — it is the #1 cause of CS0103 after extraction.

**Step 1 — Collect all field usages in the target file:**
`search_files(pattern='<field_name>', path='<target_file>')` — note all line numbers where the field is READ or WRITTEN.

**Step 2 — Verify declaration in BOTH files:**
- `search_files(pattern='int|bool|string|Thread|Timer|List<|CustBtn|ShopCart|func_mainData|DateTime|m_bln|m_int|m_str|m_Dbl.*<field_name>', path='<target_file>')` — check target file
- `search_files(pattern='<field_name>', path='<source_file>')` — check source file (field may have been left behind)

**Rule:** If usages > 0 AND declarations == 0 in BOTH files → FAIL with CS0103. The field must exist in exactly one file.

**Step 3 — Cross-file ownership audit (NEW, added 2026-08-18):**
Fields may be declared in the source file (e.g., MainWindow.axaml.cs) but used in the target file (e.g., MainWindowState.cs). After moving methods, check:
- Every field referenced in the target file's moved methods: is it declared in the target file, or does the target method need to access it via `mw.<field>` or `MainWindowState.Instance.<field>`?
- If a field is declared ONLY in the source file and used in the target file → either move the field to the target file, or change the reference to use the proper accessor pattern.

**Verification pattern (for each field used in moved methods):**
```
# 1. Count usages in target file
search_files(pattern='\\b<field_name>\\b', path='<target_file>')
# 2. Count declarations in target file
search_files(pattern='private|public|internal.*\\b<field_name>\\b', path='<target_file>')
# 3. Check if declared in source file
search_files(pattern='\\b<field_name>\\b', path='<source_file>')
# 4. If usages > 0 AND declarations == 0 in target AND not in source → MISSING FIELD
```

### 4. Cross-File Call Verification
- In source file: `search_files` for `Instance.MethodName(this, ...)` - should find all expected calls
- In source file: `search_files` for original method definitions - should find NONE
- In source file: `search_files` for original field declarations - should find NONE
- In target file: `search_files` for method signatures - should find all expected methods
- In target file: `search_files` for bare calls (without `this`) to parameterized methods

### 5. Build Verification (if possible)
Run `dotnet build` to confirm compilation passes. If `dotnet` is unavailable, note this as a limitation.

### 6. Decision
- **PASS**: All checks pass, build succeeds
- **REJECTED**: Any check fails - list ALL failures with line numbers

### 7. Dead Using Statement Verification (CRITICAL — added 2026-08-21)

When verifying that a `using` statement is safe to remove, **never check only the most common type** (e.g. only `ArrayList` for `System.Collections`). You must scan for ALL types in that namespace.

**Verification procedure for `using System.Collections;` removal:**
```bash
# Scan for ALL non-generic collection types in the namespace
rg -n -S 'ArrayList|Hashtable|Queue|Stack|SortedList|BitArray|NameValueCollection|StringCollection|ListDictionary|HybridDictionary|DictionaryEntry|CollectionBase|ReadOnlyCollectionBase' <target_file>
```

**Verification procedure for `using System.Collections.Generic;` removal:**
```bash
rg -n -S 'List<|Dictionary<|HashSet<|SortedSet<|KeyValuePair<|IEnumerable<|IList<|IDictionary<|Func<|Action<|Predicate<|Comparer<|Enumerator' <target_file>
```

**Verification procedure for `using System.Text;` removal:**
```bash
rg -n -S 'StringBuilder|Encoding|Regex' <target_file>
```

**⚠️ Lesson from TASK-015 dead using cleanup:** EzioDll.cs L145 uses `static Hashtable BarcodeTypeHash = new Hashtable();` — the `using System.Collections;` is REQUIRED. Removing it would cause CS0246. The initial scan only checked for `ArrayList` and incorrectly flagged it as safe to remove.

**Rule:** Before removing any `using` statement, run a comprehensive scan of ALL types in that namespace. If ANY match is found → the using is NOT dead.

## Deliverable
Update `task_board.json`:
- `qa_review`: "PASS" or "REJECTED"
- `qa_review_file`: path to review report
- If REJECTED, include `qa_rejection_reason` with specific failures

## Reference Files
See `references/` for project-specific pitfall details:
- `vpos-avalonia-mainwindow-state-pitfalls.md` - VPOS_Avalonia MainWindowState.cs specific issues
- `thread-safety-refactor-review.md` - checkpoints for atomic thread-safety/concurrency refactors (volatile flag, lock(this) scope, re-entrancy deadlock, background-thread bypass grep)