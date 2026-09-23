---
name: csharp-collection-migration
description: Migrate non-generic .NET collections (Queue, ArrayList, Hashtable) to generic equivalents in C# codebases. Covers Queue→ConcurrentQueue<T>, ArrayList→List<T>, Hashtable→Dictionary<K,V>.
tags: [csharp, refactoring, generics, vpos-avalonia]
---

# C# Collection Migration — Non-generic → Generic

## Scope
Migrate legacy non-generic `System.Collections` types to their generic equivalents. Common in older C# codebases (especially VPOS Avalonia).

## Patterns

### Pattern 1: Queue[] → ConcurrentQueue<object>[]

**When**: A queue array stores multiple types (e.g., both `PT_CommandOutput` and `PrintData`).

| Step | Action |
|------|--------|
| 1 | Replace field: `public static Queue[] m_Queue;` → `public static ConcurrentQueue<object>[] m_Queue;` |
| 2 | Replace array init: `m_Queue = new Queue[FIFOSIZE];` → `new ConcurrentQueue<object>[FIFOSIZE]` |
| 3 | Replace element init: `m_Queue[i] = new Queue();` → `new ConcurrentQueue<object>()` |
| 4 | Replace `.Count > 0`: use `.IsEmpty` (ConcurrentQueue has no Count in .NET Framework) |
| 5 | Replace `.Dequeue()`: use `.TryDequeue(out object obj)` + cast |
| 6 | `.Enqueue()` API unchanged — same signature for `ConcurrentQueue<T>` |

**Critical pitfalls**:
- **No `.Count` property** in older .NET — use `.IsEmpty` instead. In .NET 6+ `Count` exists but is approximate (returns lower bound).
- **`.Dequeue()` throws** if empty — always use `.TryDequeue(out object obj)` which returns bool.
- **Multi-type queues**: declare as `<object>`, cast on dequeue. The lock around TryDequeue is still recommended for the outer logic flow.

```csharp
// ❌ Old
if (m_Queue[intIndex].Count > 0) {
    PT_CommandOutputs = (PT_CommandOutput)m_Queue[intIndex].Dequeue();
}

// ✅ New
if (!m_Queue[intIndex].IsEmpty) {
    if (m_Queue[intIndex].TryDequeue(out object obj)) {
        PT_CommandOutputs = (PT_CommandOutput)obj;
    }
}
```

### Pattern 2: ArrayList → List<string> (or appropriate type)

**When**: An `ArrayList` stores a single known type.

| Step | Action |
|------|--------|
| 1 | Replace declaration: `ArrayList AL = new ArrayList();` → `List<T> AL = new List<T>();` |
| 2 | `.Add()`, `.Count`, `.Remove()` — API identical for same-type items |
| 3 | Remove unused `using System.Collections;` |

**Critical pitfalls**:
- **Type safety**: determine the actual element type from usage. If adding strings, use `List<string>`. Don't guess — grep all `.Add(...)` calls to confirm types.
- **API compatibility**: verify downstream callers accept `List<T>` (not just `IList` or `ArrayList`). In VPOS, `VTEAMQrorderAPI.update_print_queue_data()` was already updated to accept `List<string>`.

### Pattern 3: Hashtable → Dictionary<K,V>

**When**: A `Hashtable` stores key-value pairs with known types.

| Step | Action |
|------|--------|
| 1 | Replace field: `Hashtable ht = new Hashtable();` → `Dictionary<K, V> ht = new Dictionary<K, V>();` |
| 2 | `.Add(key, value)` — same signature |
| 3. `.ContainsKey(key)` — same method name |
| 4 | `.[key]` indexer — same syntax but returns typed value (no cast needed) |
| 5 | Remove `using System.Collections;` if no longer needed |

## Verification Checklist (DoD)

Write a `/tmp/hermes-verify-*.sh` script:

```bash
#!/usr/bin/env bash
BASE="/path/to/project"
PASS=0; FAIL=0

check_eq() { local desc="$1" exp="$2" act="$3"; [ "$exp" = "$act" ] && echo "✅ $desc: '$act'" && PASS=$((PASS+1)) || echo "❌ $desc: expected='$exp' got='$act'" && FAIL=$((FAIL+1)); }
check_ge() { local desc="$1" thr="$2" act="$3"; [ "$act" -ge "$thr" ] && echo "✅ $desc: '$act' >= $thr" && PASS=$((PASS+1)) || echo "❌ $desc: '$act' < $thr" && FAIL=$((FAIL+1)); }

# Pattern 1 checks
check_eq "No new Queue()" "0" "$(grep -cE 'new Queue\(\)' "$BASE/Target.cs" || true)"
check_ge "ConcurrentQueue refs (≥3)" 3 "$(grep -c 'ConcurrentQueue<object>' "$BASE/Target.cs")"
check_eq "No .Dequeue() calls" "0" "$(grep -c '\.Dequeue(' "$BASE/Target.cs" || true)"
check_ge "TryDequeue usages (≥2)" 2 "$(grep -c 'TryDequeue' "$BASE/Target.cs")"

# Pattern 2 checks
check_eq "No ArrayList refs" "0" "$(grep -c 'ArrayList' "$BASE/Target.cs" || true)"
check_ge "List<string> present (≥1)" 1 "$(grep -c 'List<string>' "$BASE/Target.cs")"

echo "RESULT: $PASS passed, $FAIL failed"
exit "$FAIL"
```

## Using Statement Cleanup

After migration, verify `using System.Collections;` is no longer needed:
- If the file only uses `System.Collections.Generic`, remove it
- If using `ConcurrentQueue<T>`, replace with `using System.Collections.Concurrent;`
- Never leave unused `using System.Collections;` in a file that's been fully genericized

## Environment Notes

- **No .NET SDK?** Use grep-based static verification (see Ad-hoc Verification Pattern skill)
- **.NET Framework vs .NET Core/6+:** `ConcurrentQueue<T>.Count` exists in .NET 6+ but is approximate. Prefer `.IsEmpty` for consistency across versions.
