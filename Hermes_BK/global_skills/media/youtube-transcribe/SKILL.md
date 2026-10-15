---
name: youtube-transcribe
description: Transcribe YouTube videos to text, SRT, or VTT.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [YouTube, Transcribe, STT, Media]
    related_skills: [youtube-content]
---

# YouTube Transcribe Skill

Turn any YouTube video into text (or timestamped SRT/VTT). Prefers the
video's own subtitles when available; otherwise falls back to local
speech-to-text via faster-whisper. This makes it work on Shorts and other
uploads that have no captions at all.

The tool lives at `scripts/youtube-transcribe.py` (also symlinked onto PATH
as `youtube-transcribe`). It needs yt-dlp, ffmpeg, and faster-whisper.
No API keys required.

## When to Use

- User pastes a YouTube link and asks what it says / wants the transcript.
- Need captions for a Short or a video with no subtitles (audio STT fallback).
- Want timestamped SRT/VTT for editing or syncing, not just plain text.
- Don't use for: videos behind a login wall, or when you specifically need
  the `youtube-content` summary/thread instead of raw transcript.

## Prerequisites

Verify once (all already present on this box):

```
yt-dlp --version        # >= 2024
ffmpeg -version | head -1
python3 -c "from faster_whisper import WhisperModel; print('ok')"
```

Install anything missing:

```
pip install -U yt-dlp faster-whisper   # ffmpeg via system pkg or the bundled tool on PATH
```

Note: faster-whisper is patched in-script for PyAV>=19 (which dropped a kwarg
it used). Do not remove that patch; without it transcription raises a TypeError.
The first run downloads the model (~140 MB for `base`) into the HF cache.

## How to Run

Run through the `terminal` tool. Default output is plain text on stdout:

```
terminal(command="youtube-transcribe '<url>'", timeout=300)
```

For a specific format or language, pass flags (see Quick Reference). The
detected/used source prints to stderr as `[detected: ...]`.

## Quick Reference

```
# plain text (default) - auto-detects language
youtube-transcribe '<url>'

# timestamped files
youtube-transcribe '<url>' --format srt -o out.srt
youtube-transcribe '<url>' --format vtt -o out.vtt

# force a language, bigger model for accuracy
youtube-transcribe '<url>' --lang zh
youtube-transcribe '<url>' --model small

# skip subtitle lookup entirely (pure STT)
youtube-transcribe '<url>' --no-subs
```

`<url>` accepts watch links, `/shorts/...`, and embed links.

## Procedure

1. Confirm prerequisites are importable (Prerequisites section).
2. Run the tool with `--format txt` first to preview; check `[detected:]` on
   stderr tells you whether it used subtitles or STT.
3. If output looks right, re-run for the desired format/file:
   `-o out.srt` (or `.vtt`). Verify the file opens and timestamps are present.
4. For accuracy-critical or long audio, use `--model small` (or `large-v3`);
   trade speed for quality. `base` is the default balance.
5. If a run fails, see Pitfalls before re-running.

## Pitfalls

- YouTube rate-limits the subtitle API (HTTP 429) after rapid calls. The tool
  retries with backoff; if subtitles stay blocked it silently falls back to
  audio STT (still correct, just transcribed). Wait a bit and retry rather than
  hammering. Audio extraction is usually not rate-limited the same way.
- No subtitles AND no auto-captions -> always uses STT. STT accuracy depends on
  model size and audio clarity; `base` can mishear homophones in noisy or
  accented speech. Review output, don't trust it blindly.
- `--format vtt` emits period-based ms (`02.500`); SRT uses comma (`02,500`).
  Both are validated by the self-test; do not mix them.
- Official-subtitle download tries a curated language set (en,zh,ja,ko,...) when
  `--lang` is omitted, so it never blasts all ~50 available languages.
- Long videos: transcription time scales with duration on CPU. Set a generous
  `timeout` (or run with background + notify) for clips over a few minutes.

## Verification

Run the offline self-test before trusting a build (no network):

```
terminal(command="python3 scripts/selftest.py")
```

It asserts SRT/VTT/txt formatting and the subtitle parser on fixture data; it
must print `ALL TESTS PASSED`. Then confirm a real run prints `[detected: ...]`
and produces the expected number of segments/lines.
