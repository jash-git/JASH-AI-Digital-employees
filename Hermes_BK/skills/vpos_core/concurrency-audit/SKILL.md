---
name: concurrency-audit
description: Audit C# SQLite codebases for thread-safety bugs.
tags: [vpos-avalonia, concurrency, sqlite, performance, audit]
---

# Concurrency Anti-Pattern Audit (C# / .NET + SQLite + background threads)

Use when asked to analyze a codebase for thread-safety problems under high-frequency multi-threaded access — e.g. "what could break when many threads hit the DB at once". Produces a diagnostic report (NOT fixes). Fixes are separate skills: `sqlite-data-access-pooling`, `refactoring-qa-review`.

## When to use this vs. others

- This skill = **diagnose** the class of problems across the whole codebase.
- `sqlite-data-access-pooling` = **fix** one file's per-call connection pattern.
- `refactoring-qa-review` = **verify** a fix after it lands.
- Do NOT use this to fix code — only to find and report. Hand findings to subagents via the project delegation workflow.

## Workflow

### 1. Map the concurrency surface (grep, not read-everything)
Read the data-access layer fully first (`DBLib/SqliteDataAccess.cs`, `DBLib/SQLDataTableModel.cs`), then grep for anti-patterns across the tree:
- bool-flag "locks": `grep -rnE 'volatile bool m_bln' --include=*.cs`
- enqueue→dequeue-one: `grep -rnE 'TryDequeue\(out ' --include=*.cs`
| Per-call connection open without `using` / with `Close()` not `Dispose()` | `grep -rnE 'new SQLiteConnection' --include=*.cs` then check for `using (` and `.Dispose()` |
| Missing `Busy Timeout` in connection string (WAL present but no busy_timeout) | `grep -nE 'Data Source' <DB files>` — inspect each connection string's components; WAL + shared cache do NOT imply a busy_timeout clause is present |
- shared static mutable collections: `grep -rnE 'public static (List|Dictionary|ObservableCollection)\s+<[^>]+>\s+m_' --include=*.cs`
- blocking HttpClient: `grep -rnE '\.GetAwaiter\(\)\.GetResult\(\)|\.Wait\(\)' --include=*.cs`
- cross-thread UI collection mutation: `grep -rnE 'ObservableCollection|AddRange' --include=*.cs`
- disk I/O inside a lock: read methods containing both `lock (` and `new FileStream`/`StreamWriter`

### 2. Identify the threads that touch shared state
Find background loops and their shared targets:
- Background thread entry points: `grep -rnE 'ThreadMain|new Thread|Task.Run|while\s*\(' --include=*.cs`
- The gate flag (`m_blnWait`) and every place it is set true/false — a bool used as a mutex is the #1 suspect.
- Static mutable fields read/written by more than one thread (UI UIThread + background threads).

### 3. Rank each finding by severity
Use the rubric in `references/vpos-avalonia-concurrency-antipatterns.md`:
- 🔴 P0 — data integrity / locking collapse (lost writes, `database is locked`, torn reads on shared collections)
- 🟠 P1 — performance/stability under load (socket exhaustion, cross-thread UI crashes, lock-free DB bypass)
- 🟡 P2 — leaks / bottlenecks (unbounded queues, disk I/O in critical section, init-order races)
- ⚪ P3 — consistency hardening (overloads missing the gate flag)

### 4. Write the report (standardized shape)
Every finding MUST have: **File + Line(s) + Problem explanation + Solution**. Structure:
1. Severity-ranked summary table (#, severity, core problem, files)
2. Per-issue detail with exact line numbers and code evidence
3. Phased roadmap mapping findings → tasks → responsible subagent (`vpos_core` for data/network layer, `vpos_ui` for UI-binding layer)
4. QA gate note: each phase verified by `refactoring-qa-review` + xUnit concurrent stress test before next phase.
Save to `review-reports/<topic>-report.md` (e.g. `multithreading-analysis-report.md`).

## Pitfalls

### Don't trust a single grep count as proof
A count like "50 static Lists" is evidence of scope, not proof of a defect. Read the actual code to confirm whether they're truly shared across threads and unsynchronized before writing it into the report.

### Distinguish two-lock / no-lock data layers
In this project `SqliteDataAccess` locks with `_lock` but `SQLDataTableModel` uses none — different or absent locks mean cross-layer access is NOT mutually exclusive. Call this out explicitly; it compounds the defect.

### A bool flag used as a mutex is not a mutex
`volatile bool m_blnWait = true/false` set at method entry and cleared at exit does NOT prevent two threads from entering simultaneously, and clearing unconditionally at the end (even when work remains) lets later readers proceed prematurely. Report it as P0.

### Blocking HttpClient on a background loop is a load problem, not just a style one
A single static `HttpClient` is correct; `.GetAwaiter().GetResult()` blocking it while several external-platform fetches run concurrently exhausts the connection limit → false network failures + stalled sync loop. Report as P1 with the async fix.

### Verify line numbers against real reads, not just grep
grep gives candidate lines; read enough context to confirm the defect actually occurs there before citing a specific number in the report. Fabricated or off-by-N line numbers make the report useless for handoff.

## Reference Files
See `references/`:
- `vpos-avalonia-concurrency-antipatterns.md` — grep detection signatures, inventory of known defects (file:line→fix), severity rubric, and standardized report format. Reuse as a checklist for future audits on this project or similar C#/.NET + SQLite codebases.
