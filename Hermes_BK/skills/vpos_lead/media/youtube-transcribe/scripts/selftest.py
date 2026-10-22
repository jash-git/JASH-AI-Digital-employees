#!/usr/bin/env python3
"""Self-tests for youtube-transcribe (offline, no network).

Validates the formatting functions and the official-subtitle parser so a
broken build fails fast before any YouTube download. Run:
    python3 scripts/selftest.py
Exits 0 on success, 1 on any failure.
"""
import importlib.util
import tempfile
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "yt", Path(__file__).resolve().parent / "youtube-transcribe.py"
)
yt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(yt)


def check(name, cond):
    print(("PASS" if cond else "FAIL"), name)
    assert cond, name


# --- formatting ---------------------------------------------------------
segs = [yt.Seg(0.0, 2.5, "Hello"), yt.Seg(30.0, 61.456, "World line")]

txt = yt.fmt_txt(segs)
check("fmt_txt joins text", txt == "Hello\nWorld line")

srt = yt.fmt_srt(segs)
check("fmt_srt header+index", srt.startswith("1") and "\n2\n" in srt)
check("fmt_srt timestamp", "00:00:00,000 --> 00:00:02,500" in srt)
check("fmt_srt ms rounding", "00:00:30,000 --> 00:01:01,456" in srt)

vtt = yt.fmt_vtt(segs)
check("fmt_vtt header", vtt.startswith("VTT"))
check("fmt_vtt comma ts", "00:00:00.000 --> 00:00:02,500" not in vtt and
      "00:00:00.000 --> 00:00:02.500" in vtt)

# --- SRT parser ---------------------------------------------------------
srt_text = """1
00:00:01,000 --> 00:00:03,500
Hello world

2
00:00:04,000 --> 00:00:06,000
Second line
one more"""
p = Path(tempfile.mkdtemp()) / "in.srt"
p.write_text(srt_text, encoding="utf-8")
r = yt.parse_subs(p)
check("parse_subs count", len(r) == 2)
check("parse_subs t0", abs(r[0].start - 1.0) < 1e-6 and abs(r[0].end - 3.5) < 1e-6)
check("parse_subs text0", r[0].text == "Hello world")
check("parse_subs multiline", r[1].text == "Second line\none more")

# --- VTT parser ---------------------------------------------------------
vtt_text = """VTT
00:00:01.000 --> 00:00:02.000
VTT line"""
p2 = Path(tempfile.mkdtemp()) / "in.vtt"
p2.write_text(vtt_text, encoding="utf-8")
r2 = yt.parse_subs(p2)
check("parse_vtt count", len(r2) == 1)
check("parse_vtt ts", abs(r2[0].start - 1.0) < 1e-6 and abs(r2[0].end - 2.0) < 1e-6)
check("parse_vtt text", r2[0].text == "VTT line")

print("\nALL TESTS PASSED")
