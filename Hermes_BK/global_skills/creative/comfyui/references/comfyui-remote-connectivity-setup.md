# 讓 Hermes 呼叫 ComfyUI：連線設定指南

## 我怎麼呼叫 ComfyUI

我的 comfyui 技能不是在本機跑 ComfyUI，而是透過 **REST / WebSocket API** 遠端呼叫：

- `POST /api/prompt` —— 送出 workflow 執行
- `GET /api/view`、`/api/upload/image` —— 讀取 / 上傳檔案
- `GET /system_stats`、`/object_info`、`/queue` —— 狀態與管理
- `WS /ws` —— 即時進度監控

所以「設定」的核心只有一件事：**讓我能連上那台主機的 API**。底下依「本機 / 遠端」兩種情況說明。

---

## 一、必要條件（兩種情況都要）

1. **ComfyUI server 正在執行**
   ```bash
   curl http://HOST:8188/system_stats
   # 回 JSON = 在跑；連不上 = 沒啟動或地址/埠錯
   ```

2. **至少安裝一個 checkpoint model**（否則跑不出圖）
   ```bash
   curl http://HOST:8188/object_info          # 看有哪些 node / model
   # 或 comfy CLI：comfy model list
   ```

3. **workflow 必須是 API format**
   - 每個 node 要有 `class_type` 欄位。
   - 從 ComfyUI UI：**Workflow → Export (API)**（新介面）或「Save (API Format)」（舊介面）。
   - Editor format（頂層有 `nodes`、`links` 陣列）**不能直接執行**，要重新匯出。

---

## 二、情況 A：ComfyUI 跟我在同一台（本機）

只要滿足上面三點即可，我直接用 `run_workflow.py` 連 `http://127.0.0.1:8188`：

```bash
curl http://127.0.0.1:8188/system_stats      # server 在跑嗎
curl http://127.0.0.1:8188/object_info        # 有 model 嗎
```

---

## 三、情況 B：ComfyUI 在遠端主機（不同 IP / GPU server）

除了上面三點，還要多設兩項：

### 1. 監聽地址要開（關鍵）

ComfyUI 預設只 listen `127.0.0.1`，**遠端連不進來**。啟動時必須加：

```bash
comfy launch --background --listen 0.0.0.0 --port 8188
# 或手跑 main.py：
python main.py --listen 0.0.0.0 --port 8188
```

### 2. 埠通防火牆

放行 TCP **8188**（伺服器安全組 + 主機 firewall）。測試：

```bash
nc -zv <遠端IP> 8188        # 或 telnet / curl
curl http://<遠端IP>:8188/system_stats
```

### 3. Auth（選用）

ComfyUI 核心預設**沒有登入驗證**。但如果你裝了需要憑證的 custom node 或 auth 外掛，要告訴我怎麼處理（例如 token、header）。

---

## 四、啟動指令速查（依安裝方式）

| 安裝方式 | 啟動（可遠端連） |
|---------|-----------------|
| comfy-cli | `comfy launch --background --listen 0.0.0.0 --port 8188` |
| 手跑 main.py | `python main.py --listen 0.0.0.0 --port 8188` |
| Comfy Desktop | 僅本機，無官方遠端 listen 參數（建議用 comfy-cli 或 portable） |

> 預設埠是 **8188**；想用其他埠就改 `--port`。

---

## 五、驗證連線（連通後這樣確認）

```bash
# 1. server 在跑？
curl -s http://HOST:8188/system_stats

# 2. 有 model 嗎？有哪些 node？
curl -s http://HOST:8188/object_info | head -c 500

# 3. 完整健康檢查（技能內建腳本）
python scripts/health_check.py --workflow <work>.json --smoke-test
```

---

## 六、實際生成（連通後）

我拿到你提供的 API format workflow JSON 後，注入參數送出：

```bash
python scripts/run_workflow.py \
  --workflow your_workflow.json \
  --args '{"prompt": "一個日落山景", "seed": -1, "steps": 30}' \
  --output-dir ./outputs
```

- `seed: -1`（或省略 + `--randomize-seed`）= 每次隨機新種子。
- img2img / inpainting：加 `--input-image image=./照片.png`，會自動上傳並注入。
- 即時進度：加 `--ws`（需 `pip install websocket-client`）。

---

## 七、常見問題

| 現象 | 原因 & 處理 |
|------|------------|
| `curl` 連不上 | server 沒啟動，或只 listen 127.0.0.1（遠端要加 `--listen 0.0.0.0`），或埠被防火牆擋 |
| 「class_type not found」 | 缺 custom node → `comfy node install <名稱>` |
| model 名對不上 | model 檔名大小寫敏感，用 `comfy model list` 確認正式名稱 |
| workflow 無法執行 | 是 editor format，要重新 Export (API) |
| 遠端 free tier 403 | 若用 Comfy Cloud，免費方案 `/api/*` 全 403，需付費方案 |

---

## 八、我需要你回報的三件事（給精確指引用）

1. 那台是**本機還是遠端**？
2. **作業系統**（Linux / Windows）+ **GPU**（NVIDIA / AMD / Mac）？
3. ComfyUI 是怎麼啟動的（comfy-cli、Desktop、手跑 main.py）？

方便的話，先貼上面「第五節」兩條 curl 的結果，我能直接幫你還缺哪一步。
