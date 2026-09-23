# XWD parsing quirks & Wayland capture diagnostics

Session-specific detail backing the `wayland-firefox-screenshot` skill. Concise; not a mirror of upstream docs.

## The XWD header layout quirk (why naive parsers fail)

The standard xwd header on Linux/x86-64 is documented as little-endian ints at fixed offsets:
`bitsPerPixel(0), bytesPerLine(4), xOrigin(8), yOrigin(12), width(16), height(20), depth(24)`, then byte_order/unit_size/format/pad (28-31), pixelsize(Q, 32), obf(Q, 40).

**On this box the captured Firefox window's XWD file does NOT follow that layout.** When parsed with the standard offsets you get garbage: `depth=0`, width/height in the billions. The actual layout observed:

| Field | Offset | Endian | Value seen |
|---|---|---|---|
| bitsPerPixel (107) | 0 | BE | 107 |
| format (7 = ??? / ZPixmap-ish) | 4 | BE | 7 |
| ... | 8,12 | BE | 2, 32 |
| **width** | 16 | **BE** | 1332 |
| **height** | 20 | **BE** | 875 |
| xOrigin/yOrigin | 24,28 | BE | 0, 0 |
| pixelsize (32) | 32 | BE | 32 |
| ... | 40,44 | BE | 32, 32 |
| **bytesPerLine** | 48 | **BE** | 5328 (=1332*4 => depth 32) |
| redMask (16711680=0xFF00) | 56 | BE | 16711680 |
| greenMask (65280=0xFF00) | 60 | BE | 65280 |

So width/height are **big-endian** at 16/20, and bytesPerLine is at offset 48 (not the little-endian position). `depth` is not directly stored — derive it as `bytesPerLine*8/width`. Pixel-data offset = `filesize - bytesPerLine*height`.

### Robust approach
Auto-detect: scan candidate offsets for width/height in both endiannesses, then find a bytesPerLine that yields a small positive pixel-data offset (`0 < filesize - bpl*height < max(4096, n//4)`). The bundled `assets/xwd_to_png.py` implements this tolerant parser. If you write your own, do the same — **do not assume standard little-endian offsets**.

## XDG Screenshot Portal under GNOME (observed behavior)

- `org.freedesktop.portal.Screenshot.Screenshot("", {})` returns a request handle string like
  `/org/freedesktop/portal/desktop/request/1_432/t`.
- The expected `Result` signal on that path (`interface=org.freedesktop.portal.Request`, `signal_name=Result`) **did not arrive** in this session, even with a broad `add_signal_receiver` (no path filter) and an 8s wait.
- `dbus-monitor --session "interface=org.freedesktop.portal.Request,signal_name=Result"` confirmed no Result was emitted.

This is GNOME portal behavior, not a bug in the call. The working capture method remains **xwd on the individual Firefox window** (see SKILL.md Step 4). grim also failed here with `compositor doesn't support wlr-screencopy-unstable-v1` (that protocol is wlroots/Sway; GNOME uses a different mechanism).

## Reproduction recipe (for future sessions hitting black/empty screenshots)

```bash
# 1. Confirm the symptom: xwd -root returns all-black or BadMatches
xwd -root -out /tmp/r.xwd   # often: X Error ... BadMatch opcode 73
python3 -c "from PIL import Image; im=Image.open('/dev/stdin'); ..." 2>/dev/null

# 2. Confirm Firefox is under Xwayland and which auth file it needs
ps aux | grep xwayland | grep -v grep   # -> -auth /run/user/1000/.mutter-Xwaylandauth.<HASH>

# 3. Dump the actual XWD header to find real offsets
python3 -c "import struct; d=open('/tmp/fw.xwd','rb').read()
for o in range(0,64,4): print(o, struct.unpack('>I',d[o:o+4])[0])"

# 4. Parse with tolerant layout (bundled helper)
python3 assets/xwd_to_png.py /tmp/fw.xwd /tmp/out.png   # -> SAVED ... depth=32
```

## Tool capability matrix (verified this session)

| Tool | Result on this box |
|---|---|
| `xwd -root` | BadMatch (opcode 73) OR all-black if auth missing |
| `xwd -id <firefox-window>` | **Works** — returns real pixel data (~4.6MB) |
| `convert xwd.png` (ImageMagick) | **Works** once installed (`apt install imagemagick`) |
| `ffmpeg -f x11grab` | Returns ~5-6KB black frame; also no xwd demuxer |
| PIL `ImageGrab.grab()` | OSError X_GetImage error 8 (needs correct auth) |
| `grim` | Fails: wlr-screencopy-unstable-v1 unsupported (GNOME) |
| XDG Portal via dbus | Handle returned, Result signal never arrives (GNOME) |
| `xdotool` / `wmctrl` | Not installed in this environment |
