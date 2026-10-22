#!/usr/bin/env python3
"""youtube-transcribe -- get text / SRT / VTT from a YouTube video.

Strategy:
  1. If the video has subtitles (CC or auto-generated) in the requested
     language, download them directly (highest quality, no STT error).
  2. Otherwise fall back to local speech-to-text via faster-whisper.

Dependencies: yt-dlp, ffmpeg, faster-whisper (+ PyAV). The PyAV>=19 API
change removed the `metadata_errors` kwarg that older faster-whisper
expects; a tiny monkeypatch (_patch_av) keeps it working on this box.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


class Seg:
    """Uniform segment with .start (s), .end (s), .text -- matches Whisper's."""

    def __init__(self, start: float, end: float, text: str):
        self.start = start
        self.end = end
        self.text = text.strip()


# --- PyAV compatibility -------------------------------------------------
def _patch_av() -> None:
    """Work around PyAV>=19 dropping faster-whisper's `metadata_errors` kwarg."""
    try:
        import faster_whisper.audio as fw_audio
    except Exception:
        return
    av = getattr(fw_audio, "av", None)
    if not (av and hasattr(av, "open")):
        return
    orig = av.open

    def open_(*a, **k):
        k.pop("metadata_errors", None)
        return orig(*a, **k)

    av.open = open_


# --- yt-dlp helpers -----------------------------------------------------
def _run(cmd: list[str], retries: int = 3, backoff: float = 2.0) -> subprocess.CompletedProcess:
    """Run yt-dlp, retrying on failure (handles transient HTTP 429)."""
    last = None
    for attempt in range(retries):
        last = subprocess.run(cmd, capture_output=True, text=True)
        if last.returncode == 0:
            return last
        time.sleep(backoff * (2 ** attempt))
    return last


DEFAULT_SUB_LANGS = "en,zh,zh-TW,ja,ko,es,fr,de,it,pt"


def has_subs(url: str) -> bool:
    r = _run(["yt-dlp", "--skip-download", "--list-subs", url])
    out = (r.stdout + r.stderr).lower()
    if "available automatic captions" in out:
        return True
    # manual CC: list-subs prints available languages instead of "no subtitles"
    return ("no subtitles" not in out) and ("no automatic captions" not in out)


def download_subs(url: str, lang: str | None, destdir: Path) -> Path | None:
    base = Path(destdir) / "subs"
    cmd = [
        "yt-dlp", "--skip-download", "--no-warnings",
        "--write-sub", "--write-auto-sub",
        f"--sub-lang={lang or DEFAULT_SUB_LANGS}",
    ]
    cmd += ["-o", f"{base}.%(ext)s", url]
    if _run(cmd).returncode != 0:
        return None
    for cand in Path(destdir).glob("subs.*"):
        if cand.suffix in (".srt", ".vtt"):
            return cand
    return None


def download_audio(url: str, destdir: Path) -> Path:
    base = Path(destdir) / "audio"
    r = _run([
        "yt-dlp", "--no-warnings", "-x",
        "--audio-format", "mp3",
        "-o", f"{base}.%(ext)s", url,
    ])
    if r.returncode != 0:
        raise RuntimeError("yt-dlp audio download failed:\n" + r.stderr[-1000:])
    for cand in Path(destdir).glob("audio.*"):
        if cand.suffix == ".mp3":
            return cand
    raise RuntimeError("no mp3 produced by yt-dlp")


# --- STT ----------------------------------------------------------------
def transcribe(audio_path: Path, model: str, lang: str | None) -> tuple[list[Seg], str]:
    _patch_av()
    from faster_whisper import WhisperModel

    m = WhisperModel(model, device="cpu", compute_type="int8")
    kw = {} if not lang else {"language": lang}
    segments, info = m.transcribe(str(audio_path), beam_size=5, **kw)
    out = [Seg(s.start, s.end, s.text) for s in segments]
    return out, (info.language or "unknown")


# --- subtitle parsing (normalise official subs into Seg list) -----------
_TS = re.compile(r"(\d{1,2}:\d{2}:\d{2}[.,]\d{3})")


