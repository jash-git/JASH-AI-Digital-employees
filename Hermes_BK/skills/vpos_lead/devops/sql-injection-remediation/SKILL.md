---
name: sql-injection-remediation
description: "Replace string.Format SQL concatenation with Dapper parameterized queries in C#/SQLite codebases."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [security, sql-injection, dapper, csharp, sqlite]
    related_skills: [systematic-debugging, sqlite-connection-pooling]
---

# SQL Injection Remediation (C# / SQLite / Dapper)

Replace `string.Format()` or `$""` SQL string concatenation with Dapper parameterized queries (`@param` syntax).

## When to Use

- C# project uses `string.Format()` or `$""` to build SQL with user input
- Legacy codebase with raw `SQLiteCommand` / `SQLiteDataAdapter` accepting string SQL
- Security audit finding SQL injection vulnerabilities
- Project already uses Dapper (check `*.csproj` for `Dapper` PackageReference)

## Prerequisites

1. Verify Dapper is in the project: `grep -r 'PackageReference.*Dapper' *.csproj`
2. If not installed: `dotnet add package Dapper`
3. Identify all injection points:
   ```
   grep -rn 'string\.Format.*SELECT\|string\.Format.*UPDATE\|string\.Format.*INSERT\|string\.Format.*DELETE' --include='*.cs'
   ```

## Step 1: Add Parameterized Methods to DB Helper

If the DB helper (e.g., `SQLDataTableModel.cs`) lacks parameterized methods, add these to the class:

```csharp
// Add to top of file:
using Dapper;
using System.Linq;

// Reflection helper: convert Dapper dynamic results to DataTable
private static DataTable DapperToDataTable<T>(IEnumerable<T> results)
{
    DataTable table = new DataTable();
    if (results == null || !results.Any()) return table;
    var props = typeof(T).GetProperties();
    foreach (var prop in props)
    {
        Type colType = prop.PropertyType;
        if (colType.IsGenericType && colType.GetGenericTypeDefinition() == typeof(Nullable<>))
            colType = Nullable.GetUnderlyingType(colType);
        table.Columns.Add(prop.Name, colType);
    }
    foreach (var item in results)
    {
        var row = table.NewRow();
        foreach (var prop in props)
            row[prop.Name] = prop.GetValue(item) ?? DBNull.Value;
        table.Rows.Add(row);
    }
    return table;
}

// SELECT with parameters — returns DataTable (for legacy consumers)
public static DataTable GetDataTableParams(string SQLiteString, object parameters)
{
    DataTable myDataTable = new DataTable();
    LogFile.SQLRecord(SQLiteString);
    try
    {
        SQLiteConnection icn = OpenConn();
        var results = icn.Query(SQLiteString, parameters);
        myDataTable = DapperToDataTable(results);
        if (icn.State == ConnectionState.Open) { icn.Close(); icn = null; }
    }
    catch (Exception ex) { /* existing error logging pattern */ }
    return myDataTable;
}

// INSERT/UPDATE/DELETE with parameters
public static void SQLiteInsertUpdateDeleteParams(string SQLiteString, object parameters)
{
    LogFile.SQLRecord(SQLiteString);
    try
    {
        SQLiteConnection icn = OpenConn();
        SQLiteTransaction mySqlTransaction = icn.BeginTransaction();
        try
        {
            icn.Execute(SQLiteString, parameters, mySqlTransaction);
            mySqlTransaction.Commit();
        }
        catch (Exception ex)
        {
            mySqlTransaction.Rollback();
            /* existing error logging pattern */
        }
        if (icn.State == ConnectionState.Open) { icn.Close(); icn = null; }
    }
    catch (Exception ex) { /* existing error logging pattern */ }
}
```

## Step 2: Replace Each string.Format SQL Call

### Conversion Patterns

