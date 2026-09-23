---
name: cs-compilation-errors
description: "Diagnose and fix C# compilation errors (CS0246, CS0103, CS1061, etc.) — missing using statements, wrong namespace, unresolved types, wrong API usage."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [csharp, compilation, build-errors, cs0246, cs0103, cs1061, using-statements]
---

# C# Compilation Error Resolution

## Overview

When a C# file fails to compile with "type or namespace not found" errors (CS0246) or "name does not exist in current context" errors (CS0103), the fix is almost always one of: missing `using` directive, wrong namespace, or unresolved assembly reference.

## When to Use

- CS0246: The type or namespace name 'X' could not be found
- CS0103: The name 'X' does not exist in the current context
- CS1061: 'Type' does not contain a definition for 'Member'
- Build succeeds but specific files show red squiggles

## Investigation Steps

### 1. Read the Error Message

Note the exact error code (CS0246, CS0103, CS1061) and the missing type/member name.

### 2. Find Where the Missing Type Is Defined

```bash
# Search for class/struct/interface definition
search_files --pattern "class TypeName" --path <project_root>

# If search times out on large project, narrow scope:
search_files --pattern "class TypeName" --file_glob "*.cs" --limit 10

# Or use grep directly:
grep -rn "class TypeName" --include="*.cs" .
```

### 3. Identify the Namespace

Read the file where the type is defined and note its `namespace` declaration (usually line 15-20).

### 4. Check Existing Using Statements in the Broken File

```bash
read_file <broken_file.cs> --limit 25
# Look at lines 1-20 for existing using directives
```

### 5. Determine What's Needed

| Scenario | Fix |
|----------|-----|
| Type is in a namespace already imported via `using` | No fix needed — check spelling/casing |
| Type is in a different namespace, same project | Add `using <namespace>;` |
| Type is in another assembly/project | Add `<ProjectReference>` or NuGet package |
| Static method from same file but different class | Ensure the class is accessible (public/static) and namespace is imported |
| Wrong API on a type (e.g., Dequeue on ConcurrentQueue) | Check the correct API for the type (see Pitfalls below) |

### 6. Patch Using Statements

Add missing using directives **after** existing project usings, before `namespace` declaration:

```csharp
using VPOS_Avalonia.Views;
using VPOS;                          // TypeName1, TypeName2, etc.
using VPOS_Avalonia.DBLib;           // TypeName3, TypeName4
using VPOS_Avalonia.ToolLib;         // TypeName5, TypeName6

namespace MyProject.ViewModels
```

**Best practice:** Add a comment listing the types that require each using, so future agents know why it's there.

### 7. Verify All References Are Covered

After adding usings, grep every usage of the previously-missing type in the broken file:

```bash
grep -n "TypeName" <broken_file.cs> | head -10
# Confirm all lines now resolve to the correct namespace
```

## Pitfalls

- **dotnet SDK not installed:** Many dev machines lack dotnet. Fall back to ad-hoc grep verification — confirm the using statement exists and that every type reference in the file is covered by an added using. Do NOT claim "build passes" without running `dotnet build`.
- **Same assembly, different namespace:** Types in the same project but different namespaces still need explicit `using` directives (unlike C++ headers).
- **Static members from MainWindow.axaml.cs:** Common pattern — static methods like `SerialCodeDataGet()` defined in `MainWindow` class require importing the containing namespace (`VPOS_Avalonia.Views`).
- **ToolLib/FileLib/DBLib classes:** These are common utility namespaces in VPOS projects. If you see `JsonClassConvert`, `LogFile`, `SQLDataTableModel`, etc., they live in `VPOS_Avalonia.ToolLib` and `VPOS_Avalonia.DBLib`.
- **Don't add duplicate usings:** Check if the namespace is already imported before patching.
- **CS1061 on LINQ methods (`.Where()`, `.Select()`, `.ToList()`):** Check if the file has `using System.Linq;`. Many VPOS files omit it because they pre-date LINQ.

### CS0122: Inaccessible due to protection level — prefer `internal` over `public` for same-assembly access

When a ViewModel (e.g., `MainWindowState`) in a different namespace needs to read/write UI control fields defined in `MainWindow.axaml.cs`, the default implicit `private` on those fields causes CS0122. Two options:

| Option | When to use |
|--------|-------------|
| `internal` | **Preferred** — same assembly, ViewModel-only access. No public API surface leak. |
| `public` | When a third-party library or separate assembly needs the member. |

Fix pattern (Avalonia code-behind):
```csharp
// Before: implicit private → CS0122 from MainWindowState.cs
BadgeButton VTSTOREBtn;

// After: explicit internal — accessible within same assembly, hidden externally
internal BadgeButton VTSTOREBtn;
```

**Verification:** After patching, grep every usage in the consuming file to confirm all references resolve. Do NOT add `public` unless a cross-assembly reference actually requires it.

### CS1061: Queue<T> vs ConcurrentQueue<T> — Dequeue() does not exist on ConcurrentQueue

`Queue<T>` and `ConcurrentQueue<T>` have DIFFERENT dequeue APIs — they are NOT interchangeable:

| Type | Dequeue method | Signature |
|------|---------------|-----------|
| `Queue<T>` | `Dequeue()` | `T Dequeue()` — returns item directly |
| `ConcurrentQueue<T>` | `TryDequeue(out T)` | `bool TryDequeue(out T item)` — returns success bool |

**Bug pattern:** Copy-pasting `Queue<T>` code into a `ConcurrentQueue<T>` field → `CS1061: 'ConcurrentQueue<T>' does not contain a definition for 'Dequeue'`.

**Fix:** Replace `.Dequeue()` with `TryDequeue(out T item)`, then adapt the consuming code:
```csharp
// Before (Queue<T> style — WRONG for ConcurrentQueue):
if (queue.Count > 0) {
    var item = queue.Dequeue();
    Use(item);
}

// After (ConcurrentQueue<T> style):
if (queue.TryDequeue(out var item)) {
    Use(item);
}
```

## Verification (Ad-Hoc)

When dotnet SDK is unavailable:

1. Confirm each added `using` line exists in the file ✅
2. Grep every previously-missing type name — all should now be covered by an existing using ✅
3. Check no duplicate usings were introduced ✅
4. File timestamp updated (edit actually saved) ✅

## Common C# Error Codes

| Code | Meaning | Typical Fix |
|------|---------|-------------|
| CS0246 | Type/namespace not found | Add `using` or assembly reference |
| CS0103 | Name doesn't exist in context | Add `using`, check spelling, verify scope |
| CS0234 | Namespace/type does not exist | Wrong namespace, missing project ref |
| CS1061 | Member doesn't contain definition | Check type, add using, verify static/instance, check correct API |
| CS0122 | Inaccessible due to protection level | Change `private` → `public`, or add accessor |
