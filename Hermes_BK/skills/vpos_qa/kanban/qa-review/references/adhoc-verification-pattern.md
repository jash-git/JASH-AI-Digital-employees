# Ad-Hoc Verification Script Pattern for QA Reviews

## When to Use

After any code refactoring task, create a focused verification script at `/tmp/hermes-verify-TASK-XXX.sh` that:
1. Runs all DoD grep checks from the task description
2. Uses Python state machine for lock coverage (not simple grep -B)
3. Validates task_board.json JSON syntax and status fields
4. Confirms review report file exists
5. Outputs PASS/FAIL summary

## Template Script Structure

```bash
#!/usr/bin/env bash
# Ad-hoc verification for TASK-XXX: <description>

cd /media/sf_VPOS_Avalonia/VPOS_Avalonia   # adjust per project
PASS=0; FAIL=0; TOTAL=0

check() {
  local desc="$1"; shift
  TOTAL=$((TOTAL+1))
  if eval "$@" >/dev/null 2>&1; then
    echo "  ✅ $desc"
    PASS=$((PASS+1))
  else
    echo "  ❌ $desc"
    FAIL=$((FAIL+1))
  fi
}

echo "=== TASK-XXX Verification ==="
echo ""

# DoD checks — use check() for uniform positive/negative handling
check "File exists" "[ -f ToolLib/BitmapBase64_Funs.cs ]"
check "No old pattern (negative)" "! grep -q 'System\.Drawing' ToolLib/BitmapBase64_Funs.cs"
check "Has new pattern (positive)" "grep -q 'SixLabors\.ImageSharp' ToolLib/BitmapBase64_Funs.cs"

echo ""
echo "=== Results: $PASS/$TOTAL passed, $FAIL failed ==="

if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
```

### Library Migration Example (System.Drawing → ImageSharp)

```bash
#!/usr/bin/env bash
# Ad-hoc verification for TASK-019: System.Drawing.Common → SixLabors.ImageSharp migration
set -euo pipefail

cd /media/sf_VPOS_Avalonia/VPOS_Avalonia
PASS=0; FAIL=0; TOTAL=0

check() {
  local desc="$1"; shift
  TOTAL=$((TOTAL+1))
  if eval "$@" >/dev/null 2>&1; then
    echo "  ✅ $desc"
    PASS=$((PASS+1))
  else
    echo "  ❌ $desc"
    FAIL=$((FAIL+1))
  fi
}

echo "=== TASK-019 Ad-hoc Verification ==="
echo ""

# DoD: BitmapBase64_Funs.cs should have NO using System.Drawing;
check "BitmapBase64_Funs.cs: no 'using System.Drawing;'" \
  "! grep -q '^using System\.Drawing;' ToolLib/BitmapBase64_Funs.cs"

# DoD: BitmapBase64_Funs.cs should have SixLabors.ImageSharp using + type refs
check "BitmapBase64_Funs.cs: has 'SixLabors.ImageSharp' using" \
  "grep -q '^using SixLabors\.ImageSharp;' ToolLib/BitmapBase64_Funs.cs"

# DoD: csproj should have no System.Drawing.Common reference
check "VPOS_Avalonia.csproj: no 'System.Drawing.Common'" \
  "! grep -qi 'System\.Drawing\.Common' VPOS_Avalonia.csproj"

# DoD: CS_PrintTemplate.cs uses ImageSharp.Image.Load()
check "CS_PrintTemplate.cs: uses ImageSharp.Image.Load()" \
  "grep -q 'SixLabors\.ImageSharp\.Image\.Load' Models/CS_PrintTemplate.cs"

# Additional: intentional retention (DPI_Funs keeps System.Drawing)
check "DPI_Funs.cs: retains System.Drawing (Windows-only)" \
  "grep -q '^using System\.Drawing;' ToolLib/DPI_Funs.cs"

echo ""
echo "=== Results: $PASS/$TOTAL passed, $FAIL failed ==="

if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
```

## Key Pitfalls in Script Writing

### bash `((PASS++))` Returns Exit Code 1 When PASS=0
Post-increment returns the OLD value. When PASS=0, `((PASS++))` evaluates to 0 (falsy), causing `set -e` or `pipefail` to abort. Use `PASS=$((PASS+1))` instead.

### `grep -c` with `|| echo 0` Produces "0\n0" on No Match
When grep finds nothing, it exits with code 1 AND outputs "0". The `|| echo 0` adds another "0", giving "0\n0" which fails integer comparison. Use:
- `grep "pattern" file | wc -l` (always succeeds)
- OR `grep -c "pattern" file || true` (suppresses exit code, keeps output)

### Lock Coverage Needs Python State Machine for Nested IF/ELSE
Simple `grep -B1 "lock (_lock)" | grep "_sharedConnection.Query"` misses calls 2+ lines below the lock statement. Use a Python state machine that tracks `in_lock` flag across all lines.

## Cleanup

After verification passes, remove the script:
```bash
rm -f /tmp/hermes-verify-TASK-XXX.sh
```
