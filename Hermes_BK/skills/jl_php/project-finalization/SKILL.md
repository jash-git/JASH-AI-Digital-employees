---
name: project-finalization
description: Finalize completed multi-agent projects with cleanup.
version: 0.1.0
author: jl_lead, Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [project-management, closure, cleanup, deployment, kanban]
    related_skills: [kanban-orchestrator, sdlc-review, deployment-checklist]
---

# Project Finalization — Closing Out a Completed Multi-Agent Dev Project

> Use when every task on the board is DONE/completed and the user says "接續最後未完成工作 / 繼續推進" but nothing obvious remains. The remaining work is **finalization, not development**: remove subagent pollution, retire watchdog cron jobs, update docs + regenerate the knowledge graph, then verify deployment health.

## When to use this skill

- Task board shows all tasks DONE/completed (no pending/REJECTED items).
- User asks to resume / continue but there is no new feature to build.
- You suspect leftover test/debug files from subagent work.
- A project just passed QA and needs a clean handoff to the user.

## The trap: "all DONE" usually means finalization remains

Subagents (jl_ui, jl_php, jl_qa) routinely leave throwaway files that never appear in any work order. If you stop at "all tasks DONE," you ship a dirty workspace. Run the cleanup sequence below before reporting closure.

## Procedure

### Step 1 — Verify the board against reality
Read `docs/task_board.json` and `review-reports/issue-log.md`. Confirm every task is DONE/completed. If any is REJECTED or stuck, that is the real remaining work — route it back to the implementer (do NOT finalize).

### Step 2 — Find and remove subagent pollution
Check two locations:
- **Deploy target** (e.g. `/var/www/html/`): test HTML pages, debug dumps, `tmp_*` files. Often owned by `root` → needs `sudo rm -f`. Verify each file is orphaned (no reference in `src/`, `docs/`, or the graph) before deleting.
- **Source tree root** (`src/` or project root): orphaned verification scripts (`verify_*.py`, `test_*.js`, stray `.html`). Delete from source too, or they re-sync into every future deploy via rsync/copy.

Enumerate with `search_files(pattern='tmp_*|verify_*|lunar_test*', target='files')`, then confirm no references with a content grep before deleting. Only delete files that are truly orphaned (no import/reference anywhere).

### Step 3 — Retire watchdog cron jobs
Every dispatched subagent spawned a 3-minute watchdog cron job. When the project is DONE, remove ALL of them via `cronjob_manage(action='remove', job_id=...)`. A completed project should have zero active watchdogs. List first with `cronjob_manage(action='list')` to collect every job_id.

### Step 4 — Update docs + regenerate graph
- Record the cleanup in `review-reports/issue-log.md` (new "結案清理" section: what was deleted, how verified).
- Bump task-board notes to drop stale lines like "subagent cleaned up test files."
- Run `graphify . --code-only` then `graphify cluster-only` so the knowledge graph reflects pruned files (`graphify-out/GRAPH_REPORT.md` timestamp updates).

### Step 5 — Verify deployment health (do not skip)
Before telling the user it is done, confirm:
- Source tree root has no orphaned scripts left.
- Deploy-target HTML list matches exactly what `src/public/` serves (no stray test/debug pages).
- Zero active cron watchdog jobs remain.
- API smoke test returns expected values for the canonical test input (e.g. correct shengxiao / pillars / day-master).
- Frontend HTTP 200 + key containers render (`headless Chrome --dump-dom` or `curl`).
- Deployed file md5 matches source; permissions are `644 www-data:www-data`, dirs `755`.

See `references/finalization-checklist.md` for the exact command recipes and a worked example from the suanming-clone project.

## Pitfalls

**Root-owned pollution cannot be auto-deleted.** The sudo gate blocks autonomous deletion of files owned by root in `/var/www/html`. If a subagent reports "cleanup done" but you still find root-owned test files present, the cleanup did NOT actually complete — re-run it yourself with `sudo rm -f` (expect an approval prompt; proceed since it is a known orphan).

**Never trust a subagent's self-report of a destructive operation.** Verify the artifact is gone by listing the directory after deletion. A deleted-file claim is only true when you see the empty list.

**Don't delete files that are legitimately in `src/public/`.** Some debug/test pages (e.g. `debug-baz.html`) may exist in both source and deploy. Decide deliberately: if it is not part of any work order's deliverable, remove from BOTH; if it is a real deliverable, keep both.

**Stale task-board notes mislead future sessions.** A note saying "subagent cleaned up" becomes false after you clean manually. Update or remove it so the next resume session doesn't re-investigate.

## Verification checklist before declaring closure
- [ ] Source tree root: no `tmp_*` / orphaned verification scripts (grep confirmed zero references).
- [ ] Deploy target HTML list == exactly what `src/public/` should serve.
- [ ] Zero active cron watchdog jobs remain (`cronjob_manage list`).
- [ ] API smoke test returns expected values for canonical input.
- [ ] Frontend HTTP 200 + key containers render.
- [ ] Deployed file md5 matches source; permissions correct (644 / 755, www-data).
- [ ] `issue-log.md` records the cleanup; task-board notes updated.
- [ ] `graphify-out/GRAPH_REPORT.md` timestamp is recent and reflects pruned files.