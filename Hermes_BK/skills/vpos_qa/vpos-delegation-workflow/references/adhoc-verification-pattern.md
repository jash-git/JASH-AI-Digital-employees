# Ad-hoc 靜態驗證模式

## 情境
當環境中無 .NET SDK 可執行 `dotnet build` 時，用 bash 腳本做靜態驗證。

## 標準流程
1. 寫驗證腳本到 `/tmp/hermes-verify-*.sh`
2. 檢查項目：
   - 原始問題字串數量（應為 0）
   - 修復後字串數量（應 >= N）
   - 檔案存在與時間戳記
3. 執行 `bash /tmp/hermes-verify-*.sh`
4. 清理：`rm -f /tmp/hermes-verify-*.sh`

## 範例：SQL 注入修復驗證
```bash
#!/bin/bash
FILE="<目標檔案>"
# 1. 無 String.Format SQL (應為 0)
COUNT=$(grep -c "String\.Format.*WHERE" "$FILE" || echo "0")
# 2. 有參數化 @ids (應 >= 3)
IDS=$(grep -c "IN @ids" "$FILE" || echo "0")
# 3. 有 Split+int.Parse (應 >= 3)
SPLIT=$(grep -c "Split.*int.Parse" "$FILE" || echo "0")
echo "PASS: $COUNT format, $IDS @ids, $SPLIT split"
```

## 注意事項
- `grep -c` 無匹配時回傳 exit code 1，需 `|| echo "0"` 避免腳本中斷。
- 腳本名必須有 `hermes-verify-` 前綴。
- 驗證完成後務必 `rm -f` 清理。
