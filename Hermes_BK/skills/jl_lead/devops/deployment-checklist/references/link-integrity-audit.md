# 全站超連結完整性巡檢 (Link Integrity Audit)

## 為什麼 curl alone 不夠（本技法的動機）

curl 只能證明「檔案存在、Apache 回 200」，但**偵測不到瀏覽器實際點擊後的跳轉結果**。
典型的盲區是「相對連結」：一個 `href="cate/geju.html"` 在首頁根目錄解析正確（→ `/cate/geju.html`），
但當使用者已經在子目錄頁面（如 `/type/dianji.html`）時，同一個相對連結會被瀏覽器解析成
`/type/cate/geju.html` → **404**。curl 直接 curl `cate/geju.html` 永遠回 200，看不出來。

## 核心方法：逐頁解析 + 逐一 curl 驗證

對部署根目錄下的**每個 HTML 檔案**：
1. 讀取該頁所有 `href="..."` / `src="..."` 引用（排除 `../` 資源引用、絕對 URL、`#top`）。
2. **把每個相對連結，相對於「該檔案所在的目錄」**做解析（不是相對於根目錄）。
3. 對每個解析後的絕對路徑 curl 一次，記下狀態碼。
4. 標記任何 `404/500`，以及任何落在錯誤子目錄的連結（例如從 `/type/dianji.html` 解析出 `/type/cate/...`）。

### 判定準則
- **真正的斷链**：解析後 curl 回 404/500。
- **相對連結陷阱**：解析後的 URL 落在「該檔案本不屬於的子目錄」（如 `/type/cate/`、`/type/blog/`），即使目前回 200（因為碰巧有同名檔）也代表從該頁點擊會崩潰。**修法 = 把導覽連結改成絕對路徑**（加 `/` 前綴）。
- **正常情況**：檔案在 `/cate/`，相對連結 `geju.html` 解析成 `/cate/geju.html`（200）→ 正確，不用動。

## 「空殼」頁面偵測（curl 看不到的崩潰）

有些頁面 curl 回 200、HTML 結構完整（有表單/按鈕），但**瀏覽器實際渲染是空白或內容沒顯示**——
這是執行時 JS 報錯（API 404、ReferenceError、`form.render()` 失敗等）。curl 無法偵測。

偵測方法（任一）：
- **瀏覽器截圖 + 視覺確認**：用 CDP / browser tool 實際載入並截圖，看畫面是否有實質內容。
- **body text length**：載入後讀 `document.body.innerText.length`，接近 0 = 空殼。
- **console error 監聽**：導航時收集 `Runtime.consoleAPICalled` / `Page.error`，抓 error/404/undefined/ReferenceError。

## 完整巡檢腳本（可直接重跑）

參見同目錄的 `scripts/link-integrity-audit.py`——遍歷部署根目錄所有 HTML，逐頁解析相對連結並 curl 驗證，
輸出每個問題連結：來源頁面、原始引用、解析後的實際 URL、HTTP 狀態碼。

## 常見根因與修法

| 症狀 | 根因 | 修法 |
|---|---|---|
| 從首頁點正常，進子目錄後全崩 | nav/footer 用相對連結（`cate/x.html`） | 改成絕對路徑（`/cate/x.html`），加 `/` 前綴 |
| 特定子頁面的 JS 引用崩潰 | `src="../js/type/dianji.js"` 解析正確但檔案位置不對 | 確認 src 相對於該頁目錄解析後指向真實存在的檔案 |
| 頁面能載入但空白（空殼） | 執行時 JS 報錯，非 HTTP 問題 | 用瀏覽器截圖 + console error 定位，不是再 curl |
| 使用者回報「還是一樣」 | 瀏覽器快取舊版靜態檔 | 通知 Ctrl+Shift+R / 無痕模式；或連結加 `?v=N` |

## 本技法實際抓到的案例（2026-09-15）

- `/type/dianji.html` 的 components.js 用相對連結 → 從該頁點擊解析成 `/type/cate/geju.html` → 404。
- 修法：把 `components.js`（17 個連結）與首頁 `index.html`（30 個連結，靜態 nav+footer）**全部改成絕對路徑**。
- 修後全站巡檢：20 頁 / 166 個引用 / **0 斷链**、0 錯誤 `/type/` 前綴。
