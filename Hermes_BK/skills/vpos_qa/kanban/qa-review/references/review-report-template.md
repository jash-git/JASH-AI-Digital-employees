# QA Review Report: TASK-<id> — <title>

| Field | Value |
|-------|-------|
| **Task ID** | TASK-<id> (subtask of TASK-<parent>) |
| **Title** | <title> |
| **Assignee** | <assignee> |
| **Reviewer** | vpos_qa (Hermes subagent) |
| **Review Date** | YYYY-MM-DD |
| **Status** | **PASS / REJECTED** |

---

## 修改摘要

<Describe what was refactored, which methods were changed, before vs after comparison>

### Refactored Methods

| # | Method Name | Table/Resource | Line (lock) |
|---|------------|----------------|-------------|
| 1 | `methodLoad()` | table_name | L80 |
| ... | ... | ... | ... |

### Before vs After

**Before:**
```csharp
// Old pattern with per-call connection
using (IDbConnection cnn = new SQLiteConnection(ConnectionStringLoad())) {
    var output = cnn.Query<T>("SELECT * FROM table").ToList();
    return output;
    cnn.Close();cnn.Dispose();
}
```

**After:**
```csharp
// New pattern with shared connection + lock
lock (_lock) {
    var output = _sharedConnection.Query<T>("SELECT * FROM table").ToList();
    return output;
}
```

---

## Definition of Done 驗證結果

| # | Check Item | Command | Expected | Actual | Result |
|---|-----------|---------|----------|--------|--------|
| 1 | `_sharedConnection.Query` count | `grep ... \| wc -l` | ≥ N | **N** | ✅ PASS / ❌ FAIL |
| 2 | Remaining `new SQLiteConnection()` | `grep ... \| wc -l` | ~M | **M** | ✅ PASS / ❌ FAIL |
| 3 | Leftover `cnn.Close();cnn.Dispose()` in refactored blocks | manual check | 0 | **0** | ✅ PASS / ❌ FAIL |

### DoD #N Notes

<Explain any discrepancies, e.g., cnn.Close count higher than expected due to error-handling branches>

---

## 潛在風險評估

### 🔴 HIGH — <Risk Category>

| Item | Description | Mitigation |
|------|-------------|------------|
| Thread Safety | ... | lock (_lock) covers all reads |
| Connection Failure | ... | Consider try-catch + reconnect |

### 🟡 MEDIUM — <Risk Category>

| Item | Description | Mitigation |
|------|-------------|------------|
| WAL Competition | ... | Lock serializes access |

### 🟢 LOW — <Risk Category>

| Item | Description |
|------|-------------|
| Memory Management | Shared connection lives for app lifetime; suggest cleanup in App.OnExit() |

---

## 結論

**TASK-<id> QA Review: PASS / REJECTED**

<Final verdict with any recommendations for follow-up tasks or next subtask>
