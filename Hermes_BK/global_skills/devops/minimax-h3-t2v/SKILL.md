---
name: minimax-h3-t2v
category: devops
description: Run MiniMax H3 text-to-video with audio in ComfyUI (AMD).
---

# MiniMax H3 Text-to-Video via ComfyUI (AMD Strix Halo)

## When to Use
The user wants text-to-video WITH sound from MiniMax H3 in their ComfyUI on the AMD box — or a prior run failed validation / produced black frames or NaN/silent audio. Do NOT use for LTX, image-to-3D, or non-MiniMax video. Start with the tool script below; fall back to the gotchas only when validation fails.

Generates short clips (text -> 768p video WITH native stereo audio) on the user's Windows ComfyUI portable, driven over HTTP from the agent VM. Models already downloaded; server at http://10.0.2.2:8188.

## The tool (use this, don't hand-build JSON)

`/media/sf_ComfyUI_windows_portable/ComfyUI/scripts/h3_t2v.py`

```
cd /media/sf_ComfyUI_windows_portable/ComfyUI/scripts
python3 h3_t2v.py "your prompt" --duration 5 --steps 20 --seed 7 --prefix beach_intro
```

It builds the API workflow, POSTs to `/api/prompt`, polls `/api/history` until `SaveVideo` (node 14) emits a file, then runs ffmpeg checks and prints PASS/FAIL per dimension + RESULT line. Exit code 0 = all pass.

Args: prompt (positional), --duration (s, default 2; ~5s is trained sweet spot), --steps (default 20), --seed (7), --width/--height (defaults now **832x480** for speed — was 1344x768; ~2.6x fewer pixels/frame on this CPU box, keeps 16:9; pass --width 1344 --height 768 to restore full res), --encoder {official|recovered_8b} (default **official** — stock 32B; faster + validated on this box. recovered_8b = smaller/lighter Qwen3-VL-8B, ~6 GB vs ~16 GB, for VRAM savings at high res only), --prefix, --base. Do NOT swap to recovered_8b expecting speed — it is measurably slower here (see "Encoder swap and time").

Speed note (2026-11): default resolution was cut from 1344x768 → 832x480 because this box runs H3 on CPU (~2 min/step). Resolution is the length-preserving lever; frame count is fixed by --duration via snap_frames() (24fps, 17k+5 grid), so cutting frames == shorter clip, not lower res. A 5s clip @832x480 ≈ 15-25 min vs >60 min at 1344x768. To go even faster: --duration 3 (shorter clip) or --steps 12 (lower quality).

## Models already in place (Comfy-Org/MiniMax-H3)
- diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors (~20 GB) — UNET
- text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors (~15 GB) — stock CLIP (type=minimax); kept for `--encoder official`
- vae/minimax_h3_video_vae_fp16.safetensors (~5 GB) — video VAE
- vae/minimax_h3_audio_vae_fp32.safetensors (~577 MB) — audio VAE

## Text encoder (default: official 32B)
Default runs use the stock **official 32B** encoder — faster and validated on this box. The smaller **recovered_8b** is opt-in via `--encoder recovered_8b` for VRAM savings at high res: a recovered Qwen3-VL-8B + ARA + 4096→5120 adapter, ~6 GB vs ~16 GB, loaded by the `MiniMaxH3TextEncoderLoader` custom node. It is **text-only T2V** — do NOT use for image-to-video, first-frame, last-frame, or reference inputs — and it degrades on proper nouns / non-English spoken lines (fine for nature/scene prompts, risky for named characters or dialogue). Revert to stock 32B with `--encoder official`. Install/recover recipe + the ClipProj 4B/8B alternative: references/text-encoder-swap.md.

