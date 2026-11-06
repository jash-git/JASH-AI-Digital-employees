---
name: ocr-quality
description: "Check and improve scanned-PDF OCR quality before batch."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [ocr, opencv, preprocessing, quality-check, pdf]
    category: media
---

## When to Use
User wants to (a) test/verify OCR accuracy of a scanned PDF before committing to a batch, or
(b) improve OCR quality with OpenCV preprocessing (denoise / CLAHE / binarization), or
(c) decide whether a scanned book is worth batch-OCRing. Also: the PaddleOCR 3.x result structure
changed and old `ocr_out[0][0]` indexing breaks — use the recursive collector instead.
(d) OCR a single standalone image (jpg/png) that is not part of a PDF.

# OCR Quality (scanned PDF → PaddleOCR + OpenCV preprocessing)

Goal: before batch-OCRing a scanned book, verify per-page accuracy against a known-text baseline,
add OpenCV preprocessing to push accuracy up, and pick the best strategy by CER. Then decide whether
to commit to full-batch (accept proofreading) or not.

## Tool location (Windows shared folder, writable from VM)
All scripts live in `/media/sf_ComfyUI_windows_portable/python_embeded_ocr/` (the Windows embedded
Python 3.12 folder). The agent CANNOT run the OCR itself — it writes scripts; the user runs them with
that folder's `python.exe`. Files:
- `cv2_check.py`        GATE: proves cv2 actually computes (not just importable) on THIS machine.
- `ocr_quality.py`      MAIN TOOL: compares 5 OpenCV preprocessing strategies per page, scores vs baseline by CER, picks best.
- `ocr_test_page10.py`  Legacy single-page test (superseded; safe to leave or delete).
- `測試OCR第10頁.bat`   Double-click entry point: runs cv2_check → ocr_quality on page 10 → opens report in notepad.
- `ocr_image.py`        Single standalone IMAGE (jpg/png) OCR — no PDF needed. Reuses offline cached models + MKL-DNN probe-fallback; lists each text segment + timing, writes `OCR_Result_<name>.txt`.
- `掃描單張圖片.bat`    Double-click entry point: runs ocr_image.py on the default JPG → opens result in notepad (pure ASCII, no BOM).

## Workflow (do in order)
1. GATE first — before building anything on OpenCV, confirm it works in the embedded python:
   `python.exe cv2_check.py` must print `CV2_OK`. The shared-folder listing showing `cv2/` +
   `opencv_python-5.0.0.93.dist-info` only means installed; a real op (bilateralFilter/CLAHE/
   adaptiveThreshold) on a synthetic image proves it computes. If FAIL → `pip install opencv-python-headless`.
2. EVALUATE — `python.exe ocr_quality.py "<PDF>" <page(s)> [--strategy all|none|clahe|denoise_clahe|adaptive_bin|otsu_bin] [--dpi 150]`.
   Default page = 10, default strategy = all (compares every strategy + picks best by CER).
3. DECIDE — read the report (`OCR品質報告_第N頁.txt`). CER<5% → batch freely; 5–15% → proofread;
   >15% → raise DPI / better scan source / accept manual correction.

## Single-image scanning (standalone JPG/PNG)
When the target is ONE image file (not a PDF page), use `ocr_image.py` instead of `ocr_quality.py`:
- `ocr_image.py [image_path]` — loads via cv2, OCRs with the same offline cached models + MKL-DNN
  probe-fallback (oneDNN Unimplemented → auto-retry enable_mkldnn=False), lists each text segment +
  timing, writes `OCR_Result_<name>.txt` (UTF-8 BOM). No baseline comparison for unknown images.
- `掃描單張圖片.bat` — double-click entry point (pure ASCII, no BOM); runs it on the default JPG and
  opens the result in notepad. Pass a different path as argv[1] for other images.
- Workflow pattern: user says "scan <file>" → agent writes/adjusts `ocr_image.py` (default or arg) + a
  matching `.bat`; user double-clicks to run on their Windows machine. Agent CANNOT run PaddleOCR (VM
  CPU = SSE4.2, SIGILL), so all inference happens on the user's box.
- Caveat: low-res images (e.g. 511×780) may have tiny text → poor OCR; preprocessing/DPI rarely help
  this book, so if the result is bad the real fix is a higher-resolution rescan, not params.

## Preprocessing strategies (basis: OpenCV wiki concepts/thresholding-and-morphology + image-filtering)
- `none` raw grayscale (baseline). `clahe` CLAHE clip=2.0 tiles 8x8. `denoise_clahe`
  bilateralFilter(d=0,sigma=60) → CLAHE — edge-preserving, SAFEST for recognition.
- `otsu_bin` denoise+clahe → global Otsu binary (needs bimodal histogram). `adaptive_bin`
  → adaptiveThreshold(GAUSSIAN_C, block=15, C=2), dark-text-on-white. Caveat: hard binarization can
  HURT the recognizer (removes grayscale stroke cues) — the CER table decides empirically; don't assume.

