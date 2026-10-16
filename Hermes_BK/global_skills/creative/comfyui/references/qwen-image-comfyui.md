# Qwen-Image in ComfyUI (agent-driven)

Domain notes for running Alibaba Qwen-Image 2.x (text-to-image + image editing)
t through ComfyUI so the agent can drive it via REST/WebSocket. The agent's
generation path is model-agnostic; this file covers the parts specific to the
Qwen-Image model family: placement, the GGUF-vs-native fork, and the VRAM gate.

## Model placement (three-file stack)

| Role | File type | Folder |
|---|---|---|
| Diffusion model (the DiT generator) | `.gguf` or `.safetensors`/`.pt` | `models/diffusion_models/` |
| Text encoder / multimodal conditioning (`type: qwen_image`) | `.safetensors` | `models/text_encoders/` |
| VAE (latent -> visible image) | `.safetensors` | `models/vae/` |

## GGUF vs native path (pick one; do not mix loaders)

- **GGUF path** — `.gguf` diffusion weights are NOT loadable by the standard
  `Load Diffusion Model` (UNETLoader) node. They require the `ComfyUI-GGUF`
  custom node, which adds `Unet Loader (GGUF)` / `QwenImageModelLoader`. If
  `/object_info` shows zero GGUF nodes, this node is not installed and the
  model cannot run — install it before expecting a generation.
- **Native path** — ComfyUI >= 0.37 ships native Qwen-Image-2.1 nodes
  (`TextEncodeQwenImage21`, `QwenImageTextToImageApi`, `QwenImageEditApi`).
  Use the standard UNETLoader for `.safetensors`/`.pt` diffusion weights here;
  no GGUF node needed, but VRAM cost is higher.

## VRAM gate (the thing that actually blocks a run)

Numbers are GPU-VRAM on a real accelerator, not system RAM:

- **GGUF Q4_K_M** diffusion + INT8 text encoder: ~11 GB VRAM. The text encoder
  encodes once per prompt and can offload to system RAM, saving 9–17 GB VRAM.
- **INT8 / FP8 native** weights: ~24 GB VRAM. bf16 native is heavier still.

A host that cannot hold the diffusion model in VRAM will OOM or run at
unusable speed regardless of how much system RAM it has. See host check below.

## Host feasibility check (promise a run only after this)

Probe the target ComfyUI's `/system_stats`. The number that matters is
`devices[].torch_vram_total` — what PyTorch actually has available for compute.
Do NOT trust top-level `vram_total`: on integrated / APU GPUs it reports shared
system memory that cannot be used for diffusion kernels, so `torch_vram_total`
comes back tiny (MB-scale). A host whose torch sees only MB of VRAM cannot run a
7B-class DiT no matter how large its system RAM is. Also read `system.argv` —
flags like `--enable-dynamic-vram` / `--lowvram` and the build tag (+rocm /
directml / cpu) reveal the real backend.

## Driving it with the agent

- The agent submits an API-format workflow (each node has `class_type`) to
  `/api/prompt` via `run_workflow.py --host <target>`; no comfy-cli needed on
  the agent side. Works for Qwen Image once nodes + models are in place.
- Need a workflow JSON? Either export "Workflow -> Export (API)" from the UI, or
  supply one wiring: GGUF loader (or native UNETLoader) + `qwen_image` text
  encoder + KSampler + VAEDecoder + SaveImage. Verify node class_types against
  the live `/object_info` before submitting.

## Reference links

- Comfy-Org/Qwen-Image-2.1 placement guide: https://huggingface.co/Comfy-Org/Qwen-Image-2.1
- Qwen-Image-2.1 Uncensored GGUF (Q4_K_M) + VRAM notes: https://huggingface.co/Janchan123/Qwen-Image-2.1-Ucensored-GGUF
- ComfyUI-GGUF custom node: https://github.com/LighTOS-AI/ComfyUI-GGUF
- Unsloth Qwen-Image-2.1 VRAM summary: https://unsloth.ai/docs/models/qwen-image-2.1
- ComfyUI native Qwen-Image tutorial: https://docs.comfy.org/tutorials/image/qwen/qwen-image