def parse_subs(path: Path) -> list[Seg]:
    """Parse SRT or VTT into Seg list. Handles comma (SRT) / dot (VTT) ms."""
    txt = path.read_text(encoding="utf-8", errors="replace")
    lines = txt.splitlines()
    segs: list[Seg] = []
    i, n = 0, len(lines)
    while i < n:
        matches = _TS.findall(lines[i])
        if len(matches) >= 2:
            a, b = matches[0], matches[1]
            j = i + 1
            text_lines = []
            while j < n and lines[j].strip() != "" and not _TS.search(lines[j]):
                text_lines.append(lines[j])
                j += 1
            segs.append(Seg(_to_sec(a), _to_sec(b), "\n".join(text_lines)))
            i = j + 1  # skip the blank line after the block
        else:
            i += 1
    return segs


def _to_sec(ts: str) -> float:
    ts = ts.replace(",", ".")
    h, mm, ss = ts.split(":")
    return int(h) * 3600 + int(mm) * 60 + float(ss)


# --- formatting ---------------------------------------------------------
def _ts(sec: float, comma: bool = True) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    base = f"{h:02d}:{m:02d}:{s:06.3f}"  # always has a '.' for ms (e.g. 02.500)
    return base if not comma else base.replace(".", ",")  # SRT=comma, VTT=dot


def fmt_txt(segs: list[Seg]) -> str:
    return "\n".join(s.text for s in segs)


def fmt_srt(segs: list[Seg]) -> str:
    out = ["1"]
    for i, s in enumerate(segs, start=2):
        out.append(str(i))
        out.append(f"{_ts(s.start)} --> {_ts(s.end)}")
        out.append(s.text)
    return "\n".join(out)


def fmt_vtt(segs: list[Seg]) -> str:
    out = ["VTT"]
    for s in segs:
        out.append("")
        out.append(f"{_ts(s.start, comma=False)} --> {_ts(s.end, comma=False)}")
        out.append(s.text)
    return "\n".join(out)


_FMT = {"txt": fmt_txt, "srt": fmt_srt, "vtt": fmt_vtt}
_EXT = {"txt": ".txt", "srt": ".srt", "vtt": ".vtt"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Transcribe a YouTube video to text/SRT/VTT.")
    ap.add_argument("url")
    ap.add_argument("--format", choices=["txt", "srt", "vtt"], default="txt")
    ap.add_argument("--lang", help="language code, e.g. zh/en (auto-detect if omitted)")
    ap.add_argument("--model", choices=["tiny", "base", "small", "large", "large-v3"],
                    default="base", help="faster-whisper model (default: base)")
    ap.add_argument("--no-subs", action="store_true", help="skip subtitle lookup, go straight to STT")
    ap.add_argument("--no-audio-fallback", action="store_true",
                    help="only use subtitles; fail if none exist")
    ap.add_argument("-o", "--output", help="output file path")
    ap.add_argument("--model-dir", help="faster-whisper model cache dir")
    args = ap.parse_args(argv)

    destdir = Path(tempfile.mkdtemp(prefix="ytsub_"))
    segs: list[Seg] | None = None
    detected = "unknown"

    # 1) official subtitles first (best quality, no STT error)
    if not args.no_subs and has_subs(args.url):
        sub_file = download_subs(args.url, args.lang, destdir)
        if sub_file is not None:
            segs = parse_subs(sub_file)
            detected = f"subs({sub_file.name})"

    # 2) audio fallback via faster-whisper
    if not segs:
        if getattr(args, "no_audio_fallback", False):
            print("error: subtitles not found and --no-audio-fallback set", file=sys.stderr)
            return 1
        audio = download_audio(args.url, destdir)
        segs, detected = transcribe(audio, args.model, args.lang)

    if not segs:
        print("error: no segments produced (no subtitles and STT returned nothing)",
              file=sys.stderr)
        return 1

    render = _FMT[args.format]
    content = render(segs)

    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
        print(f"wrote {args.output} ({len(segs)} segments)")
    else:
        print(content)

    print(f"[detected: {detected}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
