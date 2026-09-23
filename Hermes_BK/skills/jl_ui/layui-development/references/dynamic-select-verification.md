# layui 動態 select 驗證與全域變數除錯參考

## 問題模式（suanming 專案 T-09 實例）
首頁八字排盤的「月份 / 日期下拉選單無法輸入」，根因有三：
1. `#baziMonth` 在 HTML 只有單個 `<option value=9>月</option>`，JS 從未填充 1~12 月。
2. `fillDays()` 用裸變數 `L.isLeap(y)`，但全域只有 `window.Lunar`、沒有全域 `L` → 載入時拋 TypeError，日選單也沒產生。
3. 動態插入 option 後未呼叫 `form.render('select')`。

## Node.js vm sandbox 驗證法（不依賴瀏覽器）
用 `vm.createContext` 建立 `window === global` 的 sandbox，依序載入 `lunar.js → bazi.js → app.js`，mock `document` / `layui.use`。關鍵 mock 要點：

- **`innerHTML` setter 要清空 children**（真 DOM 行為）：
  ```js
  Object.defineProperty(el, 'innerHTML', { get(){return ''}, set(v){ el.children = []; } });
  ```
- **`addEventListener` 要把陣列存回**（經典 JS bug：`(el._listeners[e]||[]).push(f)` 只 push 到暫存陣列，沒存回去）：
  ```js
  el.addEventListener = function(e,f){ (el._listeners[e] = el._listeners[e] || []).push(f); };
  ```
- **`layui.use` 要能回呼**：`use: function(mods, cb){ cb && cb(mock) }`
- 用 `fire('change')` 觸發 handler 來驗證月份→日期的聯動。

## puppeteer-core + headless Chrome 實測法（真瀏覽器 ground truth）
當 browser_exec 工具需要手動授權 Chrome 遠端除錯時，可改用：
1. `google-chrome --headless=new --remote-debugging-port=9333 --user-data-dir=/tmp/chrome-tp http://localhost/ &`（背景啟動）
2. `npm install puppeteer-core`（若未安裝）
3. 用 `puppeteer.connect({ browserURL: 'http://127.0.0.1:9333' })` 連上，`page.goto(...)` 後 `page.evaluate()` dump DOM：
   ```js
   const opts = sel => Array.from(document.querySelectorAll(sel+' option')).map(o=>({v:o.value,t:o.textContent}));
   // 驗證 #baziMonth.length===12、#baziDay 依月份天數正確（9月=30）
   // 模擬使用者選 2024/2 → dispatch change → 重測 #baziDay.length===29
   ```
注意：puppeteer-core v25+ 已移除 `page.waitForTimeout()`，改用 `await new Promise(r=>setTimeout(r,ms))`。
`--dump-dom` 抓不到 JS 動態產生的 option（app.js 在 client-side 執行），必須用 evaluate 在頁面載入後讀取 DOM。

## 日數陣列備忘（平年每月天數）
`[31,28,31,30,31,30,31,31,30,31,30,31]`，index = 月份-1。閏年二月用 `window.Lunar.isLeap(y)` 判斷 → 29。
「30 days has September, April, June, November」可用来交叉驗證：9/4/6/11 月應為 30 天。
