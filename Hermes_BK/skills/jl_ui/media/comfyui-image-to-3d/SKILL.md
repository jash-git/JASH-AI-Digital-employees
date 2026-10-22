---
name: comfyui-image-to-3d
description: "Convert images to 3D models via this box's ComfyUI MoGe."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux]
metadata:
  hermes:
    tags: [ComfyUI, 3D, MoGe, AMD, GLB]
---

# ComfyUI 圖轉 3D（AMD/ROCm，已實測）

本機 ComfyUI 0.39 核心內建 2D→3D 能力。**MoGe 路徑已安裝並實測通過**；Hunyuan3D v2 核心在但權重/接線不乾淨（見下）。

## When to use

Use when the user wants to turn one or more images into 3D models (.glb/.obj) through this box's ComfyUI, or when auditing what 2D→3D capability this ComfyUI already has. Also use to run the batch converter or to fix the SaveGLB lowercase-glTF magic quirk.

## 環境事實
- ComfyUI URL：`http://10.0.2.2:8188`（VM 內網）／本機 `http://127.0.0.1:8188`
- 掛載：`/media/sf_ComfyUI_windows_portable`（Windows portable，可直讀寫）
- GPU：AMD Strix Halo 整合顯存（報告的 torch_vram≈2MB 是誤報，勿據此判可行性）
- PyTorch `2.9.1+rocm7.2.1`；**不需 pytorch3d**（網格生成/I/O 皆原生 torch）
- object_info 有 978 節點

## MoGe 路徑（推薦，已驗證）
模型：`models/geometry_estimation/moge_3_vitl_fp16.safetensors`（~706MB，來源 Comfy-Org/MoGe HF）。v1/v2/v3 checkpoint 自動偵測。

節點鏈（API format）：`LoadImage` → `LoadMoGeModel` → `MoGeInference`(resolution_level=9, refine_steps=3) → `MoGePointMapToMesh`(decimation=2, texture=true) → `SaveGLB`。

存檔位置：ComfyUI 寫入 `output/*.glb`。注意本版 `SaveGLB` 寫出**小寫 magic `glTF`**（規範應大寫），嚴格檢視器可能拒讀——用下方批次腳本會自動修正为大寫。

### 單張 workflow JSON（POST /prompt，body `{"prompt": <json>, "client_id":"x"}`）
```json
{
 "1":{"class_type":"LoadImage","inputs":{"image":"你的圖片.png"}},
 "2":{"class_type":"LoadMoGeModel","inputs":{"model_name":"moge_3_vitl_fp16.safetensors"}},
 "3":{"class_type":"MoGeInference","inputs":{"moge_model":["2",0],"image":["1",0],"resolution_level":9,"fov_x_degrees":0,"batch_size":1,"force_projection":true,"apply_mask":true,"refine_steps":3}},
 "4":{"class_type":"MoGePointMapToMesh","inputs":{"moge_geometry":["3",0],"batch_index":0,"decimation":2,"discontinuity_threshold":0.04,"texture":true}},
 "5":{"class_type":"SaveGLB","inputs":{"mesh":["4",0],"filename_prefix":"moge_out"}}
}
```
實測結果：`卡通_胖胖貓頭鷹_頭像.png` → 26,937 頂點 / 52,840 三角面 / 貼圖 GLB。

## 批次轉換（已實測 3/3 成功）
腳本：`千問文字產圖AI/批量圖轉3D.py`（純標準庫 urllib；可改 `--input/--base-url/--output-dir`，或 env `COMFYUI_BASE_URL/INPUT/OUTPUT`）。掃輸入資料夾所有圖片 → 逐一 MoGe → 匯出 GLB 並自動修正 magic。跳過 `3d/` 子夾與 `_`/`put_` 開頭提示檔。
執行：`python "千問文字產圖AI/批量圖轉3D.py" --input ComfyUI/input --base-url http://10.0.2.2:8188`

## 驗證輸出 (.glb) — 每次轉換後必做
轉換完用 `python "千問文字產圖AI/檢查3D檔案.py" ComfyUI/output`（同批次腳本目錄）逐支報：頂點/三角面數、有無貼圖、有無 UV、bounding box 尺寸。有效網格應為 mesh≥1、頂點>0、UV=是、尺寸約 1 單位尺度；「頂點=0」或「尺寸=0」才是壞的。
寫自檢解析器時避這三個踩過的坑：
- **UV 屬性名是 `TEXCOORD_0`，不是 `UV`**——用 `"UV" in attrs` 檢查會把有效網格誤判成「無 UV」。
- **magic 可能小寫 `glTF`**（ComfyUI `SaveGLB` 的瑕疵，規範應大寫 `GLTF`）——解析要同時接受 `b"GLTF"`/`b"glTF"`，否則會漏判或拒讀有效檔。
- **算 bounding box 逐軸聚合**（`zip(*mins)` 後取 min/max），別對座標 tuple 直接用 `min()`——會對 (x,y,z) 做字典序比對而非每軸最小，尺寸會錯。

## Hunyuan3D v2（高品質/含背面 — 未落地）
核心 `comfy/ldm/hunyuan3dv2_1` 已註冊，DiT 可用 `UNETLoader` 從 `diffusion_models/` 載。但官方 repo `tencent/Hunyuan3D-2` **無乾淨獨立 CLIP-Vision 編碼器**供 DiT 路徑用（影像編碼器藏在 paint 模型內），且需 DiT(~5GB)+體素 VAE + 未驗證的自變數 latent→KSampler→VAEDecodeHunyuan3D 接線。故未安裝死重量；MoGe 為現行可行方案。若強上要試：DiT 用 `hunyuan3d-dit-v2-0/model.fp16.safetensors`、VAE 用 `hunyuan3d-vae-v2-0/`，並需自行定位 vision encoder + 接 workflow。

## Caveats
- MoGe 單视角重建：還原可見面，不生成被遮擋背面；品質依賴輸入圖清晰度與背景簡潔度。
- `decimation`↑ 網格越稀疏越快；`discontinuity_threshold`↑ 裁掉深度突變像素。
- 要 360° 完整需用 Hunyuan3D v2 / 多視角。