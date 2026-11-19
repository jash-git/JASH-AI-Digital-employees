# MiniMax H3 Text Encoder Swap (recovered_8b)

Install/verify the smaller recovered_8b text encoder for MiniMax H3, and choose it vs alternatives.

## Why
H3 conditions on a Qwen3-VL-32B truncated to 50 layers (~15.7 GB in NVFP4). On this CPU-bound APU that adds load time plus one big conditioning pass per clip. recovered_8b replaces it with a recovered Qwen3-VL-8B architecture (24 language layers) + ARA + a 4096→5120 adapter, ~6 GB peak, same `[seq,5120]` output the DiT expects.

## Installed by default on this box
- Custom node: `ComfyUI/custom_nodes/ComfyUI-MiniMaxH3TextEncoders` (kgonia / publisher searchingman). Zero pip deps; registers `MiniMaxH3TextEncoderLoader`. Reads packages from `ComfyUI/models/text_encoders/<package>/`.
- Package dir `ComfyUI/models/text_encoders/recovered_8b/`:
  - `minimax_h3_recovered_8b_manifest.json` — node keys its choice list off this; `format` must equal `minimax_h3_recovered_8b_release_v1`.
  - `qwen3vl_8b_minimax_h3_recovered_int8_convrot.safetensors` (~5.9 GB) — base (INT8 ConvRot).
  - `ara.safetensors` (~29 MB) — additive refinement layers.
  - `conditioning_adapter.safetensors` (~93 MB) — 4096→5120 projection, applied inside the loader.
- Node choices are `{dir}: {variant}` → e.g. `recovered_8b: recovered_8b_int8_convrot`. h3_t2v.py defaults to this string; `--encoder official` uses CLIPLoader + stock 32B instead.

## Install / recover recipe
1. Node (if missing): `git clone --depth 1 https://github.com/kgonia/ComfyUI-MiniMaxH3TextEncoders.git` into `custom_nodes/`. No pip install (`dependencies = []`).
2. Package files: download the three `.safetensors` + manifest from `SearchingMan/MiniMax-H3-Text-Encoders` into `text_encoders/recovered_8b/`. Use the `/resolve/` endpoint (`https://huggingface.co/<repo>/resolve/main/<path>`) — it 302-redirects through the XET CDN and returns correct headers; `/raw/` can 404.
3. Verify SHA-256 against the manifest before use — the loader refuses a hash mismatch. int8 base sha256: `76d4f3d02ce7feec361369826c88ac305f220cabe021805cca1d106ead361d25`.
4. Skip the bf16 base (10.5 GB) unless you specifically want bf16; int8_convrot is smaller and faster here.
5. Restart ComfyUI so the node registers, then confirm with `GET /object_info/MiniMaxH3TextEncoderLoader` that the choice string matches what the tool passes.

## Limitations (active whenever recovered_8b is the encoder)
- Text-only T2V. The loader raises on image-to-video, first-frame, last-frame, and reference inputs.
- Proper nouns and non-English spoken lines degrade; describe people instead of naming them. Counting/unenumerables unreliable (also true of 32B).

## Alternatives decision table
| Option | Size | Quality | When |
|---|---|---|---|
| recovered_8b int8_convrot (default) | ~6 GB | good for scenes, weaker on names | fast runs, nature/scene prompts |
| recovered_8b bf16 | ~10.5 GB | best of the 8B family | VRAM allows, want max 8B fidelity |
| official 32B NVFP4/AWQ | ~16 GB | reference | named characters, non-English dialogue, image/frame inputs |
| ClipProj (nicolab28) + Qwen3-VL-4B/8B | 4.5–6 GB | learned projection, test cosine ~0.71–0.80 | VRAM-poor; more setup (custom node + base encoder + projection files); proper-noun degradation similar |
