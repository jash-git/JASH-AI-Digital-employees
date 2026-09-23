---
task_board_name: <任務板名稱>
created_date: <YYYY-MM-DD>
task_type: new_feature | bug_fix | maintenance
created_by: vpos_lead
related_commits: <若已知，列出 commit hash>
status: IN_PROGRESS | DONE
---

# <任務板名稱>

## 背景與目標
<此任務板的開發背景、預期成果>

## 任務清單

- id: TASK-001
  title: <任務標題>
  type: new_feature | bug_fix  # 明確標註，供追溯機制使用
  assignee: vpos_core | vpos_ui | vpos_qa
  status: PENDING | REVIEW | REJECTED | DONE
  files_affected: [<修改的檔案路徑>]
  created_date: <YYYY-MM-DD>
  commit_hash: <完成後回填>
  description: <任務詳細說明>
  graphify_query: <執行過的 graphify query，供追溯用>

- id: TASK-002
  title: <任務標題>
  type: new_feature | bug_fix
  assignee: vpos_core | vpos_ui | vpos_qa
  status: PENDING
  files_affected: []
  created_date: <YYYY-MM-DD>
  commit_hash: <完成後回填>
  description: <任務詳細說明>
  graphify_query: <執行過的 graphify query>

## 追溯索引
| Task ID | 類型 | 建立日期 | 完成日期 | Commit Hash | 狀態 |
|---------|------|----------|----------|-------------|------|
| TASK-001 | new_feature | 2026-08-07 | | | PENDING |
