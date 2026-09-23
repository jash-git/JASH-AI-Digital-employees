---
name: sqlite-connection-pooling
description: "Add shared SQLiteConnection with double-checked locking to C#/Dapper data access classes, eliminating per-query connection open/close overhead."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [performance, sqlite, dapper, csharp, connection-pooling]
    related_skills: [sql-injection-remediation, systematic-debugging]
---

# SQLite Connection Pooling (C# / Dapper)

Add a shared `SQLiteConnection` with double-checked locking to data access classes that currently create a new connection per query. Eliminates I/O bottleneck and WAL contention from frequent open/close cycles.

## When to Use

- C# project uses Dapper + System.Data.SQLite
- Data access class has many `Load()` methods each doing `new SQLiteConnection(...)` inside a `using` block
- SyncThread or background thread calls these methods frequently (e.g., every second)
- WAL mode is used but still experiencing I/O contention

## Step 1: Add Shared Connection Infrastructure

At the top of the data access class, after the opening brace and before the first method:

```csharp
private static readonly object _lock = new object();
private static SQLiteConnection _sharedConnection;

private static SQLiteConnection GetSharedConnection()
{
    if (_sharedConnection == null || _sharedConnection.State != System.Data.ConnectionState.Open)
    {
        lock (_lock)
        {
            if (_sharedConnection == null || _sharedConnection.State != System.Data.ConnectionState.Open)
            {
                _sharedConnection = new SQLiteConnection(ConnectionStringLoad());
                _sharedConnection.Open();
            }
        }
    }
    return _sharedConnection;
}
```

**Key points:**
- Use `private static readonly object _lock` — not a string or int (avoid interning bugs)
- Double-checked locking pattern prevents race condition on first access
- Check both null AND ConnectionState.Open — connection can close unexpectedly

## Step 2: Refactor Simple SELECT * FROM Methods

For methods that do simple `SELECT * FROM table` queries with no parameters, convert from the per-query pattern to shared connection + lock:

**Before:**
```csharp
public static List<xxx> xxxLoad()
{
    using (IDbConnection cnn = new SQLiteConnection(ConnectionStringLoad()))
    {
        var output = cnn.Query<xxx>("SELECT * FROM xxx", new DynamicParameters());
        cnn.Close();cnn.Dispose();
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
        var output = _sharedConnection.Query<xxx>("SELECT * FROM xxx").ToList();
        return output;
    }
}
```

**Changes made:**
- Remove `using (IDbConnection cnn = new SQLiteConnection(...))` wrapper
- Replace `cnn.Query<>()` with `_sharedConnection.Query<>()`
- Remove `new DynamicParameters()` — not needed for parameterless queries
- Remove `cnn.Close();cnn.Dispose();` — shared connection stays open
- Wrap in `lock (_lock)` to prevent concurrent access issues

## Step 3: Identify Methods NOT to Refactor (keep old pattern)

Do NOT refactor methods that have any of these characteristics:

1. **Parameterized queries** — use `@param`, `IN @ids`, or other Dapper parameters
2. **Conditional logic inside the method** — e.g., `if (string.IsNullOrEmpty(x)) { ... } else { ... }` with different SQL
3. **Complex WHERE clauses** — multiple conditions, JOINs, subqueries
4. **Non-standard query patterns** — manual DataTable construction, custom mapping

Examples of methods to leave unchanged:
- `condiment_dataLoad(String Strcondiment_sids="")` — has IN @ids branch
- `product_category_relationLoad(int id=0)` — conditional SQL based on parameter
- `order_type_dataLoad()` — complex WHERE with datetime comparison
- `terminal_dataLoad()` — manual DataTable construction

## Step 4: Verify

```bash
# Count remaining per-query connections (should be ~20-25, the complex ones)
grep "new SQLiteConnection(ConnectionStringLoad())" SqliteDataAccess.cs | wc -l

# Count shared connection usage (should match number of refactored methods)
grep "_sharedConnection.Query" SqliteDataAccess.cs | wc -l

# Count remaining cnn.Close();cnn.Dispose() (should be ~20-25, the complex ones)
grep "cnn.Close();cnn.Dispose()" SqliteDataAccess.cs | wc -l
```

## Pitfalls

- **Thread safety**: All refactored methods MUST use `lock (_lock)` — Dapper's Query is NOT thread-safe on a shared connection
- **Long-running queries**: If any query takes >1 second, it will block all other callers. Keep queries fast (simple SELECT * FROM).
- **Connection state changes**: The double-checked lock checks both null AND ConnectionState.Open because SQLite connections can close unexpectedly (e.g., database file moved, disk error)
- **WAL mode still recommended**: Even with shared connection, ensure `PRAGMA journal_mode=WAL` is set for concurrent read performance
- **Don't forget the lock on complex methods too**: When you later refactor parameterized methods, they also need `lock (_lock)` around `_sharedConnection.Query<>()`
- **DynamicParameters removal**: Simple SELECT * FROM queries don't need `new DynamicParameters()` — Dapper handles it. Removing this simplifies the code and avoids a minor allocation.

## Verification Checklist

- [ ] Shared connection infrastructure added (lock + _sharedConnection + GetSharedConnection)
- [ ] All simple SELECT * FROM methods refactored to use lock(_lock) + _sharedConnection.Query<>()
- [ ] Methods with parameters/complex WHERE still use old pattern
- [ ] grep counts match expected values
- [ ] File timestamp updated
