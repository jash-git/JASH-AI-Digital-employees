# Hermes 崩潰日誌地圖

崩潰診斷時，依序讀取以下檔案（都在 profile 目錄下）：

## agent.log
- 路徑：`~/.hermes/profiles/<profile>/logs/agent.log`
- 內容：每個 turn 的工具呼叫記錄、API 呼叫延遲、terminal 成功/失敗輸出。
- 怎麼用：**崩潰前最後一筆 `tool_executor: tool terminal completed` 的成功輸出**就是任務停下的位置。之後的 `timed out after Ns` = 卡死點。

## errors.log
- 路徑：同 logs/ 目錄。
- 內容：terminal 錯誤（exit_code -1 blocklist、-15 SIGTERM、超時）、CDP supervisor 連線失敗、cron fire-claim 遺失等 WARNING/ERROR。
- 怎麼用：找 `timed out after`（命令掛住）、`BLOCKED`（安全掃描擋下）、`connect failed`（瀏覽器/CDP 斷線）。這些是崩潰的直接前兆。

## gateway-exit-diag.log
- 內容：gateway 生命週期——每次 start / clean exit / non-zero exit / unclean exit 的 JSON 記錄，含 PID、記憶體、是否 OOM/SIGKILL。
- 怎麼用：確認 gateway 本身是「正常結束」還是「被強殺/OOM」。`suspected_oom` 欄位直接給答案。若此檔最後停留在很久以前但 gateway 進程還在，表示它可能卡在 drain/shutdown。

## gateway.log
- 內容：gateway 啟動/停止的 human-readable 記錄（profile、cron 排程、shutdown phase）。
- 怎麼用：確認 gateway 是否仍在運作、最後一次活動時間。若此檔最後停留在很久以前但 gateway 進程還在，表示它可能卡在 drain/shutdown。

## 快速命令
```bash
# 1. 排除 OOM
dmesg | grep -iE "killed process|out of memory|oom"

# 2. 崩潰前最後成功輸出（agent.log）
grep "tool terminal completed" ~/.hermes/profiles/<profile>/logs/agent.log | tail -3

# 3. 連續超時 / 卡死前兆（errors.log）
grep -E "timed out after|BLOCKED|connect failed" ~/.hermes/profiles/<profile>/logs/errors.log | tail -10

# 4. gateway 是否健康
ps aux | grep "[g]ateway run"
```