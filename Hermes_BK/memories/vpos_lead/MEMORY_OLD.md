VPOS 專案委派策略：
- 單一檔案 5+ 處修改 → vpos_lead 直接 patch（subagent 易迷失）
- 單一檔案 1-3 處修改 → 可委派 vpos_core
- QA 審查 → 委派 vpos_qa，效果良好
- 驗證：grep 確認修改結果，然後才派 QA
- .NET SDK 不可用：無法編譯，使用者最後驗收
- Ad-hoc 驗證：/tmp/hermes-verify-*.sh 腳本，驗證後 rm -f 清理
§
VPOS 專案技能: vpos-delegation-workflow (任務委派、監控、QA閉環SOP)
- 任務板: docs/task_board.json (JSON 格式)
- 問題表: review-reports/02_問題詳細說明與檔案對應表.md
- QA 審查: 委派 vpos_qa 效果良好，產出完整報告
- 編譯環境: /home/vblinux 無 .NET SDK，無法編譯