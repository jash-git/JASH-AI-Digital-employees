# 瀏覽器風格 JS（UMD）的 Node 驗證 + CDP Chrome 實測

本文件是 `jl-delegation-workflow` 的實戰補充，收錄 jl_lead 親身驗證、可直接貼上的 Node vm 載入模式與 CDP 實測姿勢。目的：讓主管在委派失敗（子代理卡在自測框架）時，能**獨立、快速**驗證核心邏輯是否正確，而非耗時除錯子代理的自測工具。

適用情境：`src/public/js/algo/*.js`（bazi.js、lunar.js 等）使用 UMD 包裝，Node 直接 `require()` 或 `eval()` 會因 `window is not defined` / `module.exports` 分支而失敗。本檔提供解法。

---

## A. Node vm sandbox 載入 UMD JS（核心解法）

### 為什麼一般方法會失敗
- **`require()`**：UMD 走 `module.exports = factory()` 分支，只回傳 exports、**不會設定 `window.Solar` / `window.Lunar`**（bazi.js calc() 載入時需要）。
- **`eval(src)`**：Node eval 的 `this` 不是 global，UMD 的 `root[i] = o[i]` 沒落到全域 → `window is not defined`。
- **`runInThisContext()`**：腳本內沒有 `window` 變量（它是 UMD factory 參數，非全域）。

### ✅ 已驗證可行的解法：`vm.createContext` + `sandbox.window = sandbox`
關鍵：**讓 `window === global context**，並把 `module`/`define` 設為 undefined 強制走 UMD else 分支。

```javascript
const fs = require('fs');
const vm = require('vm');

// 建立瀏覽器風格 sandbox：window === this context
const sandbox = {};
sandbox.window = sandbox;   // window === global（lunar.js compat layer 設 window.Solar）
sandbox.module = undefined; // 強制 UMD else 分支（不走 module.exports）
sandbox.define = undefined; // 無 AMD
vm.createContext(sandbox);

function run(src){ vm.runInContext(src, sandbox, {filename:'inline'}); }

// 1. lunar.js：UMD else → root[i]=o[i]；相容層設 window.Solar / window.Lunar / window.L
run(fs.readFileSync('src/public/js/algo/lunar.js','utf8'));
console.log('Solar:', typeof sandbox.window.Solar, '| L:', typeof sandbox.window.L);

// 2. bazi.js：global.Bazi = Bazi（此 context global === window）
let baziSrc = fs.readFileSync('src/public/js/algo/bazi.js','utf8').replace(/module\.exports[\s\S]*?;/g,'');
run(baziSrc);
const Bazi = sandbox.window.Bazi;

// 3. 呼叫 calc() 驗證回傳欄位
const res = Bizi_calc(Bazi, 1981, 5, 2, 0, 1);
function Bizi_calc(b,y,m,d,h,s){ return b.calc(y,m,d,h,s,'1'); }
console.log('dayGan:', res.dayGan, '| shengxiao:', res.shengxiao, '| yin_yang:', res.yin_yang);
console.log('wuxing:', JSON.stringify(res.wuxing));

// 4. 複製你的渲染邏輯做「非空驗證」（不必真的 eval wuxing.js 的 IIFE）
```

### ✅ 測 tool JS 的 render()（IIFE 包裝 + 局部函式）——2026-09-20 親身教訓
tool/*.js（yinyuan.js、wuxing.js 等）是 `(function(){ ... })()` IIFE，且 `render(res,name)` 是 **IIFE 內局部函式**，`window.render` 不存在。要跑它必須在檔案末尾注入暴露行：

```javascript
let src = fs.readFileSync('src/public/js/tool/yinyuan.js','utf8');
// ⚠️ 用 lastIndexOf("})();")——第一個 "});" 常封閉 if(submit) 等內層區塊，不是 IIFE 結束
const iifeEnd = src.lastIndexOf("})();");
src = src.slice(0, iifeEnd) + "window.render=render;\n" + src.slice(iifeEnd);
// ❌ 不要用 replace(/\}\)\);/, ...)：檔案以 \n})();\n 結尾，}與()間有換行，無 }); 序列可匹配
```

注入後需補齊 sandbox 環境（yinyuan.js 會用到）：
```javascript
const els = {};                              // getElementById 回傳的 DOM 容器
function makeEl(){ return {innerHTML:"",textContent:"",style:{},appendChild(){},addEventListener(){}}; }
global.document = { getElementById:(id)=>els[id]||(els[id]=makeEl()), createElement:()=>makeEl() };
const formMock={render(){}};
global.layui=function(){}; global.layui.use=function(m,c){c&&c({});}; global.layui.form=formMock; // yinyuan.js 讀全局 layui.form
global.layer_msg=function(){};
const sb2={console,Bazi,L,document,layer_msg,layui}; vm.createContext(sb2); sb2.window=sb2;
sb2.window.initComponents=function(){};       // yinyuan.js line 8 呼叫
vm.runInContext(src, sb2);                    // L.dizhi 需把 lunar.js 的 window.Lunar 傳入 sb2
const res = Bizi_calc(Bazi, 1981,5,2,12,1,"1");
sb2.window.render(res,"命主");                // 觸發 render()
const detail = els["yyDetail"].innerHTML;     // 驗證渲染內容（如「整體姻緣總評」+ 日主庚屬金…）
```

**踩坑順序（供參考）**：(1) `render` 未暴露 → 注入 window.render；(2) `L.dizhi is not defined` → 把 lunar.js 的 L 傳入 sb2；(3) `form.render undefined` → yinyuan.js 讀全局 `layui.form`，mock 要掛在函式上而非 callback param；(4) `createElement/addEventListener` 缺方法 → makeEl 補空方法。

### 為什麼第 4 步不直接 eval wuxing.js（IIFE）
- wuxing.js 是 `(function(){ ... })()` IIFE，內含 `layui.use(['form','layer'], cb)`。eval 它需要 mock `window.initComponents`、`layui.use`、DOM（getElementById）。
- **主管不要讓子代理耗時寫這些 mock**（記憶教訓：連續子代理卡在 document.createElement / innerHTML='' 不清空 children）。
- **對策**：只 eval lunar.js + bazi.js 取得 `res`，然後在測試腳本中「獨立複製」渲染邏輯做非空/正確性驗證。真正的語法檢查用 `node --check wuxing.js`（不執行），瀏覽器實測用 CDP（見 B 節）。

### 快速檢查簡繁統一
```bash
# 真正簡體專用字（運≠運、業≠業）應全為 0
for char in '运' '业' '财' '际' '统' '续' '论' '验'; do \
  printf "%s: " "$char"; grep -oP "$char" src/public/js/tool/wuxing.js | wc -l; done
