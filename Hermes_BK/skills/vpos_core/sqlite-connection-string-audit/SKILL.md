---
name: sqlite-connection-string-audit
description: Audit & fix cryptic SQLite errors from empty connection strings (ConnectionStringLoad root cause) in VPOS Avalonia.
tags: [vpos-avalonia, sqlite, dblib, debugging, audit]
---

# Cryptic SQLite Error Triage — Empty Connection String (VPOS Avalonia)

Use when the running app throws a cryptic SQLite error such as
`Data Source cannot be empty. Use :memory: to open an in-memory database` while
compilation passes but DB writes/reads fail repeatedly. Produces diagnosis + fix
guidance; actual fixes go to subagents via `vpos-delegation-workflow`.

## Root cause (the one class)
`SQLDataTableModel.ConnectionStringLoad(string id)` only handles three switch cases:
- `"Default"` → vpos.db
- `"Synchronize"` → vtcloud_sync.db
- `"Takeaways"` → takeaways.db

When a caller passes a DB name that is **none of these** AND `blnAppSet=true` (i.e. the
`Database` arg has no `:\\` and isn't a full path), the method returns an **empty string**.
That empty string → `SQLiteConnection.ConnectionString = ""` → `Open()` throws the cryptic
message deep inside SQLite, with NO indication of which Database or call site is at fault.

## Detection (grep first)
- Methods sharing the root cause: `grep -rn 'ConnectionStringLoad' VPOS_Avalonia/DBLib/ --include=*.cs`
- The vulnerable open signature: `grep -rn 'OpenConn(Database' VPOS_Avalonia/ --include=*.cs`
- Callers passing a table name as Database (the hidden mine): `grep -rn 'GetDataTable(Database=' VPOS_Avalonia/Thread/SyncDBData.cs`

## The fix (defense-in-depth)
In `OpenConn(string Database, bool blnAppSet=true)` add before opening:
```csharp
string cnstr = (blnAppSet)? ConnectionStringLoad(Database) : string.Format("Data Source={0};", Database);
if (string.IsNullOrEmpty(cnstr))
{
    throw new ArgumentException(
        "VPOS: OpenConn failed - empty connection string for Database='" + Database + "'. Invalid DB name or missing case in ConnectionStringLoad.");
}
```
Effect: any wrong DB name now throws an explicit `ArgumentException` naming the Database,
instead of a cryptic SQLite error. Normal connection strings (full paths) are unaffected
(`string.IsNullOrEmpty` is false for non-empty input).

## Audit methodology — live / latent / safe classification
When auditing for this class across the codebase, classify every shared-signature method:
- 🔴 **LIVE** — actually triggered at runtime (e.g. DBWriter `useDefault` branch when queue drained). Fix it.
- 🟡 **LATENT** — call sites pass valid values now, but a future maintainer mistake would trigger the identical cryptic error. Harden + document. The most hidden one: `SyncDBData.DBColumnsPadding(table_name,...)` passes a table name as Database; if someone adds a column to the padding list without updating the create-table template, it explodes exactly like the live case.
- 🟢 **SAFE** — structurally never empty (fixed `"Default"` / known literals).

## DoD greps
- `grep 'string.IsNullOrEmpty(cnstr)'` inside `OpenConn(Database,...)` → ≥1
- explicit error message naming Database → present
- no-arg `OpenConn()` signature unchanged
- all original `OpenConn(Database,blnAppSet)` call sites still intact

## Related conventions (vpos-delegation-workflow)
- DB-layer fixes route to `vpos_core`. Never edit the code yourself — Lead hands fixes to the developer; QA (`vpos_qa`) verifies after.
- Each micro-step is a separate delegate_task with exact file:line context pre-loaded.
