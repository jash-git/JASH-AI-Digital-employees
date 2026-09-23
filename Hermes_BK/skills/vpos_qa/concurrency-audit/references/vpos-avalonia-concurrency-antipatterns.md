# VPOS Avalonia — Concurrency Anti-Pattern Inventory (Audit Reference)

Condensed knowledge bank of thread-safety defects found during the 2026-09-15 audit. Use as a grep checklist for future audits on this project or similar C#/.NET + SQLite + background-thread codebases.

## Detection patterns (grep signatures)

| Anti-pattern | grep signature |
|---|---|
| bool-flag "lock" (`volatile bool` used as mutex) | `grep -rnE 'volatile bool m_bln' --include=*.cs` |
| Enqueue-then-immediately-dequeue-one (silent SQL loss) | `grep -rnE 'TryDequeue\(out ' --include=*.cs` |
| Per-call connection open without `using` / with `Close()` not `Dispose()` | `grep -rnE 'new SQLiteConnection' --include=*.cs` then check for `using (` and `.Dispose()` |
| Static mutable collections shared across threads | `grep -rnE 'public static (List|Dictionary|ObservableCollection)\s+<[^>]+>\s+m_' --include=*.cs` |
| Blocking HttpClient calls | `grep -rnE '\.GetAwaiter\(\)\.GetResult\(\)|\.Wait\(\)' --include=*.cs` |
| Cross-thread ObservableCollection mutation | `grep -rnE 'ObservableCollection|AddRange' --include=*.cs` |
| Disk I/O inside a lock critical section | read methods containing both `lock (` and `new FileStream`/`StreamWriter` |

## Known defects (file:line → fix)

- **SyncThread.cs:24** — `m_blnWait` bool flag is one-way throttle, not mutual exclusion. Fix: replace with SemaphoreSlim(1,1) or Mutex; add `PRAGMA busy_timeout=5000`.
- **SQLDataTableModel.cs:162-247** — `SQLiteInsertUpdateDelete` enqueue→dequeue-one pattern; `m_blnWait=false` set unconditionally at end even when queue non-empty. Fix: single writer thread + BlockingCollection (bounded).
- **SqliteDataAccess.cs:671-723** — ~50 `public static List<T>` with no sync; two data-access layers use different/absent locks. Fix: DbCache + ReaderWriterLockSlim, assign via new-reference swap.
- **SQLDataTableModel.cs:93-120 (+10 sites)** — `new SQLiteConnection()` per call, `Close()` not `Dispose()`, no try-finally. Fix: `using` wrapper or shared connection behind gate.
- **SqliteDataAccess.cs:507-550** — `terminal_dataLoad()` skips `lock(_lock)` (only method that does). Fix: add lock / route through same gate.
- **HttpsFun.cs:155 + 10 blocking sites** — static HttpClient correct, but `.GetAwaiter().GetResult()` blocks SyncThread; concurrent external-platform fetches exhaust connection limit. Fix: `await SendAsync().ConfigureAwait(false)` + retry/backoff.
- **BulkObservableCollection.cs:24-45** — AddRange mutates UI collection off UIThread; `_suppressNotification` not volatile. Fix: marshal to `Dispatcher.UIThread.InvokeAsync`.
- **LogFile.cs:41-93** — disk I/O inside ReaderWriterLockSlim critical section serializes all logging on every SQL record. Fix: background writer + BlockingCollection or shared stream.
- **PrintThread.cs:67-97** — `m_intQueueSequence = new int[FIFOSIZE]` depends on FIFOSIZE set first; no ordering guarantee. Fix: single Init() with lock / static constructor.
- **SyncDBData.cs bulk get_* methods** — each INSERT opens its own connection+transaction. Fix: batch into one transaction per sync pass.

## Severity rubric (for ranking findings)

- 🔴 P0 — data integrity / locking collapse (lost writes, `database is locked`, torn reads on shared collections)
- 🟠 P1 — performance/stability under load (socket exhaustion, cross-thread UI crashes, lock-free DB bypass)
- 🟡 P2 — leaks / bottlenecks (unbounded queues, disk I/O in critical section, init-order races)
- ⚪ P3 — consistency hardening (overloads missing the gate flag)

## Report format (standardized)

Each finding = **File + Line(s) + Problem explanation + Solution**. Output as severity-ranked table + per-issue detail + phased roadmap. Save to `review-reports/<topic>-report.md`. See SKILL.md for full methodology.