# 繁體形式應存在：運/業/財/際/統
```

---

## B. CDP Chrome 實測（瀏覽器層級驗證）

### 啟動專屬 Chrome（port 9222）
config.yaml 的 `browser.cdp_url` 設為 `http://127.0.0.1:9222/json/version`。需保持一個 dedicated Chrome 常駐 port 9222：

```bash
# background=true 啟動（Hermes terminal 不支援 nohup/disown）
google-chrome --headless=new --no-sandbox --disable-gpu \
  --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-suanming-profile \
  --noerrdialogs --no-first-run --ozone-platform=headless
# 就緒檢查
curl -s http://127.0.0.1:9222/json/version | head -c 200
```

### ⚠️ browser_harness 不支援 top-level await
`browser_exec` 的 `js()` / `await js()` 在頂層會拋 `SyntaxError: 'await' outside function`。**用同步 IIFE**：

```javascript
// ❌ await js("...")   // 頂層 await 非法
// ✅ 同步 IIFE，回傳結果
const res = js('(function(){ document.getElementById("wxSubmit").click(); return "ok"; })()')
```

### ⚠️ URL 路徑陷阱（404 常見根因）
- **原站**用 `/tool/wuxingchaxun`（無 .html，Apache rewrite）。
- **我們的專案**用 `/tool/wuxingchaxun.html`（有副檔名）。先 `curl -o /dev/null -w "%{http_code}" http://localhost/tool/xxx` 確認路徑。
- 404 時檢查：`ls src/public/tool/` 與 `ls /var/www/html/tool/`，用 curl 逐路徑試 HTTP status。

### 實測流程（以 wuxing 頁為例）
```javascript
// 1. 載入頁面
new_tab('http://localhost/tool/wuxingchaxun.html'); wait_for_load();

// 2. 填表單 + 提交（同步 IIFE，回傳 wxResult.display）
js('(function(){ document.getElementById("wxYear").value="1981"; ...; document.getElementById("wxSubmit").click(); return "display="+document.getElementById("wxResult").style.display; })()')

// 3. 提取渲染內容驗證四維度非空
const detail = js('document.getElementById("wxDetail") ? document.getElementById("wxDetail").innerHTML : "not found"');
```

### CDP Chrome profile 快取陷阱（重要）
舊 profile（`/tmp/chrome-suanming-profile`）快取會導致瀏覽器載入舊版 JS，即使 Apache ETag 已更新、curl 拿到新檔。`window.__dbg` debug marker 可證實 browser 看不到新碼。**解法：kill + rm profile + 重啟 Chrome**。

---

## C. 主管獨立驗證的「最小有效組合」

當子代理卡住時，主管按此順序快速確認（避免陷入自測框架內耗）：

1. **`node --check <file>.js`** → exit=0（語法無誤）
2. **Node vm sandbox 載入 lunar.js + bazi.js** → 取得 `res`，驗證回傳欄位正確（dayGan/shengxiao/wuxing/yin_yang/cheng_gu 等）
3. **獨立複製渲染邏輯做非空驗證**（不必 eval IIFE）
4. **grep 簡繁統一**（真正簡體專用字 = 0）
5. **CDP Chrome 實測** → 確認 DOM 渲染 + 零 JS Error
6. **md5 src=deploy 一致** → 部署正確

> 鐵律：第 2~3 步驗證「邏輯正確」，第 5 步驗證「瀏覽器實際渲染」。兩者缺一不可，但都不該讓子代理用複雜自測框架完成。
