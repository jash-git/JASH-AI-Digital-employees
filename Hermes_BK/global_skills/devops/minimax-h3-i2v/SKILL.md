---
name: minimax-h3-i2v
category: devops
description: Image-to-video via MiniMax H3 in ComfyUI with audio.
---

# MiniMax H3 Image-to-Video via ComfyUI (AMD Strix Halo)

## When to Use
User wants **image-to-video** — a first-frame picture animated into a short clip WITH native stereo audio, using MiniMax H3 on the AMD box. Or they say things like 「用這張產影片」「把這圖動起來」「图生影片」. Do NOT use for text-only (that's `minimax-h3-t2v`), LTX, Wan, or image-to-3D.

Start with the tool below; fall back to gotchas only when validation fails.

## The tool

`/media/sf_ComfyUI_windows_portable/ComfyUI/scripts/h3_i2v.py`

```
cd /media/sf_ComfyUI_windows_portable/ComfyUI/scripts
python3 h3_i2v.py "your prompt" --image start.png --duration 5 --steps 20 --seed 7 --prefix beach_i2v
```

Builds the API workflow, POSTs `/api/prompt`, polls `/api/history` until SaveVideo (node 14) emits a file, then ffmpeg/PIL checks + PASS/FAIL per dimension. Exit 0 = all pass.

## Speed (measured)
CPU-bound on this APU. **Measured end-to-end at 832x480 / 5s / 20 steps = ~30.5 min** (single run; first i2v of the session, so cold-ish + a long continuous job). Extra cost vs text-to-video: VAE-encode of the first-frame keyframe + tokenizing latents with images. Lower res and shorter duration are faster, but do NOT trust linear extrapolation — measure at the target resolution before promising a number.

Args: prompt (positional), **--image (REQUIRED)** — a filename already in ComfyUI/input/, OR a full path that gets copied into input/; --duration (default 5.0, trained sweet spot; --duration 3 for speed); --steps (20); --seed (7); --width/--height (defaults **832x480**, 16:9, CPU-speed tuned; multiples of 32); --prefix; --base.

## CRITICAL constraint: official 32B CLIP only
i2v MUST use the stock **Qwen3-VL 32B** CLIP loader. That encoder tokenizes BOTH the input image and the prompt, so it is mandatory for any image/first-frame input. The `recovered_8b` package (MiniMaxH3TextEncoderLoader) is **TEXT-ONLY** — it does NOT support image inputs and will fail here. h3_i2v.py hard-codes CLIPLoader + official clip; there is no --encoder option. Do not try to add recovered_8b.

## Node wiring (authoritative: ComfyUI/comfy_extras/nodes_minimax_h3.py)
`MiniMaxH3ImageToVideo` inputs: `clip, vae, prompt, width, height, length, first_frame(optional Image), last_frame(optional)`. Outputs: [0] Conditioning(positive) -> BasicGuider(model); [1] Latent -> SamplerCustomAdvanced.
The i2v workflow is t2va wiring + one LoadImage node (id 100) feeding `first_frame`:
```
"100": LoadImage {"image": <basename in input/>}
"5":   MiniMaxH3ImageToVideo {..., "first_frame": ["100", 0]}
```
The node resizes first_frame to the canvas (geometry anchor, keyed at frame 0); sampling still runs from full noise (denoise=1.0) exactly like t2v — the image only guides appearance + first-frame alignment.

## Models in place (Comfy-Org/MiniMax-H3)
- diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors (~20GB) UNET
- text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors (~15GB) official CLIP (type=minimax)
- vae/minimax_h3_video_vae_fp16.safetensors (~5GB) video VAE (fp16 works; int8_convrot optional)
- vae/minimax_h3_audio_vae_fp32.safetensors (~577MB) audio VAE

## Critical gotchas (learned the hard way)
1. **--image is mandatory.** resolve_image() copies a source path into ComfyUI/input/ and returns its basename; LoadImage resolves by name. Put the picture in `ComfyUI/input/` or pass its full path.
2. **API link refs MUST be strings**: `["node_id", slot]`, NOT integer `[13, 0]`. Integer refs raise KeyError at execution.py validate_inputs ~line 943 -> HTTP 400. THE classic blocker.
3. **Terminal node must be SaveVideo** (is_output_node=True). Plain CreateVideo is not an output -> HTTP 400 "Prompt has no outputs". Wrap terminal in SaveVideo.
4. **SaveVideo `format`**: pass `"mp4"` (string).
5. **length is snapped** to the model's 17k+5 frame grid at 24 fps via snap_frames(): duration=5 -> 124 frames. The tool computes it; don't pass raw frame counts.
6. **first_frame auto-resizes to canvas.** width/height set the output resolution, not the image's. Match the image aspect ratio (--width/--height) to minimize cropping; both must be multiples of 32 (native short edge up to 768, long up to 1344).
7. **CPU-only speed**: H3 runs on CPU on this APU (~2 min/step). 20 steps ~= ~40 min at high res; ~4-5 min at 512x288/832x480. Normal but slow — use background + notify_on_complete.
8. **No negatives / cfg=1**: BasicGuider runs at cfg 1, no negative branch. State what SHOULD appear; ban lists add unwanted concepts.

## Prompt format (T2VA)
One block: shots `[Shot 1]`, camera moves, and audio intent (dialogue/SFX/music) together. Write in English. On-screen text in verbatim double quotes; spoken lines in backticks. Native canvas 768px short edge, capped 768x1344, multiple of 32.

## 用戶下達方式（輸入慣例）
用戶以白話、簡短需求下达，例如「用這張海島照片、5 秒、要音」。我負責全部：轉成英文 T2VA 提示詞（分鏡＋鏡頭移動＋音效意圖）、選解析度與秒數、調 h3_i2v.py 執行、跑完回報耗時與 PASS/FAIL。用戶不指定的欄位用預設：**5 秒、832×480 橫式、內建立體聲**。圖片由我透過 --image 處理（放 input/ 或給路徑）。

## Verification meaning (what PASS/FAIL tells you)
Same historical black-frame + NaN-audio bug as t2v. verify() checks independently:
- video stream h264 present; sampled frames meanY > 30 (not near-pure-black)
- audio AAC stereo present; mean_volume > -70 dB (not silent/NaN)
If audio FAILs, re-check VAEDecodeAudio wiring.

## If generation fails validation again
Grab full error: node_errors[id].extra_info.traceback. Most common = string-vs-int link ref (gotcha #2). Re-run with the tool; it prints the exact failing node + detail on HTTP 400.

## Reference templates
- Official T2V blueprint: https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_minimax_h3_t2v.json
- HF weights: https://huggingface.co/Comfy-Org/MiniMax-H3
- Tutorial: https://docs.comfy.org/tutorials/video/minimax/minimax-h3