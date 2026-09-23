---
name: qa-review
description: "Structured QA review workflow for kanban code-refactoring tasks — DoD grep checks, refactoring completeness verification, shared resource validation, structured markdown report, and task_board.json update."
version: 1.0.0
metadata:
  hermes:
    tags: [qa-review, kanban, code-review, refactoring, verification]
    related_skills: [kanban-worker, github-code-review]
---

# QA Review — Kanban Code Refactoring Tasks

Structured QA review workflow for kanban tasks that involve code refactoring (connection pooling, SQL injection fixes, async migration, etc.). Produces a markdown review report and updates `task_board.json`.

## When to Use

- A kanban task involves refactoring multiple methods/functions
- The task has specific DoD grep counts to verify
- A review report must be written to `review-reports/`
- `task_board.json` subtask status needs updating

## Workflow

### Step 1: Run DoD Grep Checks

Execute the verification commands specified in the task. Typical checks for refactoring tasks:

```bash
# Count of new pattern (e.g., shared connection usage)
grep "_sharedConnection.Query" VPOS_Avalonia/DBLib/SqliteDataAccess.cs | wc -l

# Count of remaining old pattern (e.g., per-call connections)
grep "new SQLiteConnection(ConnectionStringLoad())" VPOS_Avalonia/DBLib/SqliteDataAccess.cs | wc -l

# Count of leftover patterns that should be gone
grep "cnn.Close();cnn.Dispose()" VPOS_Avalonia/DBLib/SqliteDataAccess.cs | wc -l
```

**DoD criteria:**
- New pattern count ≥ expected minimum (all refactored methods must use it)
- Old pattern count ≈ expected remainder (only non-refactored methods should have it)
- Leftover pattern count = 0 in refactored blocks (no missed cleanup)

#### Library Migration Tasks (e.g., System.Drawing → ImageSharp)

For library replacement tasks, checks are primarily **negative** (old patterns gone) and **positive** (new patterns present), plus **intentional retention** (some files keep old patterns):

```bash
# Negative: no remaining old pattern in refactored file
! grep -q 'System\.Drawing' ToolLib/BitmapBase64_Funs.cs   # should PASS (no match)

# Positive: new pattern present
grep -q 'SixLabors\.ImageSharp\.Image\.Load' Models/CS_PrintTemplate.cs  # should PASS (match found)

# Intentional retention: some files keep old patterns
grep -q '^using System\.Drawing;' ToolLib/DPI_Funs.cs   # should PASS (intentionally kept)
```

**DoD criteria for library migration:**
- All refactored files have zero remaining old-pattern references (except intentional retention)
- New pattern present in all expected locations
- Intentional-retention files verified separately

### Step 2: Verify Shared Resource Initialization

For tasks involving shared connections, singletons, or static resources:

```bash
# Check lock object declaration
grep "_lock" <file> | head -5

# Check shared resource declaration and initialization method
grep "GetSharedConnection\|_sharedConnection" <file> | head -10
```

**Verify:**
- Lock object is `static readonly` (thread-safe)
- Shared resource is declared at class level
- Initialization uses double-check locking (outer if + inner lock + inner check)
- Connection state check: `_resource == null || _resource.State != Open`

### Step 3: Verify Refactoring Completeness

For each refactored method, confirm the lock block contains the new pattern and no leftover old patterns:

```bash
# Find all lock blocks that use the new pattern
grep -n "lock (_lock)" <file> | while read line; do
  linenum=$(echo "$line" | cut -d: -f1)
  context=$(sed -n "${linenum},$((linenum+5))p" <file>)
  if echo "$context" | grep -q "_sharedConnection.Query"; then
    # This is a refactored method — check for leftovers
    leftover=$(sed -n "${linenum},$((linenum+10))p" <file> | grep "cnn.Close()")
    if [ -n "$leftover" ]; then
      echo "LINE $linenum: HAS leftover cnn.Close()"
    fi
  fi
done
```

### Step 4: List Refactored Methods

Document which methods were refactored for the report:

