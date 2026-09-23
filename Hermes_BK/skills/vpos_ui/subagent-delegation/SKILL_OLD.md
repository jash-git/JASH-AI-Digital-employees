---
name: subagent-delegation
description: Managing subagent delegation, cron monitoring, and manual progress checks in CLI environments.
---

# Subagent Delegation & Monitoring

派單給子代理後，必須建立 Cron 監控排程，這是鐵律。

## 核心流程

1. **派遣子代理** → `delegate_task()` 取得 `delegation_id`
2. **立即建立 Cron 監控** → `cronjob(action='create', schedule='every 3m', repeat=10)`
   - 監控內容：檢查子代理狀態、檔案修改痕跡、是否卡死
   - 連續 3 次（約 9 分鐘）無進度 → 終止並重新派遣
3. **手動檢查（備援）** → 當 Cron 回報無法到達時

## 手動檢查子代理進度的模式

當 Cron 回報無法自動送達時（CLI/TUI 環境限制），改用以下模式：

### 步驟 1：檢查檔案修改痕跡
```bash
ls -la <target_file>          # 比對修改時間與大小
git status <target_file>      # 確認是否有未提交修改
```

### 步驟 2：比對檔案大小變化
- 原始大小 vs 目前大小
- 行數變化
- 若檔案大小/時間有變化 → 子代理正在執行
- 若檔案無變化超過 10 分鐘 → 可能卡死

### 步驟 3：讀取修改後的程式碼
```
read_file(path, offset=行號, limit=30)
```
確認修復內容是否符合預期。

## CLI 環境限制

⚠️ **CLI/TUI 環境的 Cron deliver='origin' 不會自動推送回報！**

- `deliver='origin'`（預設）在 Telegram/Discord 等聊天平台會推送
- 但在 CLI/TUI 環境，回報僅儲存在本地，不會顯示在終端
- 解決方案：
  1. 手動回覆詢問進度（「進度？」）
  2. 將 Cron 改為 `deliver='telegram'` 或 `deliver='all'`（需有連接的聊天平台）
  3. 手動執行 `cronjob(action='list')` 查看狀態

## 監控排程設定建議

- **頻率**: `every 3m`（每 3 分鐘）
- **次數**: `repeat=10`（總計 30 分鐘，覆蓋一般修復時間）
- **CRITICAL 修復**: 建議 `repeat=20`（60 分鐘）
- **HIGH/MEDIUM 修復**: `repeat=10` 即可
- **LOW 修復**: 可考慮不建立 Cron，手動檢查即可

## 卡死判定標準

| 條件 | 判定 |
|------|------|
| 檔案無修改超過 10 分鐘 | 可能卡死 |
| 子代理無回報且 Cron 連續 3 次無變化 | 確認卡死 |
| 檔案修改但內容無實質變化 | 可能無效執行 |

卡死時：終止子代理（如有方法）或重新派遣並更新 prompt 加入更明確的步驟。

## 完成確認

子代理完成後：
1. 讀取修改後的檔案確認修復內容
2. 標記 todo 為完成
3. 通知使用者進行編譯與驗收
4. 刪除或暫停對應的 Cron 監控排程
