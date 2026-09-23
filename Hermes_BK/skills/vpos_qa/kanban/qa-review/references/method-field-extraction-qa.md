# Method/Field Extraction QA Review Pattern

## When to Use
After any subagent completes a task that extracts methods and/or fields from a large codebehind file (e.g., MainWindow.axaml.cs) to a singleton/state class (e.g., MainWindowState.cs).

## 8-Point Check Pattern

### Check 1: Method definitions removed from source file
```bash
grep -n '^\s*\(private\|public\|internal\|protected\)\s\+\(void\|Task\|bool\|int\|string\)\s\+MethodNames\|s\?' <source_file>
```
**Expected**: 0 matches (except intentional stubs like Window_Loaded)

### Check 2: Field declarations removed from source file
```bash
grep -n '^\s*\(private\|public\|internal\|protected\)\s\+\(Thread\|Timer\|int\|bool\)\s\+FieldNames\|s\?' <source_file>
```
**Expected**: 0 matches

### Check 3: Call sites updated to Instance.Method(this, ...)
```bash
grep -n 'MainWindowState\.Instance\.\(Method1\|Method2\|...)(this' <source_file>
```
**Expected**: ≥1 match per method that has callers. Verify no direct calls remain.

### Check 4: Stub methods correctly delegate to Instance
```bash
grep -A3 'void Window_Loaded' <source_file>
```
**Expected**: Stub body calls `MainWindowState.Instance.OnWindowLoaded(this, sender, e)`

### Check 5: Method signatures in target file include MainWindow parameter
```bash
grep -n 'public.*MethodNames\|s\+\(MainWindow\|void\|Task\)' <target_file>
```
**Expected**: All methods have `MainWindow mw` as first parameter

### Check 6: All fields declared in target file
```bash
grep -n '^\s*\(private\|public\|internal\|protected\)\s\+\(Thread\|Timer\|int\|bool\)\s\+FieldNames\|s\?' <target_file>
```
**Expected**: All fields found. Also grep for usages without declarations — these indicate MISSING fields.

### Check 7: No duplicate method definitions in target file
```bash
grep -c 'public.*MethodNames\|s\+' <target_file>
```
**Expected**: Each method appears exactly once as a definition.

### Check 8: Code style consistency
- No stray method name fragments (lines containing only a method name, not a definition or call)
- All method calls pass required parameters
- Brace balance: `{` count == `}` count

## Critical Pitfalls Found (TASK-024a)

### Pitfall 1: Stub body breakage
**Problem**: When extracting `Window_Loaded`, the stub replacement only kept the delegate line but left the original method body AFTER the closing brace `}`. This orphaned code sits in the class member declaration area, not inside any method.
**Detection**: `read_file` the stub area and verify the opening `{` and closing `}` are balanced within the stub.
**Fix**: Move all original body code to the target method, or keep it inside the stub.

### Pitfall 2: Missing field declaration in target
**Problem**: A field used in the extracted method (e.g., `m_intTimerCount`) was not declared in the target class. The field exists in the source file but wasn't part of the extraction checklist.
**Detection**: After extraction, grep all field usages in the target file, then grep for declarations. Any usage without a matching declaration is a missing field.
**Fix**: Add the field declaration to the target class.

### Pitfall 3: Stray method name fragments
**Problem**: Lines containing only a method name (e.g., `MainTimmer_Tick` on its own line) remain in the target file after extraction. These are neither definitions nor calls — they are extraction artifacts.
**Detection**: Search for lines that are exactly a method name (or start with it and have no `(` or `)`).
**Fix**: Delete these lines or convert to comments.

### Pitfall 4: Missing method parameter in call
**Problem**: An extracted method requires a `MainWindow mw` parameter, but some calls within the target file don't pass it (e.g., `RunCpuReportBat()` instead of `RunCpuReportBat(mw)`).
**Detection**: Compare method signatures with all calls to those methods in the target file.
**Fix**: Update calls to include the required parameter.

## Quick Verification Script
```python
import re, os

methods = ["SpecifyScreen", "OnWindowLoaded", "InitTimmer", "DeleteTimmer", "RunCpuReportBat",
           "MainTimmer_Tick", "syncthreadStop", "syncthreadCreate", "printthreadStop", "printthreadCreate"]
fields = ["m_AutoSyncThread", "m_PrintThread", "m_intTimerCount", "m_blnBatchShow", "MainTimmer"]

# Check source file
with open(source) as f:
    src = f.read()
for m in methods:
    defs = [l for l in src.split('\n') if re.search(r'\b' + m + r'\s*\(', l) and re.match(r'\s*(private|public|internal|protected)\s+', l.strip())]
    if defs: print(f"FAIL: {m} still defined in source")

for fld in fields:
    decls = [l for l in src.split('\n') if re.search(r'\b' + fld + r'\b', l) and re.match(r'\s*(private|public|internal|protected)\s+', l.strip())]
    if decls: print(f"FAIL: {fld} still declared in source")

# Check target file
with open(target) as f:
    tgt = f.read()
for m in methods:
    defs = [l for l in tgt.split('\n') if re.search(r'\b' + m + r'\s*\(', l) and re.match(r'\s*(private|public|internal|protected)\s+', l.strip())]
    if len(defs) == 0: print(f"FAIL: {m} NOT defined in target")
    elif len(defs) > 1: print(f"FAIL: {m} DUPLICATE in target ({len(defs)} times)")
    elif 'MainWindow' not in defs[0]: print(f"FAIL: {m} missing MainWindow param")

for fld in fields:
    decls = [l for l in tgt.split('\n') if re.search(r'\b' + fld + r'\b', l) and re.match(r'\s*(private|public|internal|protected)\s+', l.strip())]
    if not decls: print(f"FAIL: {fld} NOT declared in target")

# Check brace balance
if tgt.count('{') != tgt.count('}'): print(f"FAIL: brace imbalance in target ({tgt.count('{')} vs {tgt.count('}')}))")
```

## Output Format
Write findings to `review-reports/review-TASK-XXX-extraction.md` with:
- Review date
- Modified files with line counts
- PASS/FAIL for each of the 8 checks
- List of found issues with line numbers
- Conclusion (PASS / REJECTED with reasons)
- Recommended fix order

Then update `task_board.json` subtask:
- `qa_review` = "PASS" or "REJECTED"
- `qa_review_file` = path to review report
