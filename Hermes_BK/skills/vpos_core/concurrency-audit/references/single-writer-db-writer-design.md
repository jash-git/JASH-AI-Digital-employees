# Single-Writer DB Queue Design (replacing bool-mutex writes)

Design guidance for fixing the F1/F5/F10 anti-patterns in VPOS Avalonia: replacing the `m_blnWait` bool mutex + enqueue→dequeue-one pattern with a dedicated single-writer thread. Captured from TASK-028 (Phase 1a, 2026-09-17). The audit skill (`concurrency-audit`) finds these; this file is how to design the fix.

## Core model change

All `SQLiteInsertUpdateDelete*` overloads become **pure Enqueue** (fire-and-forget); a single dedicated writer thread drains `m_SQLDBQueue` and `m_SQLQueue` in order, each statement wrapped in `lock(SharedDbLock)` + transaction. Remove: the bool gate at method entry/exit, the inline `TryDequeue` inside each write function, and the UI-timer drain block (`MainWindow.axaml.cs`).

### Micro-step decomposition (each ≤10 min / one cron tick)
1. Create a new `DBWriter.cs` in `DBLib/`: dedicated writer thread with `Start()`/`Stop()`, a drain loop (`while(m_blnRunLoop){ if(!q.IsEmpty) q.TryDequeue(...); Thread.Sleep(10); }`), and per-statement transaction under `SharedDbLock`. Pure infrastructure — changes no existing call behavior yet.
2. Wire `DBWriter.Start()` / `Stop()` into app startup/shutdown (must start before any Enqueue can occur).
3. Convert each write overload to pure Enqueue, deleting its gate + inline dequeue body one at a time.
4. Remove the bool gate from every reader/writer that set it (`GetDataTable(Database,...)`, `GetDataTableParams(Database,...)` — F10 consistency hardening: remove gate from ALL overloads uniformly).
5. Remove the self-counting auto-reset logic in the background loop (`SyncThread.cs` m_intWaitCount block).
6. Delete the UI-timer drain block.
7. Finally remove/retire the `m_blnWait` declaration once grep confirms zero remaining reads.

## The critical correctness decision: write-then-read hotspots

**Problem:** Some functions do a write and then immediately read the same table in the same call, e.g. `promotion_dataLoad()` (SQLDataTableModel.cs ~L944-951):
```csharp
SQLiteInsertUpdateDelete(SQL);   // UPDATE promotion_data SET start_time='1970-01-01' WHERE start_time=''  (normalize empty dates)
...
promotion_DataTable = GetDataTable(SQL);  // SELECT the table just updated
```
After converting writes to fire-and-forget, the SELECT may run before the UPDATE commits → reads stale/normalized data. In this case the empty-string date would still be present and trigger `string '' was not recognized as a valid DateTime` (the very error the UPDATE is meant to prevent) → login crash or corrupted load.

**Three options — pick option 2:**

- **Option 3 (GetDataTable flushes pending writes before read) — REJECT.** Looks most complete but reintroduces exactly the coupling we are removing: every read blocks until all writes commit, which is a bool-gate in disguise. GetDataTable is called dozens of times during login/load, so this kills read performance and risks writer↔UI deadlock. Violates TASK-028's core goal (decouple, non-serial).

- **Option 1 (accept + annotate only) — REJECT.** Not a minor/scale issue: the normalization UPDATE is idempotent but its *absence* at read time is a real correctness bug (crash on empty-string date). Annotating does not fix it.

- **Option 2 (make the hotspot write synchronous) — CORRECT, safest + most maintainable.** Add an explicit synchronous variant `SQLiteInsertUpdateDeleteSync(...)` that executes inline (no queue) and use it ONLY in the known write-then-read hotspots. The load-time normalization writes then run on the same thread before the read → ordering guaranteed by construction. ~95% of writes stay fire-and-forget; only the single known hotspot stays synchronous, and future developers see an *explicit* sync call rather than relying on hidden global-queue ordering (explicit beats implicit).

**Why option 2 wins:** The load-time normalization path is not high-frequency (it runs at login/load), so flushing there has negligible performance impact. It preserves correctness without reintroducing a read-side coupling or deadlock risk.

## DoD greps for this fix
- `grep m_blnWait` → only unrelated `m_blnWaitAuthorization*` remains in other files; zero DB-mutex uses left.
- `grep TryDequeue` → only the new DBWriter drain loop references the queues.
- Queues drained from exactly one place (the writer thread), not multiple points.

## Related project conventions (from vpos-delegation-workflow)
- Route this work to `vpos_core` (DBLib/Thread/Views data layer). Never edit the code yourself — Lead hands fixes back to the developer; QA (`vpos_qa`) verifies after.
- Each micro-step is a separate delegate_task with exact file:line context pre-loaded. Cron watchdog every 3m, repeat=10 for this class of large refactor.
- After all patches on the task: notify user to compile-verify before moving on (do NOT batch multiple tasks).
