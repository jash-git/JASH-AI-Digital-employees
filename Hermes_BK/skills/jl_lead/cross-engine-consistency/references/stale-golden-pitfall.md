# Stale Golden File Pitfall

## The lesson

A golden/reference file is only as trustworthy as the code that generated it. If you change an algorithm, **regenerate or discard** any pre-existing golden file — otherwise your test asserts the *old* (possibly buggy) value and passes while hiding the bug.

## Concrete reproduction (suanming project)

1. Built `src/public/js/tests/bazi-core-xcheck.js` that ran the JS engine and compared it against a hand-written `golden.json`.
2. `golden.json` was generated from the **old** PHP `calcWuxing` (which did NOT count 地支本氣).
3. After patching PHP to add 地支本氣 +1, the test still reported FAIL — but not because JS was wrong. It failed because the golden file encoded the *old* PHP value (火=0.4) while the correct JS value was (火=1.4).
4. The real fix: stop comparing JS against a static golden file at all. Rewrite the harness to run **both** engines live and compare them (`bazi-core-xcheck.js` → JS-vs-PHP oracle). No golden file needed; the second engine is the oracle.

## Rule of thumb

- Prefer a **live second-engine oracle** over any static golden/reference file.
- If you must use a golden file, regenerate it from current code and note the generation command in the file header.
- A test that passes on day one against hand-written values proves nothing — design it so it *would* fail if the two engines diverge.

## Detection heuristic

When a "consistency" test fails after you changed only engine B, check whether the golden value matches engine A's output. If it doesn't, your oracle is stale — fix the oracle, don't force engine B to match a wrong expectation.