```bash
# Extract method names from lock blocks using new pattern
grep -n "lock (_lock)" <file> | while read line; do
  linenum=$(echo "$line" | cut -d: -f1)
  context=$(sed -n "${linenum},$((linenum+5))p" <file>)
  if echo "$context" | grep -q "_sharedConnection.Query"; then
    method=$(sed -n "$((linenum-20)),$((linenum+1))p" <file> | grep "public static List<" | head -1)
    echo "$method"
  fi
done | sort -u
```

### Step 5: Write Review Report

Create `review-reports/review-TASK-<id>-<description>.md` with this structure:

| Section | Content |
|---------|---------|
| Header table | Task ID, title, assignee, reviewer, date, status (PASS/REJECTED) |
| 修改摘要 | Which methods were refactored, before vs after code comparison |
| DoD Verification Table | Each grep check with expected vs actual values and PASS/FAIL |
| 潛在風險評估 | Thread safety, connection failure handling, memory/resource management |
| 結論 | Final verdict + any recommendations for follow-up tasks |

**Report filename convention:** `review-reports/review-TASK-<id>-<short-description>.md`

### Step 6: Update task_board.json

Update the subtask entry in `docs/task_board.json`:

```json
"TASK-010a": {
  "title": "#11a: ...",
  "status": "PASS",
  "completed_date": "2026-08-12",
  "qa_review": "PASS",
  "qa_review_file": "review-reports/review-TASK-010a-sqlitedataaccess-connection-pooling.md"
}
```

**If PASS:** set `status: "PASS"`, add `qa_review: "PASS"` and `qa_review_file`
**If REJECTED:** set `status: "REJECTED"`, add `qa_review: "REJECTED"` with reason in summary

### Step 7: Handle Sibling Subagent Conflicts

The task_board.json may be modified by sibling subagents between your read and write. Always re-read before patching:

```bash
# If patch fails with "candidate content fails .json syntax validation" + "modified by sibling"
# Re-read the file, then retry the patch with updated old_string
```

## Common Pitfalls

### False Positive on `cnn.Close();cnn.Dispose()` Count

Non-refactored methods may have multiple error-handling branches (try-catch-finally), each calling `cnn.Close();cnn.Dispose()`. The count will exceed the expected number of non-refactored methods. **Solution:** verify that none of the refactored lock blocks contain leftover `cnn.Close()` — if they don't, the excess is from error-handling branches in non-refactored code.

### Lock Coverage False Negative with Nested IF/ELSE (TASK-010b 教訓)

**問題**: `grep -B1 "lock (_lock)" <file> | grep "_sharedConnection.Query"` 只抓到 43/56，因為 lock 語句與 Query 呼叫之間可能隔了 2+ 行（IF/ELSE 巢狀區塊）。

**修復方式 — Python state machine**:
```python
with open('<file>') as f:
    lines = f.readlines()
in_lock = False
count = total = 0
for line in lines:
    if 'lock (_lock)' in line.strip():
        in_lock = True
    elif in_lock and '_sharedConnection.Query' in line:
        count += 1
    total += 1 if '_sharedConnection.Query' in line else 0
print(f'{count}/{total}')  # 應為 N/N（全部覆蓋）
```

**適用場景**: 任何 lock + shared resource 重構任務的驗證，特別是帶 IF/ELSE 條件分支的方法。

### Shared Connection Never Disposed

The shared connection lives for the application lifetime. For desktop apps (Avalonia), this is acceptable but note it as a low-priority risk. Suggest cleanup in `App.OnExit()` if needed.

### Connection State Stale After File Deletion

If the SQLite file is deleted/moved, `_sharedConnection.State` may still report `Open`. The query will throw an exception on next access. Consider adding try-catch + reconnection logic for production robustness.

## Reference Templates

- `references/review-report-template.md` — Markdown review report template
- `references/adhoc-verification-pattern.md` — Ad-hoc verification script pattern with bash pitfalls and Python state machine for lock coverage
- `references/method-field-extraction-qa.md` — 8-point QA review pattern for method/field extraction tasks (codebehind → state class), with 4 critical pitfalls from TASK-024a