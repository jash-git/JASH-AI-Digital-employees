---
name: wayland-firefox-screenshot
description: "Screenshot Firefox on a Wayland/Xwayland Linux box where xwd, PIL, grim and portal all fail. Diagnose display, daemonize Firefox to survive terminal timeout, capture window via xwd then convert."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [browser, screenshot, wayland, firefox, linux, debugging]
    related_skills: [dogfood]
---

# Wayland Firefox Screenshot

## When to use
Firefox runs on a Linux box but you cannot capture its screen. Symptoms that point here:
- `xwd -root`, PIL `ImageGrab`, and `ffmpeg x11grab` all return **all-black** images.
- `xwd -root` throws `X Error ... BadMatch (invalid parameter attributes)` on opcode 73 (`X_GetImage`).
- `grim` fails with `compositor doesn't support wlr-screencopy-unstable-v1`.
- XDG Screenshot Portal returns a handle but the `Result` signal never arrives.
- Firefox processes exist but **no window is mapped** in `xwininfo -root -tree`.

## Root cause (the layered problem)
Firefox on GNOME runs under **Xwayland** (an X server at `:0`), not native Wayland. Three independent blockers stack:
1. **Process dies**: a foreground `terminal()` call that times out kills the whole process group, so Firefox vanishes. Fix: daemonize it.
2. **Snap sandbox + missing XAUTHORITY**: snap-wrapped Firefox cannot open `:0` without the correct auth file; and `unset MOZ_HEADLESS` / env exports in a fresh terminal snapshot do NOT persist (the terminal restores its snapshot each call). Fix: pass everything inline via `env VAR=val cmd`, use the full binary path, force X11 with `MOZ_ENABLE_WAYLAND=0`.
3. **Capture tooling**: root-window xwd BadMatches on Xwayland; ffmpeg lacks an xwd demuxer; grim/portal don't work under GNOME. Fix: capture the **individual Firefox window** (not root) with `xwd`, then convert to PNG with ImageMagick `convert`.

## Prerequisites (install once)
```bash
DEBIAN_FRONTEND=noninteractive sudo apt-get install -y imagemagick x11-apps x11-utils
# xwd is in x11-apps; xwininfo/xwininfo are in x11-utils
```
Verify: `which xwd convert`.

## Step 1 — Diagnose the display environment
```bash
echo "DISPLAY=$DISPLAY"
xdpyinfo | grep -iE "depth of root|dimensions"          # :0 is a real X server (24-bit)
ls /tmp/.X11-unix/                                       # may show X0 and X1
ps aux | grep -i xwayland | grep -v grep                 # find the Xauth path
```
The Xwayland line shows `-auth /run/user/1000/.mutter-Xwaylandauth.<HASH>`. That HASH is your `XAUTHORITY`.
Also check Firefox's own env for `MOZ_HEADLESS=1` (means headless — no window will map):
```bash
for pid in $(pgrep -f firefox); do tr '\0' '\n' < /proc/$pid/environ | grep '^MOZ_HEADLESS'; done | sort -u
```

## Step 2 — Kill any existing Firefox (by PID, NOT pkill)
`pkill -f firefox` will also kill your own shell because the pattern matches the terminal command text. Use exact PIDs:
```bash
for pid in $(pgrep -f firefox); do [ "$pid" != "$$" ] && kill "$pid" 2>/dev/null; done
```

## Step 3 — Launch Firefox as a daemon (survives terminal timeout)
Use the bundled helper `assets/start_firefox.py` (double-fork detaches it from the terminal process group):
```bash
DISPLAY=:0 XAUTHORITY=/run/user/1000/.mutter-Xwaylandauth.<HASH> \
  MOZ_ENABLE_WAYLAND=0 /snap/firefox/<rev>/usr/lib/firefox/firefox "<URL>"
```
Or run the helper directly (it sets DISPLAY/XAUTHORITY/MOZ_ENABLE_WAYLAND=0 and daemonizes):
```bash
python3 assets/start_firefox.py "https://www.google.com/search?q=..."
```
Wait ~5s, then confirm it is alive AND a window mapped:
```bash
pgrep -af firefox | grep -v bash | head -2
xwininfo -root -tree 2>&1 | grep -iE "firefox|google"   # expect at least one Firefox window with geometry
```
The main content window (large geometry, e.g. `1332x896+90+59`) is the one to capture.

## Step 4 — Capture the Firefox window and convert to PNG
```bash
export DISPLAY=:0
export XAUTHORITY=/run/user/1000/.mutter-Xwaylandauth.<HASH>
# Get the main window ID (the one with real width/height, not 1x1):
WINID=$(xwininfo -root -tree 2>&1 | grep firefox | awk '{print $1}' | sort -t x -k2 -rn | head -1)
xwd -id "$WINID" -out /tmp/firefox.xwd
/usr/bin/convert /tmp/firefox.xwd /tmp/firefox.png
```
If `xwd -id` also BadMatches, fall back to capturing the whole Xwayland screen via a small Python xwd reader (see `assets/xwd_to_png.py`) — but window-level capture is preferred.

## Step 5 — Verify the image is real content (not black)
```bash
/usr/bin/python3 -c "
from PIL import Image
im = Image.open('/tmp/firefox.png')
px = list(im.convert('RGB').getdata())
nb = sum(1 for r,g,b in px if not (r<8 and g<8 and b<8))
print('size', im.size, 'non-black %.1f%%' % (100*nb/len(px)))
"
```
A real page is typically >80% non-black. If ~0%, the window was off-screen or headless — re-run Step 2–3.

## Helper scripts
- `assets/start_firefox.py` — daemonizes Firefox with correct DISPLAY/XAUTHORITY/MOZ_ENABLE_WAYLAND=0, takes a URL arg.
- `assets/start_browser.py` — daemonizes Chrome/Chromium; adds `--no-sandbox --disable-gpu --user-data-dir=/tmp/chrome-profile --ozone-platform=x11`. The last flag is **critical for Chrome**: unlike Firefox (which defaults to X11 here), Chrome prefers native Wayland and maps no X11 window without it.
- `assets/xwd_to_png.py` — parses an XWD file and writes PNG (fallback if `convert` unavailable).

## Session notes / diagnostics
- `references/xwd-parsing-and-portal.md` — the XWD header layout quirk on this box (big-endian width/height at offsets 16/20, bytesPerLine at 48), why the XDG Portal `Result` signal never arrives under GNOME, and a full tool-capability matrix. Read before writing your own xwd parser.

## Pitfalls learned the hard way
- **Never** use `pkill -f firefox` from a terminal call — it kills your own shell. Kill by PID.
- **Never** rely on `unset VAR` or `export VAR=val` persisting across separate `terminal()` calls — each call restores its snapshot. Pass env inline: `VAR=val cmd`.
- **Never** capture the Xwayland *root* window with xwd — it BadMatches. Capture the individual Firefox window.
- Snap-wrapped apps need the exact `.mutter-Xwaylandauth.*` file, not a generic one.
- `MOZ_HEADLESS=1` in a process env means no window maps; ensure it is absent (the daemon helper does not set it).

## Quick reference: which tool works when
| Environment | Working capture method |
|---|---|
| Plain X11 (`DISPLAY=:0`, real X server) | `xwd -root` or `import -window root` |
| GNOME Wayland + Xwayland (Firefox under Xwayland) | `xwd -id <firefox-window>` + `convert` |
| Native Wayland compositor | XDG Screenshot Portal via DBus, or `grim`+`slurp` on wlroots (Sway) |