| Before (injection) | After (safe) |
|---|---|
| `string.Format("SELECT ... WHERE order_no = '{0}'", userVal)` | `GetDataTableParams("SELECT ... WHERE order_no = @order_no", new { order_no = userVal })` |
| `string.Format("UPDATE t SET x='{0}' WHERE id='{1}'", a, b)` | `SQLiteInsertUpdateDeleteParams("UPDATE t SET x=@x WHERE id=@id", new { x = a, id = b })` |
| `string.Format("INSERT INTO t VALUES ('{0}','{1}')", a, b)` | `SQLiteInsertUpdateDeleteParams("INSERT INTO t VALUES (@a,@b)", new { a, b })` |
| `string.Format("SELECT COUNT(*) FROM t WHERE name='{0}'", n)` | `GetDataTableParams("SELECT COUNT(*) FROM t WHERE name=@name", new { name = n })` |

### Rules

- Use `@paramName` in SQL — Dapper maps anonymous object properties by name
- Keep variable names identical to parameter names for shorthand: `new { order_no }` maps to `@order_no`
- For different names: `new { order_no = m_StrPosOrderNumber }` maps to `@order_no`
- Remove the old `string SQL = string.Format(...)` line entirely
- Remove the old `GetDataTable(SQL)` / `SQLiteInsertUpdateDelete(SQL)` call

### Example: INSERT with many columns

```csharp
// Before (18 string.Format placeholders):
SQL = string.Format("INSERT INTO order_payment_data (...) VALUES ('{0}','{1}',...,'{17}')", ...);
SQLDataTableModel.SQLiteInsertUpdateDelete(SQL);

// After:
SQL = "INSERT INTO order_payment_data (...) VALUES (@order_no,@payment_sid,...,@no_include_invoice)";
SQLDataTableModel.SQLiteInsertUpdateDeleteParams(SQL, new {
    order_no, payment_sid, payment_code, payment_name, payment_time,
    created_time, updated_time, del_flag, amount, received_fee,
    change_fee = m_dblChangeFee, item_no,
    payment_info = Strpayment_info, payment_module_params = Strpayment_module_params,
    payment_module_code = Strpayment_module_code,
    coin_discount = dblCoin_DiscountSum, coupon_discount = dblStoreRedeemAmountSum,
    no_include_invoice
});
```

## Step 3: Verify

1. **No remaining string.Format SQL**: `grep -n 'string\.Format.*SELECT\|string\.Format.*UPDATE\|string\.Format.*INSERT\|string\.Format.*DELETE' *.cs` — should return zero matches
2. **All new calls use parameterized methods**: `grep -n 'GetDataTableParams\|SQLiteInsertUpdateDeleteParams' *.cs` — should show all fixes
3. **All method names exist** in the DB helper class
4. **Build passes**: `dotnet build`

## Pitfalls

- **`AsTable()` does not exist in Dapper** — use `DapperToDataTable<T>()` reflection helper instead
- **Multi-line SQL** — the parameterized SQL string may be long; assign to `SQL` variable then pass to method, or inline
- **Transaction-aware methods** — if the original method used `SQLiteTransaction`, the parameterized version must also use transactions
- **User input in WHERE clauses** — even internal variables like `m_StrPosOrderNumber` are injection vectors if they originate from user input anywhere in the chain
- **Non-target SQL calls** — some `GetDataTable(SQL)` calls may use `DateTime.Now` or hardcoded strings; these are safe and should NOT be changed
- **`string.Format` for non-SQL strings** — `string.Format` for UI messages, log messages, etc. is fine; only SQL string concatenation needs fixing
- **C# reserved keyword as column name** — if the DB column is `params`, `type`, `namespace`, etc., use `@params = value` syntax in the anonymous object. Without the `@` prefix, C# will reject compilation.
- **Identical code blocks in multiple methods** — the same `string.Format` SQL may be duplicated across methods (e.g., `VerifyVLCS` and `IsRegisterDevice`). Use `replace_all=True` with `patch` when blocks are truly identical, or add surrounding context lines to make each patch unique.

## Verification Checklist

- [ ] All `string.Format` SQL patterns eliminated (grep returns zero)
- [ ] All 6 target injection points replaced with parameterized calls
- [ ] All method names (`GetDataTableParams`, `SQLiteInsertUpdateDeleteParams`) exist in DB helper
- [ ] `using Dapper;` and `using System.Linq;` added to both files
- [ ] `DapperToDataTable<T>` helper exists and uses `DBNull.Value` for nulls
- [ ] `dotnet build` passes
