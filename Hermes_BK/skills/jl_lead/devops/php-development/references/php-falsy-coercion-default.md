# PHP Falsy-Coercion Default Bug (reproduction + fix)

**Class**: Silent data bug from `?:` fallback on numeric fields where `0` is valid.
**First observed**: 2026-09-12, suanming project (`src/api/bazireport.php`).

## The trap

```php
$hour = filter_var($_POST['hour'] ?? null, FILTER_VALIDATE_INT,
    ['options' => ['min_range' => 0, 'max_range' => 23]]) ?: 12;
```

`filter_var('0', ...)` returns integer `0`. Then `0 ?: 12` evaluates to `12` because
`0` is falsy in PHP. A legitimately-submitted `0` (e.g. hour=0 = 子時 / midnight)
silently becomes the default `12`. No error, no warning — just wrong output downstream.

## Why it's dangerous here

In a BaZi (八字) calculator, `hour=0` feeds `computePillars()` → `hourGanZhi()`, which
drives the 時柱 (hour pillar), 命宮 (life palace), and 身宮 (body palace). All three came
out wrong for anyone born in the 子時 / 丑時 window.

## Reproduction recipe

```bash
# Same input, every hour returns identical hour pillar — red flag:
for h in 0 3 6 9 12 15 18 21; do
  curl -s -X POST 'http://localhost/api/bazireport.php' \
    --data "year=1981&month=5&day=2&hour=$h" | \
    python3 -c "import sys,json;d=json.load(sys.stdin)['data'];p=d['pillars'][3];print('hour=%2s -> %s%s'%( $h,p['gan'],p['zhi']))"
done
# hour=0 and hour=1 both return 壬午 (the hour=12 result) instead of their own pillars.
```

## Fix

Use an explicit null/`=== false` check — never `?:` for numeric defaults:

```php
$h = $_POST['hour'] ?? null;
if ($h === null || !is_int($h)) { $h = 12; }   // default only when absent/invalid
// $h is now the real submitted value, including 0
```

Or with filter_var:

```php
$h = filter_var($_POST['hour'] ?? null, FILTER_VALIDATE_INT,
    ['options' => ['min_range' => 0, 'max_range' => 23]]);
if ($h === false) { $h = 12; }   // note: !== 0 check — only `=== false` means invalid
```

## General rule

Any field where `0` is a legitimate value (booleans, counts, indices, flags, hours,
IDs, scores) must NOT use `?: default`. Use explicit null/`false` checks.
