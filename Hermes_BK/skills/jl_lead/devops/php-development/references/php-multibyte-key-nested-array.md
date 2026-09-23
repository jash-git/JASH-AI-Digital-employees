# PHP 8.3 Multibyte String Keys in Nested Arrays — Reproduction Matrix

## Symptom
`parse error: syntax error, unexpected token ":", expecting "]"` on a line containing
a single-quoted multibyte string key with a nested-array value.

## Root cause
PHP 8.3 CLI tokenizer mis-counts bytes when it encounters multibyte characters inside
nested-array literals (`['中'=>[...]]`). It is NOT an encoding problem (UTF-8 bytes are
correct) and NOT fixed by `mbstring.internal_encoding=UTF-8` or `default_charset`.

## Reproduction matrix (verified on PHP 8.3.6 CLI)
| Pattern | Result |
|---|---|
| Single-quote, single nested entry: `['子'=>['子']]` | ✅ works |
| Single-quote, two+ nested entries: `['子'=>['子'],'丑':['己','癸']` | ❌ fails |
| Double-quote, two+ nested entries: `["子"=>["子"],"丑"=>["己","癸"]]` | ✅ works |
| Single-quote, scalar values: `['金'=>0.0,'木'=>0.0]` | ✅ works |
| ASCII keys, nested arrays: `['a'=>['b'],'c'=>['d','e']]` | ✅ works |
| Multi-line single-quote nested arrays | ❌ fails (same bug) |

## Fix options
1. **Double-quoted keys** (recommended): `["子"=>["子"], "丑"=>["己","癸"]]`
2. Flatten to a single line (works with single quotes but less readable).

## Verification recipe
```bash
php -l src/api/bazireport.php   # must say: No syntax errors detected
SKIP_AUTH_DEBUG=true php src/api/bazireport.php | python3 -m json.tool  # valid JSON output
```

## Real-world example (suanming project)
The `$cang` (藏干) array in `src/api/bazireport.php` used single-quoted Chinese keys with
nested-array values across multiple lines — the exact trigger. Converted to double quotes:
```php
$cang = ["子"=>["子"], "丑"=>["己","癸"], "寅"=>["甲","丙","戊"],
    "卯"=>["卯"], "辰"=>["戊","乙","壬"], "巳"=>["丙","庚","戊"],
    "午"=>["丁","己"], "申"=>["庚","壬","戊"], "酉"=>["酉"],
    "戌"=>["戊","辛",""], "亥"=>["壬","甲"]];
```
