---
description: 修 ComfyUI glb 在 donmccundry 空白——改小寫 magic 與 offset8；並用 glb_preview.py 產單檔案預覽頁。
name: view-comfyui-glb
---

# 處理 ComfyUI image-to-3d GLB 在檢視器空白的問題

## 完整流程：輸入圖 → 網格 → 驗證 → 修正（如需）→ 預覽
本技能管「image-to-3D GLB」全程。第一步產生網格不寫死在本文件，改呼叫既有腳本 `h3d_run.py`（Hunyuan3D v2.1），之後才用下面的 glb_validate / 修正 / glb_preview。

**1. 產生 GLB**（`/home/vblinux/h3d_run.py`；stdlib only，loading 跑在遠端 ComfyUI）：
```bash
python3 /home/vblinux/h3d_run.py --image <輸入圖> [--resolution 512] [--steps 25] [--octree 256]
```
- 權重（DiT 7.37GB / VAE 655MB / DINOv2-L 1.22GB）預先下在 `ComfyUI/models/`、大小對就跳過下載；缺才會自動下。
- ComfyUI host 預設 `http://10.0.2.2:8188`（`--host` 改）。輸入圖路徑含中文字也行（Linux UTF-8）。
- 輸出固定落在 `ComfyUI/output/3d/h3d_NNNN_.glb`。腳本會輪詢到 size>0 才回報（修過落盤競態，log 偶因執行中被中斷而為空——重跑即可續）。

**2. 驗證**：對新檔跑 `scripts/glb_validate.py x.glb`（見下）。PASS✅ 即確定能在 donmccundy/THREE 渲染，流程可結束。
**3. 修正**：FAIL（大寫 magic / offset8 錯）才動 header 12 位組（见下方）。
**4. 預覽**：`scripts/glb_preview.py x.glb` 產 `_預覽.html`，雙擊即開（自包含、不受 magic 坑影響），作為「真看得到的」最終保險。

> 瀏覽器實測（browser_exec 開 `_預覽.html` 看 INFO「✅ 模型已渲染」、console.error=0）是最強證據，但**非必需**：若本 session 的自動化 Chrome（CDP :9222）沒在跑，glb_validate.py PASS 已是充分結論——它忠實模擬 THREE 解析分支，不等於沒測。別因開不了瀏覽器就停在中間、只交一個沒驗證的檔。

## 真正根因（已用 THREE 原始碼 + 瀏覽器實測確認）
gltf-viewer.donmccurdy.com 用的是 THREE r160 的 `GLTFLoader`。它的 `parse()`（GLTFLoader.js 第 312-352 行）對 ArrayBuffer 這樣判斷：

```js
const magic = textDecoder.decode(new Uint8Array(data,0,4));   // 讀前 4 字節
if (magic === BINARY_EXTENSION_HEADER_MAGIC) { ...走區塊解析... }  // 第 1797 行:
else { json = JSON.parse(textDecoder.decode(data)); }           // 把「整個二進位檔」當 JSON parse
```

其中 `BINARY_EXTENSION_HEADER_MAGIC = 'glTF'`（**小寫** g、l，第 1797 行）。

- **小寫 `glTF`** → 匹配 → 走 GLTFBinaryExtension 區塊解析分支 → 抽出 JSON → 成功。
- **大寫 `GLTF`**（glTF spec 的正規寫法 0x46544C47）→ **不匹配** → 掉進 else，去 `JSON.parse(解碼整個二進位檔)` → 遇到 'G' → **「Unexpected token 'G', "GLTF..." is not valid JSON」**（即 donmccundry 的錯誤訊息），畫面空白。

另外 GLTFBinaryExtension 讀區塊時用 `chunkContentsLength = header.length - 12` 當迴圈邊界（header.length = offset 8 的欄位）。若它太小（小於實際區塊總長）→ **「JSON content not found」**。所以 offset 8 必須是**區塊資料總字节數（≈檔案大小）**，不是區塊數量。

**結論（反直覺但實測如此）**：spec 正規的大寫 `GLTF` + 正確區塊數反而開不了；能開的是小寫 `glTF` magic + offset8=檔案大小（mikedh/trimesh 的 cube.glb 就是這樣，到處都能開）。ComfyUI exporter 出大寫版所以壞。

## 本地快速預檢：glb_validate.py（先跑這個，不必開瀏覽器）
`scripts/glb_validate.py` 一次檢查「能否在 donmccundy 開啟」+「幾何是否有效」，不依賴 THREE/瀏覽器，適合批次掃 output 資料夾。
```bash
python3 scripts/glb_validate.py "*.glb"        # 批量；全部 PASS 回傳 0，有 FAIL/WARN 回傳 1（可接 CI）
python3 scripts/glb_validate.py x.glb           # 單檔
```
它會報告：magic 是否小寫、offset8 是否=檔案大小、頂點/三角形數、max_index 是否越界、邊界盒(x,y,z延伸+中心)、有無 NaN、有無 vertex normals。
- PASS✅ = magic 小寫 + offset8 OK + 幾何有效 → 可確定能在 donmccundy/THREE 正常開啟並渲染。
- WARN⚠️/FAIL❌ = 大寫 magic（→空白）或 offset8 錯（→JSON not found）或索引越界/NaN。這些就是 ComfyUI 檔開不了的原因。
- 它算出的邊界盒/頂點數與「真 THREE GLTFLoader r176 實測」一致（例：cube.glb → 8 頂點/12 三角/bbox 2×2×2；貓頭鷹 → 26937 頂點/bbox 1.25×1.40×0.46）。要「證明真的渲染出來」再走下面的瀏覽器實測。

