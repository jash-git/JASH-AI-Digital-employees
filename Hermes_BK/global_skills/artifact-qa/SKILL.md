---
name: artifact-qa
description: "Verify standalone HTML/JS files run before delivery."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [qa, testing, browser, web, html, canvas, single-file]
    related_skills: [dogfood]
---

# Artifact QA: Verifying Self-Contained Single-File Web Artifacts

## Overview

Deliver a **single local file** (e.g. `<name>.html`) with no server and zero external dependencies?
Before handing it over, verify it actually runs — don't trust that the code is correct. This skill
covers the QA workflow for those artifacts: syntax-check the JS, load it headless, capture console
errors, drive real interactions, and confirm behavior + rendering via screenshots.

This is a different class from `dogfood` (which targets hosted web apps at a URL). Here the target
is a local file with no server, so you verify it directly rather than navigating to a deployed site.

## When to use

- The user asked for a standalone HTML/JS/CSS artifact: a game, infographic, diagram, demo, or mockup.
- You want to confirm "works before delivery" rather than just "code looks right".

## Workflow

### 1. Syntax-check the JS first (cheap, high-value)

Extract the inline `<script>` block and run `node --check`:

```bash
# extract inline script(s) from the HTML to a temp .js file, then:
node --check extracted.js   # exit 0 => no parse errors
```

A clean pass rules out syntax errors before you spend time on browser QA. If there are multiple
`<script>` blocks or external `.js` includes, check each one.

### 2. Load headless and capture console errors

Load the file via `file://` in a headless browser (see "Browser backend" below). Register BOTH:

- `page.on("console", ...)` — catches warnings + errors logged at runtime
- `page.on("pageerror", ...)` — catches uncaught exceptions / rejected promises

Check console after load AND after each significant interaction. Silent JS errors are the single most
valuable finding for these artifacts.

### 3. Confirm DOM basics + initial state

Verify: document title, canvas dimensions (if any), overlay/initial-screen visibility, and the game's
internal state through whatever global API the artifact exposes on `window`.

### 4. Drive real interactions — don't just render

Script actual use of the artifact: click start buttons, move the mouse + click (or press Space / R),
then read back internal state between steps to confirm behavior changed as expected:

- Scores increment when actions succeed
- Chains/sequences clear on valid matches
- Overlays appear for win/lose/level-complete states
- Counters that should only increase never decrease

### 5. Verify rendering + layout via screenshots

Screenshot at meaningful moments (ready screen, mid-play, win/lose overlay) and vision-analyze them to
confirm elements are positioned correctly — especially overlapping elements (e.g. a skull endpoint vs.
a shooter device in a Zuma-style game). A code edit that "looks right" can still leave two elements on
top of each other; only the screenshot confirms separation.

### 6. Confirm success AND failure paths explicitly

Test both branches: e.g. "cleared but items remain queued" should keep playing, while "all queued items
emitted AND chain empty" should fire level-complete. Don't assume one path implies the other.

## Browser backend

The interactive `browser_*` toolset launches Chrome/Chromium. If no Chromium binary exists in this
environment (only Firefox is installed), fall back to Playwright + its bundled Firefox engine:

```bash
python3 -m venv .venn && source .venn/bin/activate
pip install playwright
python -m playwright install firefox
```

Then drive the artifact with an async harness. See `references/self-contained-html-qa.md` for the full
setup, a copy-paste Playwright+Firefox harness (state logging + screenshot capture), and gotchas learned
this session (`page.evaluate` runs in page context — don't reference Python loop variables inside it;
confirm overlapping elements via screenshots after fixes).

## Output to the user

- State the verification result honestly: what was tested, that console was clean, and that behavior
  + rendering were confirmed.
- Include a screenshot path so the user can see evidence inline (use `MEDIA:<path>` on messaging platforms;
  on plain CLI just give the absolute file path).
- Only claim "works" after you actually exercised it headless — never assert correctness from code alone.
