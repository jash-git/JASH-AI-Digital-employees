---
name: cdp-web-test
description: "Verify a live web app by driving Chrome directly over CDP."
version: 0.1.0
author: jl_lead, Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [qa, testing, browser, cdp, functional-verification, python]
    related_skills: [dogfood, systematic-debugging]
---

# CDP Web Test: Functional Verification via Chrome DevTools Protocol

## Overview

Verify that a **live** web app actually works — not just that it renders — by driving the browser directly over the Chrome DevTools Protocol (CDP) from Python. Use this when the high-level `browser_exec` tool returns empty/blank results, or whenever you need deterministic DOM assertions (option counts, form output, JS errors) rather than an AI screenshot description.

Screenshots and page snapshots prove a page *renders*; they do **not** prove a button click produces output. Always submit forms and read the result DOM before declaring anything "normal".

## When to Use

- `browser_exec`/high-level browser tool returns empty values (js() calls, page_info, capture_screenshot all come back blank) — the tool is malfunctioning but Chrome itself may be fine.
- You need a **deterministic** assertion: "select has 12 options", "submit produced pillar X", "zero console errors".
- You must exercise an interactive flow end-to-end (fill inputs → click submit → read result) on a deployed site.

## When NOT to Use

- The page is static and needs no interaction — use `web_extract` or curl instead.
- You only need visual layout assessment — use `browser_exec` + `vision_analyze`.

## Prerequisites

- Chrome running with remote debugging on a known port (default 9222):
  ```
  google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-qa-profile \
    --no-first-run --disable-gpu --remote-allow-origins=* 2>&1
  ```
  Run it via `terminal(background=true)` so Hermes tracks the process. The **`--remote-allow-origins=*` flag is mandatory** — without it, WebSocket handshakes fail with `403 Forbidden` (see Pitfalls).
- Python `websocket-client` installed in the active venv (`import websocket`). If missing, install: `pip install websocket-client`.

## How to Run

Use the bundled probe script for a quick smoke test:
```
terminal(command="python3 scripts/cdp_probe.py --url http://localhost/tool/lunar.html")
```
The script navigates, waits for load, and reports option counts + any JS errors. For custom flows (fill specific fields, click specific buttons), write a short inline Python in `terminal` using the same CDP pattern — see the procedure below.

## Procedure

1. **Confirm Chrome is reachable.** `curl -s http://127.0.0.1:9222/json/version | head -c 200`. If nothing returns, start Chrome (see Prerequisites) and wait ~3 seconds.
2. **List page targets** to find the correct webSocketDebuggerUrl:
   ```python
   import json, urllib.request
   data = json.load(urllib.request.urlopen("http://127.0.0.1:9222/json"))
   ws_url = next(t["webSocketDebuggerUrl"] for t in data if t.get("type") == "page")
   ```
3. **Open a WebSocket** and write a `cdp(method, **params)` helper that sends an id, then drains the socket until it receives the matching response (console/runtime events arrive interleaved and must be skipped):
   ```python
   import websocket, json
   ws = websocket.create_connection(ws_url, timeout=30)
   _c = [0]
   def cdp(m, **p):
       _c[0] += 1; ws.send(json.dumps({"id": _c[0], "method": m, "params": p}))
       while True:
           r = json.loads(ws.recv())
           if isinstance(r, dict) and r.get("id") == _c[0]:
               return r.get("result", {})
   ```
4. **Enable runtime + console** to capture errors: `cdp("Runtime.enable")`, `cdp("Console.enable")`.
5. **Navigate**: `cdp("Page.navigate", url=TARGET)`; sleep 3s for scripts to load.
6. **Drain console events** into an error list (see Pitfalls — you must read the socket, not just call methods):
   ```python
   errors = []
   def drain(n=8):
       for _ in range(n):
           try:
               ws.settimeout(1.0); resp = json.loads(ws.recv())
               if isinstance(resp, dict) and resp.get("method") == "Runtime.consoleAPICalled":
                   for a in resp.get("params", {}).get("args", []):
                       if a.get("type") == "error": errors.append(str(a.get("value", "")))
           except Exception: break
   ```
7. **Drive the flow** with `Runtime.evaluate` (returnByValue=True to get values back):
   - Fill inputs: `cdp("Runtime.evaluate", expression="document.getElementById('id').value='2026'", returnByValue=True)`.
   - Click submit: `cdp("Runtime.evaluate", expression="document.getElementById('submitBtn').click()", returnByValue=True)`; sleep 1-2s.
8. **Read the result DOM** — this is the proof:
   ```python
   res = cdp("Runtime.evaluate",
     expression="(function(){var el=document.getElementById('result');return el?el.innerHTML.substring(0,1200):'NONE';})()",
     returnByValue=True)
   print(res.get("result", {}).get("value", ""))
   ```
9. **Assert and report**: option counts (`el.options.length`), result content, and `errors` list. Declare verified only when the result DOM is non-empty AND errors is empty.

## Pitfalls

- **403 WebSocket handshake** — Chrome rejects CDP connections unless launched with `--remote-allow-origins=*`. If `websocket.create_connection` raises `WebSocketBadStatusException: Handshake status 403 Forbidden`, restart Chrome with that flag. This is a launch-flag problem, not a code bug.
- **Do NOT use `print()` inside `browser_exec` js()** — it times out in the harness. When using CDP directly from Python (via `terminal`), `print()` works fine; the timeout was specific to the browser-harness JS wrapper.
- **CDP `Runtime.evaluate` return values are reliable only when read via `returnByValue=True`.**
- **Interleaved events**: after enabling Runtime/Console, socket reads may return event objects before your method responses. The drain loop in step 3 handles this — never assume the first recv is your answer.
- **Chrome profile cache can serve stale JS** even when Apache ETag/Last-Modified are fresh and `curl` fetches new bytes. If a deployed fix isn't reflected, kill Chrome + remove its `--user-data-dir` + relaunch (a clean profile). See the reference for the full incident.
- **pkill by pattern can kill your own shell** — `pkill -f chrome-suanming-profile` terminated the agent's bash too. Kill by exact PID from `ps aux | grep ... | awk '{print $2}'`, or use `terminal(background=true)` + `process(action="kill")`.

## Verification

A verification is complete only when all three hold:
- The result DOM after submit is **non-empty** and contains the expected value (e.g. correct pillar/gan-zhi conversion).
- Select option counts are as expected (`monthOpts=12`, `dayOpts>=28`).
- The drained console error list is empty.

## Support Files

- `scripts/cdp_probe.py` — reusable smoke-test probe: navigate, wait, report select option counts + JS errors. Extend with your own fill/click/read steps for custom flows.
- `references/cdp-qa-incident.md` — the full session incident: browser_exec returning empty, the 403 handshake fix, and the Chrome-cache trap that required a clean profile.