## 封閉性：單面 vs 包覆（scripts/boundary_check.py）——glb_validate 不區分，需要時才跑
glb_validate.py 確認「開得開 + 幾何有效」，但**不分封閉與否**。單圖重建典型分成兩類，用戶要「背面/包覆」時必須量：
- **front-facing / 2.5D 方法（如 MoGe）→ 開網格**：背面有邊界、無後臉。
- **voxel / occupancy 方法（如 Hunyuan3D v2.1）→ 封閉流形**：等表層包一圈，有後臉、可包覆。
判定：**解三角形統計每條無向邊被使用次數，只被一個三角使用的邊 = 邊界邊**。boundary_edges==0 → 封閉（watertight）；>0 → 開網格（單面）。
```bash
python3 scripts/boundary_check.py "*.glb"      # 批次；可接 <dir>（遞迴）或指定檔，回傳 1=有解析失敗
python3 scripts/boundary_check.py x.glb
```
報告每檔：頂點/三角形/邊界邊數/closed。封閉與否不影響回傳碼（幾何有效才有意義，先過 glb_validate）。
> 換模型前先量這個再論品質：Hunyuan3D v2.1 即使安全 octree(256) 下只有 ~127 頂點（比 MoGe 的 ~2 萬少約 150 倍、看起來較粗），但它是**封閉有背面**；MoGe 細緻卻單面。要「包覆」就選前者，細節代價靠拉 octree（注意顯存/OOM）。

> ⚠️ 路由提醒：本技能側重「檢視/預覽/GLB magic 修正」。用戶若是要「可列印 / 轉 STL / watertight」→ 改調 `3d-print-mesh-repair` 技能（pymeshfix 修封閉 → STL），別用本技能的驗證流程當最終交付。

## 驗證幾何無誤（先確認不是壞檔）——手勢解析版（glb_validate.py 的內部邏輯）
用容錯 python 從 offset 12 走區塊到結束（不信任 numChunks），檢查：accessor 索引全小於頂點數、座標全 finite、至少一個 mesh 有 POSITION。符合幾乎即幾何沒問題，純是 header 讓 THREE 誤判。
- JSON chunk type=0x4E4F534A，BIN chunk type=0x004E4942（是 0x42 不是 0x44）。索引解碼要依 componentType 選寬度：UNSIGNED_BYTE→`<B`(1)、UNSIGNED_SHORT→`<H`(2)、UNSIGNED_INT→`<I`(4)，別一律用 `<I`。
- gltf-validator npm 包在某些環境（node v26 等）對**所有** glb 都失敗，是驗證器/環境問題，別當結論。以本腳本或瀏覽器實測為準。

## 修正（只動 header 12 位組，不碰資料，最安全）
```python
import struct
data = bytearray(open('in.glb','rb').read())
data[0] = 0x67   # 'G' -> 'g'
data[1] = 0x6C   # 'L' -> 'l'   （第 2、3 字節 'TF'=0x54,0x46 不用動）
struct.pack_into('<I', data, 8, len(data))   # offset8 -> 檔案總字节數
open('in_可視化_.glb','wb').write(bytes(data))
```
批量：對資料夾每個 `.glb` 跑上面三步，輸出 `_可視化_.glb`。若原檔已是小寫 `glTF`（有些已是），只修正 offset8 即可。

## 驗證修正結果（二選一，都要實測不要只信字面）
1. **Python 忠實模擬 THREE 解析**：檢查 magic==='glTF' → 用 GLTFBinaryExtension 邏輯（header.length-12 當邊界）抽區塊 → JSON 能 parse。能過即 THREE/donmccundy 一定能開。
2. **瀏覽器 + 真 THREE GLTFLoader**：建頁 `import {GLTFLoader} from 'three/...loaders/GLTFLoader.js'`，`loader.load(url)` 成功即 OK。（我自己的手勢解析預覽页不靠 GLTFLoader，不能證明 donmccurdy 看得懂，別用它當唯一證據。）

## 正式預覽工具（單檔案自包含，必看得到的保險方案）
`scripts/glb_preview.py`：把 .glb base64 內嵌進一個 HTML（three.js 手勢解析、自動對焦、打光、滑鼠互動）。因用 `.replace()` 填 base64（不用 str.format），不受 JS/CSS 花括号影響。雙擊即可開，不需伺服器、不受 magic/numChunks 坑影響。
```bash
python3 scripts/glb_preview.py "*.glb"          # 批量為每個 glb 產 _預覽.html
python3 scripts/glb_preview.py x.glb out.html    # 單檔 + 指定輸出
```
用 browser_exec 開該 html 確認 INFO 顯示「✅ 模型已渲染」且 console.error 為 0；必要時截圖 + vision_analyze 確認畫面真有模型。

## 交付與清理
- 主動區（output/）只留能開的：每個模型的 `_可視化_.glb` + `_預覽.html`。
- 修正後**仍打不開**的檔（極少見），移到 `unopenable_backup/`（可復原，不硬刪源檔），並告知用戶。
- vmware shared folder（/media/sf_*）的 ls 常顯示錯誤大小（如 770），實際大小看第二欄或用 python read 為準。

## 備註/代價
改成小寫 magic 是為相容 THREE r160/donmccurdy；極少數死守 spec 的檢視器可能不認小寫，但 donmccundry 與 trimesh 等主流都正常。若需同時顧 spec 正規性，可改 THREE 版本或用能正確解析的檢視器（如本技能的 _預覽.html）。