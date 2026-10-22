---
description: 把 AI .glb 網格修成可列印封閉 STL——先判連通性，pymeshfix 補洞，碎塊靠改善輸入。
name: 3d-print-mesh-repair
---

## 何時用
用戶要把單圖轉 3D 的輸出（Hunyuan3D / TripoSR / InstantMesh 等 .glb/.obj）拿去 3D 列印。列印要求「單一、實心、流形(watertight)網格」。AI 輸出常是空殼+破面，需修補。

## 關鍵判斷：連通塊數能不能封閉
- **單一連通塊 (block=1)**：只有破洞 → pymeshfix 一次就能完全封閉（實測派大星 boundary 1088→0）。
- **碎裂成多塊**（扁平/糟糕輸入圖會這樣，Hunyuan3D 可碎成上千塊）：補洞只能關每塊的洞，塊連不回一起 → **補洞救不了，必須改善輸入圖**。這是主要失敗來源。

## 已驗證能封閉的配方（pymeshfix，即 ComfyUI-3D-Pack Auto Hole Fill 底層）
```python
import trimesh, numpy as np, pymeshfix
m = trimesh.load("in.glb", force="mesh", process=False)
pm = pymeshfix.PyTMesh(); pm.set_quiet(1)
pm.load_array(np.ascontiguousarray(m.vertices,dtype=np.float32),
              np.ascontiguousarray(m.faces,dtype=np.int64))
pm.fill_small_boundaries()     # 補邊界洞（關鍵）
pm.fix_connectivity()          # 修法向/連通
pm.join_closest_components()
out = trimesh.Trimesh(vertices=pm.return_points(), faces=pm.return_faces())
out.export("out.stl")
```
- 比 trimesh.repair.fill_holes 強（trimesh 對這些網格封不成）。
- 有縫合頂點可先 snap 合併：`q=round(v/eps); remap faces; 去退化面`，但 eps 會讓網格坍縮需試 (0.02 常太狠)。

## STL 驗證（別被假破騙）
binary STL 每三角獨立存 3 頂點、不共享 → trimesh.is_watertight 會 False。正確：先 snap 合併同座標頂點再算邊界邊，boundary==0 才是真封閉。slicer 匯入會 weld，幾何封閉即可印。

## ComfyUI 整合（若要用節點）
- 正確 repo：**MrForExample/ComfyUI-3D-Pack**（不是 cubiq，cubiq 已 404）。含 Make Manifold + Auto Hole Fill。
- 完整 requirements 是 CUDA 專用（spconv-cu126/nerfacc/slangtorch），AMD/ROCm 裝不全；修補節點只需 trimesh+pymeshlab+open3d。
- 自訂節點需**重啟 ComfyUI** 才會載入——無法遠端觸發。
- 對 AMD/ROCm 更輕的路徑：只在 venv `pip install pymeshfix`，用上面腳本轉 STL，避開整個重包。

## 此環境已知坑
- ComfyUI = Windows portable + AMD/ROCm；嵌入式 Python **3.12 win_amd64**；已有 torch 2.9.1+rocm、numpy 2.5.3、scipy、networkx、pillow、safetensors；**無 trimesh/open3d/pymeshlab**。
- Agent VM 是 Linux，執行不了他們的 python.exe（格式錯誤），無法遠端 pip；可下好 Windows wheel 手動解包進 site-packages，但原生庫風險高易衝突。
- Hunyuan3D GLB header 非標準：區塊從 offset **12**、offset8=檔案大小；bin_start=chunk off+8。要容錯走區塊解析。

## 結論句
「正常重建網格（單一連通塊）用 pymeshfix 補洞可封閉可印；碎裂是輸入圖問題，補洞救不了，要換真實物體圖片重生成。」