---
name: comfyui-qwen-image-gguf
description: Run Qwen Image 2.1 GGUF models through ComfyUI's API.
version: 0.1.1
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [comfyui, gguf, qwen-image, amd, low-vram, image-generation]
    related_skills: [comfyui]
---

# ComfyUI Qwen Image GGUF Skill

把 GGUF 量化的 Qwen Image 2.1（或其他 GGUF 生成器）接到 ComfyUI，並用 comfyui skill 的 API 路徑下單生成。專為 AMD / 低显存環境設計（GGUF 才需要），核心是 city96 的 `ComfyUI-GGUF` 自訂節點。

依賴 comfyui skill（負責執行/計時）；本 skill 補上 GGUF 專屬的安裝、一行 patch、模型擺放、editor→API 轉換與 REST 下單。不處理原生 safetensors 路線（那不需要 GGUF 節點）。

## When to Use
- 用戶有 Qwen Image 2.1 的 `.gguf` 生成器權重，想在 ComfyUI 跑、且要我的 SKILL 驅動。
- 在 AMD / 低显存上用 GGUF 量化而非原生 safetensors。
- ComfyUI 拋 `Unexpected architecture type in GGUF file: 'qwen_image21'` → 需要 patch。
- 要把 ComfyUI 編輯器格式 workflow（`"type":`）轉成 API 格式（`"class_type":`）給 run_workflow.py。
Don't use for: 原生 safetensors 的 Qwen Image workflow、或沒有 GGUF 載入器的其他 diffusion。

## Prerequisites
- 一台可透過 HTTP 連上的 ComfyUI（先驗：`terminal`: `curl -s http://HOST:8188/system_stats`）。
- comfy-cli 非必需；走 REST + comfyui skill 腳本。

## Environment / paths（參數化，勿寫死）
- `COMFY_HOST`：如 `http://10.0.2.2:8188`
- `COMFY_ROOT`：ComfyUI 安裝根目錄（Windows 主機路徑，或 agent 可寫的掛載點）
- 自訂節點：`$COMFY_ROOT/ComfyUI/custom_nodes/`
- 模型：`$COMFY_ROOT/ComfyUI/models/{diffusion_models,text_encoders,vae}/`

## Procedure
### 1. 裝 city96 ComfyUI-GGUF 節點
`terminal`: `git clone https://github.com/city96/ComfyUI-GGUF.git` 進 custom_nodes/（或下 master zip，解壓到 custom_nodes/ComfyUI-GGUF/）。確認 repo 是 **city96**（4k star 那個熱門版）；其他 fork 可能沒有要的節點。
完成準則：資料夾存在於 `$COMFY_ROOT/ComfyUI/custom_nodes/ComfyUI-GGUF`。

### 2. 在 ComfyUI 內嵌 Python 裝 `gguf` 依賴
此節點需 `gguf` 套件；numpy 通常已隨 ComfyUI 提供。若 agent 能寫進內嵌 site-packages（掛載上）：
`terminal`: `pip download gguf --no-deps -d /tmp/ggufdl` → 解壓 wheel → `cp -a /tmp/ggufdl/gguf <site-packages>/gguf`（純 Python，可直接複製）。
若碰不到內嵌 Python，給用戶這行在其 ComfyUI 資料夾執行：
`.\python_embeded\python.exe -s -m pip install -r .\ComfyUI\custom_nodes\ComfyUI-GGUF\requirements.txt`
完成準則：ComfyUI 的 python 能 `import gguf`。

### 3. PATCH — 把 qwen_image21 加入支援架構（關鍵）
city96 loader 只列 "qwen_image"；2.1 GGUF 的 metadata arch 是 "qwen_image21" → 節點拋 `Unexpected architecture type`。用 `patch` 改 `$COMFY_ROOT/ComfyUI/custom_nodes/ComfyUI-GGUF/loader.py` 約第 12 行：
old: `IMG_ARCH_LIST = {..., "qwen_image"}`
new: `,` 後加 `"qwen_image21"`
這是**唯一需要的程式碼變更**——後面載入邏輯對圖像模型只去前綴 + dequant，與 qwen_image 同族 DiT、路徑一致。
⚠️ 重裝/更新該節點會這行消失，要再補。完成準則：`patch` 後 grep 確認 `qwen_image21` 在 IMG_ARCH_LIST 中。

