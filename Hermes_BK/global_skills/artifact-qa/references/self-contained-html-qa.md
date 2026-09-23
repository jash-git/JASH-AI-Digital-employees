# QA for Self-Contained Single-File HTML/JS Artifacts

Session-specific detail backing the "Browser backend" section. Reproducible recipe used to verify a
zero-dependency `<name>.html` game (Zuma) delivered as one file.

## Why not just use the browser toolset?

The interactive `browser_*` toolset launches Chrome/Chromium. In some environments only Firefox is
installed and no Chromium binary exists, so `browser_exec` fails with something like:

    chrome-not-running: no supported browser is running and none could be launched -- ask the user to open Chrome, then retry.

Fall back to Playwright + its bundled Firefox engine (headless). This is a setup FIX, not a
"the tool is broken" claim — once Chromium exists the normal `browser_*` path still applies.

## Setup (one-time)

```bash
python3 -m venv .venn
source .venn/bin/activate
pip install playwright
python -m playwright install firefox
```

Use a venv to avoid polluting system packages; non-root users can do this without sudo.

## Verification workflow

1. **Extract + syntax-check the JS.** Pull the inline `<script>` out of the HTML and run `node --check`.
   This catches parse errors before any browser QA. (Python one-liner to extract: read file, regex
   `<script>(.*?)</script>`, write group 1.)
2. **Load via `file://`** in a headless Playwright Firefox page. Register both `page.on("console", ...)`
   (for warnings/errors) and `page.on("pageerror", ...)` to collect uncaught exceptions.
3. **Confirm DOM basics**: title, canvas dimensions, overlay visibility, initial game state via any
   global API the artifact exposes on `window`.
4. **Drive real interactions.** Move mouse + click (or press Space / R) in a loop; read back internal
   state between steps to confirm behavior changed (scores increment, chains clear, overlays appear).
5. **Screenshot at meaningful moments** (ready screen, mid-play, win/lose overlay) and vision-analyze
   them to verify element positioning — e.g. that overlapping elements (skull vs shooter in Zuma) are
   actually separated after any fix.

## Harness pattern (async Playwright)

```python
import asyncio
from playwright.async_api import async_playwright

URL = "file:///path/to/artifact.html"

async def main():
    errors, warnings = [], []
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1000, "height": 760})
        page.on("pageerror", lambda e: errors.append(f"PAGEERROR: {e}"))
        page.on("console", lambda m: warnings.append(f"{m.type}: {m.text}")
                if m.type in ("warning", "error") else None)

        await page.goto(URL, wait_until="domcontentloaded")
        await asyncio.sleep(0.8)  # let scripts initialize

        # read internal state through the artifact's exposed API
        st = await page.evaluate("""() => { const g = window.zuma.game;
            return { state: g.state, chainLen: g.chain.length, score: g.score }; }""")

        # drive interactions + sample state periodically
        for i in range(60):
            await page.mouse.move(tx, ty)
            await asyncio.sleep(0.06)
            await page.mouse.click(tx, ty)
            await asyncio.sleep(0.08)
            if i % 4 == 0:
                row = await page.evaluate("""() => { const g=window.zuma.game;
                    return {state:g.state, chainLen:g.chain.length, emitted:g.emitted, score:g.score}; }""")

        print("STATE:", st); print("PAGE_ERRORS:", errors or "NONE")
        await page.screenshot(path="/tmp/artifact.png")
        await browser.close()

asyncio.run(main())
```

## Gotchas learned this session

- **`page.evaluate` runs in the PAGE context**, not your Python loop. Do NOT reference a Python-side
  loop variable (e.g. `i`) inside the evaluated expression — it is undefined there and raises
  "X is not defined". Sample state without needing the counter, or capture what you need per step.
- **`emitted`/counter monotonicity** is a good health signal: counters that only ever increase should
  never decrease between samples. A decrease usually means your test ran two independent playthroughs,
  not a game bug — check the harness before suspecting the artifact.
- **Overlapping elements are easy to miss in code but obvious in screenshots.** In Zuma the skull and
  shooter were both drawn at center (480,350), hiding the skull. Fix by offsetting the shooter below
  the skull, then confirm via vision-analyze of a mid-play screenshot rather than assuming the edit worked.
- **Confirm win/lose paths explicitly.** "Cleared but items remain" should keep playing; only when all
  queued items are emitted AND the chain is empty does level-complete fire. Test both branches.