### Encoder swap and time (measured)
### Encoder swap and time (measured) — official is FASTER on this box
Measured total wall-clock at 5s @512×288 / 20 steps, same prompt:
- **official 32B**: 241s, then 241s (two warm runs) ≈ **4.0 min**, very consistent
- **recovered_8b**: 281s cold → 305s warm ≈ **~4.9 min** average
So recovered_8b does NOT speed things up — it is measurably SLOWER (~50–60s / ~12%) even fully warm; the ARA + projection adapters add overhead on ROCm/CPU that offsets its smaller size (cold-start hypothesis ruled out by the warm re-run). At low resolution the diffusion steps + VAE decode dominate and the encoder runs once per clip, so the absolute gap is small (~1 min). Pick recovered_8b ONLY for lower VRAM (~6 GB vs ~16 GB) at high res (e.g. 1344×768) where memory pressure matters; keep official as default for speed + it is the validated config here. The real speed lever is resolution (`--width/--height`) or `--steps`/`--duration`, not the encoder.
Official template references `minimax_h3_video_vae_int8_convrot` but the fp16 file we have works and is more reliable on AMD (no convrot quant backend). Do not block on missing int8 video VAE.

## Critical gotchas (learned the hard way)
1. **API link refs MUST be strings**: `["node_id", slot]`, NOT integer `[13, 0]`. Integer refs raise `KeyError` at execution.py `validate_inputs` ~line 943 (`prompt[o_id]['class_type']`) -> HTTP 400 "Exception when validating node". This was THE blocker that killed every early attempt.
2. **Terminal node must be `SaveVideo`** (has `is_output_node=True`). Plain `CreateVideo` is NOT recognized as an output by validate_prompt -> HTTP 400 "Prompt has no outputs". The official blueprint's terminal IS CreateVideo, but it only works inside the subgraph; for API submission wrap it in SaveVideo.
3. **SaveVideo `format` DynamicCombo**: pass `"format": "mp4"` (string). Omitting/invalid values can cascade a validation exception onto the upstream node.
4. **length is snapped** to the model's 17k+5 frame grid at 24 fps via `max(5,round(d*24)) + (5-(max(5,round(d*24))%17))%17`. duration=2 -> 56 frames (~2.33s). The tool computes this; don't pass raw frame counts.
5. **CPU-only speed**: H3 runs on CPU on this APU (~2 min/step). 20 steps ~= ~40 min total. Normal, just slow — do NOT treat as stuck. Use background + notify_on_complete for long polls.
6. **No negatives / cfg=1**: BasicGuider runs at cfg 1 with no negative branch. State what SHOULD appear; ban lists add unwanted concepts.

## Prompt format (T2VA)
One block: shots `[Shot 1]`, camera moves, and audio intent (dialogue/SFX/music) together. Write in English. On-screen text in verbatim double quotes; spoken lines in backticks. Native canvas 768px short edge, capped 768x1344, multiple of 32.

## 用戶下達方式（輸入慣例）
用戶以白話、簡短需求下达，例如「海島清晨、5 秒、豔屏、要音」。我負責全部：把它轉成英文 T2VA 提示詞（分鏡＋鏡頭移動＋音效意圖，單一段落）、選解析度與秒數、調 h3_t2v.py 執行、跑完回報耗時與 PASS/FAIL。用戶不指定的欄位用預設：**5 秒、832×480 橫式、內建立體聲**（H3 本來就出音，「要音」是預設值）。

## Verification meaning (what PASS/FAIL tells you)
The historical bug was black frames + NaN audio track. verify() checks each independently:
- video stream h264 present; sampled frames meanY > 30 (not near-pure-black)
- audio AAC stereo present; mean_volume > -70 dB (not silent/NaN)
If audio FAILs, that's the old NaN-audio regression — re-check VAEDecodeAudio wiring.

## If generation fails validation again
Grab full error: node_errors[id].extra_info.traceback. Most common = string-vs-int link ref (gotcha #1). Re-run with the tool; it prints the exact failing node + detail on HTTP 400.

## Reference templates
- Official T2V blueprint: https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_minimax_h3_t2v.json
- HF weights: https://huggingface.co/Comfy-Org/MiniMax-H3
- Tutorial: https://docs.comfy.org/tutorials/video/minimax/minimax-h3