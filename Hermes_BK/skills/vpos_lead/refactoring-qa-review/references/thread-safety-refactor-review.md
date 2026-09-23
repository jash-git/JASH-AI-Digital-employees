# Thread-Safety / Concurrency Refactor QA Review

Use when QA-reviewing an **atomic thread-safety refactor** (volatile flag, `lock(this)` serialization, collection-wrapper synchronization) — e.g. BulkObservableCollection `_suppressNotification` + `AddRange`/`ClearAndAddRange`. This is a different class than method-extraction/field-migration refactors; the structural pitfalls (A/B/C/D in the main skill) do not cover it.

## Checkpoints (verify each with grep, record command + result)

### 1. Volatile flag declaration
`grep -n '<flag>' <file>` → confirm the field is declared `volatile` and every read/write site is covered by that guarantee.
- FAIL if the flag is a plain `bool`/`int` written from one thread and read from another (torn read / visibility hazard).

### 2. lock(this) scope covers mutate + flag
`grep -cn 'lock (this)' <file>` → count must match expected serialized methods.
- The lock body must fully enclose **both** the base-collection mutation (`Add`/`Clear`/etc.) **and** all reads/writes of the suppression flag. A lock that wraps only the flag but not the `foreach Add` leaves the base collection exposed to concurrent readers.

### 3. Re-entrancy / deadlock check (the non-obvious one)
When a method body is wrapped in `lock(this)` and internally calls another method that may also touch shared state, verify those internal calls **do not themselves re-acquire the same monitor** (`lock(this)`).
- Default C# `Monitor`/`lock` is non-reentrant: a second `acquire` from the same thread deadlocks. A *recursive call* (calling your own method) does NOT deadlock — only a second explicit lock acquisition does.
- Example that is SAFE: `BulkObservableCollection.AddRange` holds `lock(this)` and calls `OnCollectionChanged(Reset)`; but `Add()`/`OnCollectionChanged()`/`Clear()` never themselves take `lock(this)`, so no recursive acquire → no deadlock. The single coalesced notification inside the lock matches design intent.
- FAIL if any method called inside the lock also declares `lock (this)` on a different code path reachable from there.

### 4. Background-thread bypass grep
Confirm NO background thread mutates the target collections outside the synchronized wrapper:
```bash
grep -rn '<targetCollection1>\|<targetCollection2>' VPOS_Avalonia/Thread/
```
- Expected: no matches. All legitimate mutations must go through `BulkObservableCollection.AddRange/ClearAndAddRange` (or, if on UI thread only, through `.Add()` in event handlers — which is fine because it's single-threaded).
- Also confirm SyncThread/PrintThread only touch print/order JSON, not the target collections.

### 5. Structural integrity
```bash
python3 -c "s=open('<file>').read(); print(s.count('{'), s.count('}'))"
```
- Braces must balance; no orphaned braces, bare method-name statements, or dangling lock blocks introduced by the edit.

## Notes (non-blocking, record but do NOT fail on)
- Call sites using `.Add()`/`.Clear()` individually instead of `AddRange()` are a future optimization opportunity, not a thread-safety defect — as long as they run on the UI thread.
- Pre-existing `catch { }` that swallows subscriber exceptions is out of scope unless this refactor introduced it.

## Decision
Record PASS only when all five checkpoints pass with grep evidence. If REJECTED, list each failing checkpoint with line numbers and return to vpos_ui for rework (Lead must NOT patch the source itself — see trap 26/27 in vpos-delegation-workflow).