### 4. 擺三檔模型
- `diffusion_models/qwen-image-2.1-UC-Q4_K_M.gguf`（.gguf UNET 生成器）
- `text_encoders/qwen3vl_8b_int8_convrot.safetensors`（CLIP/編碼器）
- `vae/qwen_image_2.1_vae_bf16.safetensors`
完成準則：三檔在對應資料夾；`/object_info` 的 UnetLoaderGGUF/CLIPLoader/VAELoader 下拉能看到它們。

### 5. 重啟 ComfyUI 讓節點載入新邏輯
用戶在 Windows 重啟（`run_amd_gpu.bat` 或他們的啟動檔）。完成準則：伺服器回到 HOST、控制台無 ComfyUI-GGUF import 報錯。

### 6. 轉 workflow 成 API 格式（提交前必做）
comfyui skill 的 run_workflow.py 要 API 格式。常見失敗與修正：
- 頂層必須是「以 id 為鍵、每個有 `class_type`」的扁平節點 dict，**不要**包在 `nodes:` 下。
- Link 源節點 id **必須字串**：用 `["451", 0]`，別用 `[451, 0]`（整數會導致驗證期 KeyError）。
- KSampler 需要 `denoise` 輸入（預設 1.0）。
- SaveImageAdvanced 選 format 後還要 `bit_depth` + `input_color_space`；直接用 `SaveImage`（只要 images + filename_prefix）避開。
- 標準節點的 `class_type` 等於編輯器的 `type` 值。
完成準則：POST `/api/prompt` 回 prompt_id、無驗證錯誤。

### 7. 下單並計時（REST 或 run_workflow.py）
可用 comfyui skill 的 `run_workflow.py --host HOST --workflow api.json`；或直接 curl + 輪詢 history 拿權威耗時（回饋更快）：
`terminal`: `curl -X POST http://HOST:8188/api/prompt -H 'Content-Type: application/json' -d @prompt.json`
其中 prompt.json = `{"prompt": <扁平節點dict>, "extra_data": {"extra": {"pa_data": {}}}}`。
然後輪詢 `http://HOST:8188/history/<prompt_id>` 到 `status.completed == true`。讀 `outputs[].filename` 與 `execution_times[]`（毫秒）。注意：run_workflow.py 會緩衝 stdout 寫檔；快速迭代建議直接 curl + history。

### 8. 參考圖 + 提示詞（reference-guided）workflow
Qwen Image 2.1 支援「參考圖 + 提示詞」：參考圖被編碼器看見、以 VAE latent 形式拼進序列。節點 `TextEncodeQwenImage21`（在 ComfyUI/comfy_extras/nodes_qwen.py，非 GGUF 節點）負責，輸入含 `clip`、`prompt`、`negative_prompt`、`vae`、`resolution`、`images`。
- **`images` 是 autogrow 輸入**：API 用內聯 dict，key=`image_1`…（最多 16），value=`{"image":{"filename":"...","subfolder":"","type":"input"}}`。先 `curl -X POST /upload/image -F "image=@檔"` 上傳參考圖拿 filename。
- **連結一律 `[「id」,0]`**（字串 id + 整數輸出序）；勿用 `{"node":...}`（會當普通值傳入致 SaveImage `KeyError: 0`、整段不執行）。
- **三檔都要接**：`clip`←CLIPLoader(`clip_name="qwen3vl_8b_int8_convrot.safetensors","type":"qwen_image"`)、`vae`←VAELoader、`model`←UnetLoaderGGUF。漏 `clip` 會報 required_input_missing。
- **三個輸出**：positive(0)、negative(1)、latent(2)。KSampler 接 positive/negative/latent_image。
- `resolution`（≤1024，32 倍數）控制每張參考圖縮放大小；0 保留原尺寸。
- 存檔用 `SaveImage`（images + filename_prefix），避開 SaveImageAdvanced 的 format/bit_depth/input_color_space。
- 範本：`$COMFY_ROOT/千問文字產圖AI/_API_qwen_ref_workflow.json`。
完成準則：POST `/api/prompt` 回 prompt_id、無驗證錯誤、outputs 有圖片。

