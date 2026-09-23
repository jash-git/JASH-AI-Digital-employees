# Task Board Lifecycle Pattern (TASK-009 教訓)

## Problem
task_board.json was missing TASK-009 entry because it was only updated AFTER QA PASS, not at analysis time. Future sessions would repeat this gap.

## Solution: Three-Phase Lifecycle

### Phase 1 — Initialization (Step 0.5, before dispatching)
**When**: Graphify complete → before first delegate_task call
**Action**: Read `docs/task_board.json`, create task entry if missing
```json
{
  "id": "TASK-XXX",
  "title": "<short title>",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "assignee": "vpos_core|vpos_ui|vpos_qa|vpos_lead",
  "status": "IN_PROGRESS",
  "description": "<detailed description>",
  "files": ["<file paths>"],
  "issue_ref": "<issue reference>"
}
```
**Verify**: `python3 -c "import json; d=json.load(open('docs/task_board.json')); assert 'TASK-XXX' in [t['id'] for t in d.get('tasks',[])]"`

### Phase 2 — Subagent Update (during execution)
**When**: Subagent completes work, before QA review
**Action**: Subagent updates status to `REVIEW` with verification evidence (ls -la + grep results)
**Dispatch reminder**: "完成後請將 task_board.json 中 Task 狀態更新為 REVIEW，並附上 ls -la 與 grep 實體寫入驗證結果。"

### Phase 3 — Final Update (after QA PASS, before user notification)
**When**: vpos_lead QA PASS → before notifying user
**Action**: Update status to `DONE`, add qa_review="PASS", qa_review_file path, completed_date
**Also update**: `last_updated` field to current date (YYYY-MM-DD)
**Backup**: task_board.json 是專案可重生成物，更新後**不觸發 Hermes_BK 備份**（依 vpos-delegation-workflow §0.5 備份觸發鐵律：僅在 skill/memory/SOUL/config/cron 等系統資料異動時才備份）

## Common Pitfalls
- **TASK-009 gap**: Only updating at Phase 3 means the task is invisible during execution. Always initialize at Phase 1.
- **Duplicate entries**: Check if task already exists before creating. Don't add duplicates.
- **Stale last_updated**: Must be updated on every change, not just initial creation.

## Applicable To
Any project with a task_board.json or similar tracking file. The three-phase pattern (IN_PROGRESS → REVIEW → DONE) is universal for agent-managed workflows.
