# Connection Pooling 重構模式 (TASK-010a)

## 情境
SqliteDataAccess.cs 等 DBLib 檔案中，每個 Load() 方法都 `new SQLiteConnection()`，沒有 Connection Pooling。SyncThread 每秒多次呼叫，頻繁開關連線造成 I/O 瓶頸與 WAL 競爭。

## 標準重構模式

### 1. 加入共享連接基礎設施
在 class 開頭（第一個 method 之前）加入：

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

### 2. 重構簡單查詢方法
從：
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

改為：
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

## 驗證腳本模板
寫在 `/tmp/hermes-verify-connection-pooling.sh`：

```bash
#!/bin/bash
FILE="<目標檔案>"
PASS=0
FAIL=0

# Check: _sharedConnection.Query count >= N (N = 重構方法數)
COUNT=$(grep "_sharedConnection.Query" "$FILE" | wc -l)
if [ "$COUNT" -ge N ]; then echo "✅ _sharedConnection.Query: $COUNT"; PASS=$((PASS+1))
else echo "❌ _sharedConnection.Query: $COUNT (<N)"; FAIL=$((FAIL+1)); fi

# Check: new SQLiteConnection(ConnectionStringLoad()) 應大幅減少
COUNT=$(grep "new SQLiteConnection(ConnectionStringLoad())" "$FILE" | wc -l)
echo "ℹ️ new SQLiteConnection count: $COUNT (剩帶參數的查詢)"

# Check: _lock exists
if grep -q "private static readonly object _lock" "$FILE"; then echo "✅ _lock found"; PASS=$((PASS+1))
else echo "❌ _lock missing"; FAIL=$((FAIL+1)); fi

echo "=== Result: $PASS passed, $FAIL failed ==="
```

## 陷阱與注意事項

### 陷阱：lock count 比方法數多 1
`GetSharedConnection()` 內部也有一個 `lock (_lock)`，所以 `grep -c "lock (_lock)"` 的結果會比重構的方法數多 1。驗證時需注意此差異。

### 陷阱：GetSharedConnection() 被宣告但未被呼叫（TASK-010）
vpos_core 寫了 `GetSharedConnection()` 函數，但忘了在 Load() 方法中使用它。所有 `_sharedConnection.Query` 都是直接存取，沒有先初始化連接。

**派單時必附提醒**: "注意：所有 `_sharedConnection.Query` 必須改為 `GetSharedConnection().Query`，確保連接先初始化。不要直接存取 `_sharedConnection`。"

**vpos_lead 修復方式**: `patch(replace_all=True)` 將 `_sharedConnection.Query` → `GetSharedConnection().Query`

**驗證**:
```bash
grep "_sharedConnection.Query" <file> | wc -l → 應為 0
grep "GetSharedConnection().Query" <file> | wc -l → 應 >= N (重構方法數)
```

### 執行緒安全
- lock 粒度為整個查詢，高併發時可能成為瓶頸
- SQLite 本身是檔案型資料庫，lock 粒度可接受
- 若未來需要更高效能，可考慮改用 `ReaderWriterLockSlim`

### 連線中斷處理
- `GetSharedConnection()` 有 `State != ConnectionState.Open` 檢查
- 若連線中斷會自動重新建立（double-check locking）
- 建議加入 try-catch 包裝 `_sharedConnection.Open()` 以處理初始化失敗

### 潛在風險：共享連接永不 Dispose
共享連接在應用程式生命週期中不會被 Dispose。建議在 `App.OnExit()` 或適當的關閉流程中呼叫 `_sharedConnection.Dispose()`。