## Environment facts (critical, learned)
- **Windows .bat gotcha (hard-won):** this cmd.exe does NOT honor a UTF-8 BOM (it renders as garbage like `嚜濃` and breaks `@echo off`), and reads the file in the system ANSI codepage (Big5 on 繁中 Windows). So keep the `.bat` PURE ASCII with NO BOM — never type Chinese in it. The Chinese PDF/report paths are handled *inside* ocr_quality.py (Python reads its own UTF-8 source fine); the bat calls `python.exe ocr_quality.py` with no path arg and opens the ASCII report name `OCR_Report_Page10.txt`. Note: write_file may prepend a BOM to .bat — strip it (`b[3:]`) if needed.
- Embedded env: PaddleOCR **3.7.0** (paddlex), cv2/OpenCV **5.0**, pymupdf 2.1, numpy 2.3.5.
- **PaddleOCR 3.x API returns list-of-dicts**, NOT the old `[[box,(text,conf)],...]`. Never index
  `ocr_out[0][0]` (KeyError). Use a recursive string collector that walks dict.values() + lists and
  keeps strings len>=2 (skips float scores / [x,y] box coords). This is what `collect_strings()` does.
- Harmless noise on run: `offload-arch failed with return code 1` (paddlex, models still load from cache),
  `No ccache found`, and `DeprecationWarning: Please use predict instead` (`.ocr()` still works). Don't treat as errors.
- SyntaxWarning `invalid escape '\C'`: Windows paths in a docstring → make the module docstring a raw
  string `r"""..."""` to kill it.
- **Baseline `_01.txt` is itself low-quality OCR** (has typos like 技木→技術, 領中→領域中). So CER vs it
  is inflated — new output may actually be BETTER than the baseline in prose. Read the actual text side-by-side,
  don't trust the raw CER number alone.
- **Local Linux cannot run this OCR**: PaddleOCR SIGILL on import (VM CPU = SSE4.2, no AVX). Only cv2/numpy
  work locally — and only when cwd is NOT the shared folder (else it imports the Windows cv2 and crashes).
  So: validate preprocessing + syntax LOCALLY from `/tmp` with local cv2 5.0; the user runs real OCR on Windows.
- EE books are formula/diagram-heavy (Laplace, block diagrams, matrices) — OCR reads prose ~82–85% but
  mangles equations/figures regardless of preprocessing. Plan for manual handling of those pages.

## Model caching (offline — download once, reuse forever) & quality notes
- PaddleOCR/paddlex 3.x re-resolves models each run but **uses the local cache** (`C:\Users\User\.paddlex\official_models\`) and does NOT re-download when cached. `ocr_quality.py` pins det/rec to those local dirs, disables the optional doc-orientation + unwarp models (fewer models = faster, less network surface), and auto-falls-back to a minimal proven config if this build rejects those params (never crashes). One `PaddleOCR` object is reused across all pages/strategies → **load once, then every page infers fully offline**; a network drop mid-batch won't break it. Models are already cached on this machine.
- QUALITY NOTE (胡寿松 p10): OpenCV preprocessing HURT — clahe/denoise_clahe dropped accuracy 82%→79%; best was raw `none` (~17.9% CER vs a noisy `_01.txt` baseline that itself has typos, so real quality is higher than measured). For batch, **skip OpenCV preprocessing** unless a specific scan clearly benefits; verify per source. ~82% prose (proofread-able); equations/diagrams need manual handling regardless of engine.

## Speed (MKL-DNN) — finding & mechanism
- **MKL-DNN is NOT usable with this build.** Enabling `enable_mkldnn=True` loads oneDNN v3.6.2 but the
  PP-OCRv6 models hit `(Unimplemented) ConvertPirAttribute2RuntimeAttribute not support
  [pir::ArrayAttribute<pir::DoubleAttribute>]` at INFERENCE time (onednn_instruction.cc). This is a
  model/build limitation, NOT an AVX problem — the Ryzen AI Max+ has AVX; this PaddleOCR build just can't
  route PP-OCRv6 through oneDNN.
- **Always-on gate for any perf/acceleration change:** before wiring an inference-time accelerator
  (MKL-DNN, thread count, batch parallelism) into the page loop, validate it with a tiny probe OCR on a
  blank image BEFORE the loop. Accelerator failures surface at INFERENCE time, not construction — a
  try/except around `PaddleOCR(...)` will NOT catch them and the whole run returns an empty result. On
  failure, rebuild without the accelerator (fall back to the proven config) so the tool degrades instead
  of crashing; build_ocr() does exactly this for MKL-DNN below.
- **MKL-DNN on this machine:** enabling `enable_mkldnn=True` loads oneDNN v3.6.2 but the PP-OCRv6 models
  hit `(Unimplemented) ConvertPirAttribute2RuntimeAttribute not support
  [pir::ArrayAttribute<pir::DoubleAttribute>]` at inference (onednn_instruction.cc). Not an AVX problem —
  the Ryzen AI Max+ has AVX; this PaddleOCR build cannot route PP-OCRv6 through oneDNN. So MKL-DNN is off
  by default here; build_ocr() probes it and auto-reverts to `enable_mkldnn=False` when the probe fails.
- **Speed ceiling:** with MKL-DNN unavailable, per-page time is ~45–52s on this machine (page 10) → 697
  pages ≈ 8–9h single-strategy. Untested lever to try next: cap `cpu_threads` (os.cpu_count() = 32 here;
  single-image CPU inference often runs FASTER with fewer threads due to contention — try 6–8).

## Interpreting / next steps
- If best strategy still >15% CER on prose: try DPI 200 (marginal gain, slower) or a cleaner scan source.
- For full batch later: run ocr_quality on a few representative pages first (prose + one formula page),
  confirm quality bar, then batch with the winning strategy. Keep `cpu_threads` modest to avoid crashing
  the user's machine (they cap concurrent subprocesses at 2).
## See also
- [[opencv-docs-wiki]] — thresholding-and-morphology / image-filtering pages are the basis for strategies.
- Local PaddleOCR is unusable here; see memory note on SSE4.2/AVX SIGILL if you try to run OCR on the VM.