---
name: cross-engine-consistency
description: Verify two algorithm implementations agree on shared inputs.
version: 0.1.0
author: jl_lead (jl_lead), Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  tags: [testing, parity, consistency, cross-engine, oracle]
  related_skills: [test-driven-development, systematic-debugging, subagent-driven-development]
---

# Cross-Engine Consistency Testing

## Overview

Verify that two independent implementations of the same algorithm produce identical results by running **both engines against the same inputs in one harness and comparing field-by-field** — not by checking either engine against hand-written golden values.

Applies when a project has two code paths for one computation (e.g. JS frontend engine + PHP backend engine, or Python reference + C++ production). The risk is silent divergence: both "work" but disagree on edge cases.

## When to Use

- Two implementations of the same algorithm exist and must agree (JS vs PHP, client vs server, refactored vs original).
- A bug was found where one engine disagreed with another — you need a regression test that pins them together.
- You are about to change one engine; want a guard so the other can't drift silently.

**Don't use for:**
- Verifying a single implementation against expected output (use TDD).
- Two implementations that are *supposed* to differ by design.

## Core Idea — Oracle, Not Golden Values

Hand-written golden values are themselves an unverified guess. The strongest oracle is **the other engine**. Run both on the same inputs; if they agree across a spread of cases (including boundaries), you have high confidence. If they disagree, one is wrong and the diff tells you where to look.

The test harness must be able to **fail** — i.e. before any fix it should show FAILs, proving the comparison actually catches divergence. A test that passes on day one against hand-written values proves nothing.

## Procedure

1. **Identify the shared-input space.** Pick cases spanning normal + boundary (year boundaries, leap years, month/day edges). For calendar/algo code, include dates near节气/立春/leap transitions.
2. **Build a pure oracle for engine B** that takes inputs on stdin and returns structured output on stdout — no DB, no HTTP, no side effects. Extract only the pure-function section of its source (see `references/php-oracle-pattern.md`).
3. **Load engine A in-process.** If it is browser/UMD JS, load it via a VM sandbox so `window`/`global` resolve (see `scripts/xcheck.js`).
4. **Run both on each input and compare field-by-field** (pillars, shengxiao, wuxing, etc.). Report PASS/FAIL per case with the exact diverging fields.
5. **Fix engine B to match engine A's authoritative algorithm**, then re-run until all cases PASS. Commit the harness so it guards against future drift.

## Pitfalls

- **Stale golden files.** A golden/reference file generated from *old* code encodes old (possibly wrong) values. If you change an algorithm, regenerate or discard the oracle — otherwise your test asserts the bug. Prefer a live second-engine oracle over any static golden file (`references/stale-golden-pitfall.md`).
- **Browser/UMD JS won't `require` in Node.** It guards on `window`/`define`/`module.exports`. Use `vm.createContext` with a sandbox where `sandbox.window = sandbox` and `sandbox.global = sandbox`, then `vm.runInContext`. A common trap: the module assigns to `global.X` (Node-only), which is undefined in the VM context — set `sandbox.global = sandbox` so it lands on your sandbox.
- **Two engines can disagree for a legitimate convention reason** (e.g. JS uses 立春-adjusted year for shengxiao, PHP uses raw input year). That is not always a bug — classify each divergence as "algorithm mismatch" vs "intended convention difference" and handle separately. Do not auto-fix conventions.
- **`sed -n 'START,END'` extraction can bleed in an unterminated comment** from the source. Stop at a clean boundary (a function's closing brace), not an arbitrary line number; re-check after any edit that shifts lines.

## Support Files

- `scripts/xcheck.js` — Node harness: loads JS engine via VM sandbox, shells out to the PHP oracle on stdin, compares field-by-field. Adapt the CASES array and comparison fields per project.
- `references/php-oracle-pattern.md` — how to extract a pure-function PHP oracle from a larger API file (DB-free, stdin→JSON).
- `references/stale-golden-pitfall.md` — the golden-file staleness lesson with the concrete reproduction.

## Verification

- [ ] Harness FAILs before the fix (proves it catches divergence)
- [ ] Harness PASSES after the fix on all cases
- [ ] Each reported divergence is classified as algorithm-mismatch or intended-convention
- [ ] Oracle regenerated from current code, not a stale golden file
- [ ] Harness committed to guard against future drift