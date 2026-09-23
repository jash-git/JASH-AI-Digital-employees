# SQL 注入修復驗證模式

## 驗證腳本模板

```bash
#!/bin/bash
FILE="<目標檔案路徑>"
PASS=true

echo "=== SQL 注入修復驗證 ==="

# 1. 檢查 string.Format SQL 拼接 (應為 0)
echo "[1] 檢查 string.Format SQL 拼接 (應為 0)..."
SQL_FMT=$(grep -c "string.Format.*UPDATE\|string.Format.*SELECT\|string.Format.*INSERT\|string.Format.*DELETE" "$FILE" || true)
echo "    string.Format SQL 數量: $SQL_FMT"
if [ "$SQL_FMT" -eq 0 ]; then echo "    ✅ PASS"; else echo "    ❌ FAIL"; PASS=false; fi

# 2. 檢查參數化方法使用 (應為 N 處)
echo "[2] 檢查參數化方法使用..."
PARAMS=$(grep -c "SQLiteInsertUpdateDeleteParams\|GetDataTableParams" "$FILE" || true)
echo "    參數化方法數量: $PARAMS"
if [ "$PARAMS" -gt 0 ]; then echo "    ✅ PASS"; else echo "    ❌ FAIL"; fi

# 3. 檢查參數化語法 (應有 @param)
echo "[3] 檢查參數化語法..."
if grep -q "@param" "$FILE" || grep -q "@company_sid" "$FILE"; then echo "    ✅ PASS"; else echo "    ⚠️  無 @param 語法"; fi

# 4. 檢查審查報告
echo "[4] 檢查審查報告..."
if [ -f "<審查報告路徑>" ]; then echo "    ✅ PASS"; else echo "    ⚠️  不存在"; fi

echo ""
if [ "$PASS" = true ]; then echo "=== 全部通過 ✅ ==="; else echo "=== 有未通過項目 ❌ ==="; fi
```

## 注意事項
- `grep -c` 在無匹配時回傳 exit code 1，需用 `|| true` 避免腳本中斷。
- 驗證腳本放在 `/tmp/hermes-verify-*.sh`，驗證完成後 `rm -f` 清理。
- 檔案路徑需使用絕對路徑，避免工作目錄差異。

## 常見 SQL 注入模式
| 模式 | 危險等級 | 範例 |
|------|----------|------|
| string.Format WHERE | CRITICAL | `string.Format("SELECT ... WHERE x='{0}'", val)` |
| String.Format IN 拼接 | CRITICAL | `String.Format("WHERE id IN ({0})", ids)` |
| 表名拼接 | HIGH | `DELETE FROM {tableName}` |
| 欄位名拼接 | MEDIUM | 通常無法注入，但仍需注意 |