### 9. 透明背景貼圖（去背 + LINE 規格）
要做透明貼圖（如 LINE 上架：**PNG、RGBA 透明、375×375 px 靜態**），在生成流程尾端接「`VAEDecode` → `InspyrenetRembg` → `ImageScale(375)` → `SaveImage`」。
- **節點**：`john-mnz/ComfyUI-Inspyrenet-Rembg`（GitHub，~750★；city96 的 `ComfyUI-rembg` 不存在、勿裝）。clone 進 custom_nodes。依賴 `transparent-background`（含 onnxruntime 編譯版）→ agent VM 裝不了 Windows exe，**給用戶在 Windows 執行**：`.\python_embeded\python.exe -s -m pip install transparent-background`。重啟後 `/object_info` 確認有 `InspyrenetRembg`。
- **必 patch tensor2pil**（新版 `transparent-background` 預處理只吃 3 通道 RGB，收到 RGBA 會 `img -= self.mean` broadcast 崩潰、尺寸變掉）：在 `custom_nodes/ComfyUI-Inspyrenet-Rembg/Inspyrenet_Rembg.py` 的 tensor2pil 內加 `.convert("RGB")`（rembg 仍輸出 RGBA）。patch 後**需重啟**。
- **接法**：VAEDecode 輸出 → `InspyrenetRembg.image`；`ImageScale(width=375,height=375,upscale_method="lanczos",crop="center")`；`SaveImage`。
- **驗證透明**：agent VM python 缺 PIL、跑不了 Windows exe，用純 Python 讀 PNG IHDR 頭（color type=6 即 RGBA）+ 抽樣 alpha 算全透明%與邊緣漸層%。
- **可重放 workflow**：`$COMFY_ROOT/千問文字產圖AI/qwen_owl_sticker_API_workflow.json` + `qwen_owl_sticker_README.md`（改 prompt/seed 即可連續產系列）。
完成準則：outputs 的 PNG color type=6、alpha 有全透明區、尺寸 375×375。

## Pitfalls
- **別全信 ComfyUI system_stats 的顯卡/显存報表**（AMD 上可能誤報卡名與近零 torch VRAM，即使卡完全可用）。實測曾報 8060S / 2MB，真實裝置約 115GB 統一記憶體。用「真的跑一次」驗證能力，而非看報表。
- GGUF arch 字串必須與 IMG_ARCH_LIST 完全吻合（"qwen_image21" ≠ "qwen_image"）。
- 首次會先載模型+VAE（~30s）再取樣；總時 ≠ 取樣時，兩者都報。
- APU / 統一記憶體下每步會很慢（記憶體頻寬限制）：跑得動但不快。
- Windows portable 的自訂節點放 `custom_nodes/`（不是 nodes/）。

## Verification
- `/object_info` 有 `UnetLoaderGGUF`，且模型出現在其 `unet_name` 選項 → 節點+檔接好。
- POST `/api/prompt` 回 prompt_id、無驗證錯誤。
- `/history/<id>` 的 `status.completed == true`、outputs 有圖片檔名、execution_times 存在。
- 輸出圖落在磁碟（ComfyUI/output/），且可在 `http://HOST:8188/view?...` 開啟。

## Reference results（本環境實測）
Qwen Image 2.1 UC Q4_K_M、1024²、25 step euler/simple：取樣約 2:09、含載入總約 156s，跑在 AMD Ryzen AI Max+ 395（gfx1151、~115GB 統一記憶體）。純文字輸出 `qwen_test_00001_.png`。
參考圖模式（`qwen_test_00001_.png` 當參考 + watercolor restyle prompt）：含載入總約 130s，成功輸出 `qwen_ref_test_00001_.png`（~1.9MB）。autogrow `images` 內聯 dict 格式有效。