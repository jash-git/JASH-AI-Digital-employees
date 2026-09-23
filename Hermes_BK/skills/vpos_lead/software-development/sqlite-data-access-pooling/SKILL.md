---
name: sqlite-data-access-pooling
description: Refactor SqliteDataAccess.cs from per-call new SQLiteConnection() to shared connection + lock pooling, eliminating I/O bottleneck and WAL contention.
tags: [vpos-avalonia, database, performance]
---

# VPOS Avalonia — SQLite Data Access Connection Pooling

Procedure for converting all `using (IDbConnection cnn = new SQLiteConnection(ConnectionStringLoad()))` patterns in SqliteDataAccess.cs to use a shared connection with lock-based synchronization.

## Prerequisites

- `_lock` object and `_sharedConnection` field already exist at class level
- `GetSharedConnection()` double-checked-locking method exists (lines 20-34)
- File: `VPOS_Avalonia/DBLib/SqliteDataAccess.cs` (~750 lines)

## Two-Phase Refactoring Approach

### Phase A: Simple SELECT * FROM Methods First

Refactor methods that have no parameters or simple parameterless queries. These are the easiest and most numerous.

**Before:**
```csharp
public static List<xxx> xxxLoad()
{
    using (IDbConnection cnn = new SQLiteConnection(ConnectionStringLoad()))
    {
        var output = cnn.Query<xxx>("SELECT * FROM xxx ORDER BY sort");
        cnn.Close(); cnn.Dispose();
        return output.ToList();
    }
}
```

**After:**
```csharp
public static List<xxx> xxxLoad()
{
    lock (_lock)
    {
        var output = _sharedConnection.Query<xxx>("SELECT * FROM xxx ORDER BY sort").ToList();
        return output;
    }
}
```

### Phase B: Methods with WHERE/IN Parameters

Refactor methods that use Dapper parameters (`@ids`, `@id`) or conditional branching. Preserve all parameter logic.

**Before:**
```csharp
public static List<xxx> xxxLoad(String param="")
{
    using (IDbConnection cnn = new SQLiteConnection(ConnectionStringLoad()))
    {
        if (string.IsNullOrEmpty(param))
        {
            var output = cnn.Query<xxx>("SELECT * FROM xxx WHERE ...");
            cnn.Close(); cnn.Dispose();
            return output.ToList();
        }
        else
        {
            var ids = param.Split(',').Select(s => int.Parse(s.Trim())).ToArray();
            var output = cnn.Query<xxx>("SELECT * FROM xxx WHERE SID IN @ids", new { ids });
            cnn.Close(); cnn.Dispose();
            return output.ToList();
        }
    }
}
```

**After:**
```csharp
public static List<xxx> xxxLoad(String param="")
{
    lock (_lock)
    {
        if (string.IsNullOrEmpty(param))
        {
            var output = _sharedConnection.Query<xxx>("SELECT * FROM xxx WHERE ...").ToList();
            return output;
        }
        else
        {
            var ids = param.Split(',').Select(s => int.Parse(s.Trim())).ToArray();
            var output = _sharedConnection.Query<xxx>("SELECT * FROM xxx WHERE SID IN @ids", new { ids }).ToList();
            return output;
        }
    }
}
```

## Methods That Stay Unchanged

- `terminal_dataLoad()` — uses `SQLDataTableModel.GetDataTable()`, not Dapper
- Any method that calls `ConnectionStringLoad("Synchronize")` or other non-"Default" variants (if added later)

## Verification Checklist (MANDATORY before finishing)

Run these commands to confirm the refactor succeeded:

1. **Orphaned connection count** — should be 0:
   ```bash
   grep -c "using.*IDbConnection.*new SQLiteConnection" VPOS_Avalonia/DBLib/SqliteDataAccess.cs
   ```

2. **Shared connection only in GetSharedConnection** — should be exactly 1:
   ```bash
   grep -c "new SQLiteConnection(ConnectionStringLoad())" VPOS_Avalonia/DBLib/SqliteDataAccess.cs
   ```

3. **_sharedConnection.Query count** — should match total refactored methods (56+ after both phases):
   ```bash
   grep -c "_sharedConnection.Query" VPOS_Avalonia/DBLib/SqliteDataAccess.cs
   ```

4. **No orphaned cnn references** — should be 0:
   ```bash
   grep -c "cnn\." VPOS_Avalonia/DBLib/SqliteDataAccess.cs
   ```

5. **Lock count** — should match total refactored methods (49+):
   ```bash
   grep -c "lock (_lock)" VPOS_Avalonia/DBLib/SqliteDataAccess.cs
   ```

## Pitfalls

### Dapper Parameter Names Must Be Preserved
When converting, keep the exact parameter object: `new { ids }`, `new DynamicParameters()`, etc. Some methods pass `new DynamicParameters()` even when empty — this is harmless but should be preserved for consistency with existing callers.

### IN @ids Pattern Requires Array Conversion
The `.Split(',').Select(s => int.Parse(s.Trim())).ToArray()` pattern must stay intact. Dapper handles the array → SQL IN clause automatically via the `@ids` parameter name.

### Comments and Inline SQL Must Be Preserved
Methods like `order_type_dataLoad()` have inline comments (e.g., `//order_type_data 加上 stop_time 過濾條件 at 20221021`). Preserve these when refactoring — they document business logic decisions.

### Conditional Branching Methods Need Both Paths Refactored
Methods with `if/else` or `if(id==0)` branching must have BOTH branches converted to `_sharedConnection`. Missing one branch is a common error.

### Build Verification (When dotnet SDK Available)
```bash
cd VPOS_Avalonia && dotnet build 2>&1 | grep -i "error\|warning" || echo "BUILD OK"
```
If dotnet not available on the VM, rely on the grep-based verification above.

## Post-Refactoring State

After both phases complete:
- **56+** methods use `_sharedConnection.Query`
- **1** remaining `new SQLiteConnection(ConnectionStringLoad())` — only in `GetSharedConnection()`
- **0** orphaned `using (IDbConnection cnn = ...)` blocks
- **0** orphaned `cnn.Close()/cnn.Dispose()` calls
- File timestamp updated, task_board.json status → REVIEW
