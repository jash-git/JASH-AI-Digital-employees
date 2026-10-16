# Provider Probe Recipes

Cheap single-call checks to confirm an external generation backend works before committing a full run. Mask secrets; never print full key values. Use short prompts and the smallest sizes to minimize cost.

## Generic endpoint probe
```bash
key=$(grep -m1 "^VAR_NAME=" ~/.hermes/.env | cut -d= -f2-)
[ -z "$key" ] && echo "no key" && exit
curl -s -o /dev/null -w "HTTP %{http_code} (%{time_total}s)\n" --max-time 45 \
  URL -H "Authorization: Bearer $key" -H "Content-Type: application/json" \
  -d '{"prompt":"a red circle","width":256,"height":256}'
```
A non-2xx usually means do not commit: 401 = bad/empty key or no image permission; 404/501 = model not offered; connection refused = server down.

## Image providers
- OpenAI images: `POST https://api.openai.com/v1/images/generations` — model e.g. `gpt-image-1`; body `{"model":..., "prompt":..., "num_images":1, "size":"256x256"}`.
- Stability AI: `POST https://api.stability.ai/v1/generation/diffusion-text-to-image`.
- SiliconFlow: `POST https://api.siliconflow.cn/v1/images/generations`.
- Replicate: `POST https://api.replicate.com/v1/models/<owner>/<model>/predictions`.

## Local backends (no key)
ComfyUI / Stable Diffusion WebUI: probe the HTTP port rather than an API key — curl the server root or a `/system_stats` or health endpoint. Connection refused means it is not running. See the `comfyui` skill for its own setup.

## Credentials check (the trap)
```bash
for k in OPENAI_API_KEY STABILITY_API_KEY SILICONFLOW_API_KEY; do
  line=$(grep -m1 "^$k=" ~/.hermes/.env); echo "$k : value_len=${#line#*=}"
done
```
A key name present with `value_len=0` is declared-but-empty — the usual reason a probe returns 401 despite the key appearing configured.
