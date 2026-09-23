---
name: layui-development
description: Layui v2.9+ frontend development workflows, pitfalls, and best practices. Covers local resource setup, CDN migration, jQuery bundling, and module loading.
category: software-development
---

# Layui Development Skill

Layui v2.9+ frontend development workflows, pitfalls, and best practices.

## Prerequisites

- Layui v2.9.3+ (prefer local files over CDN for offline/intranet environments)
- jQuery is bundled inside `layui.js` — see pitfall below

## Pitfalls

### layui.js 內建 jQuery，不需要額外下載

Layui 2.9.3 的 `layui.js` 已經內建 jQuery（約 87KB）。當從 CDN 遷移到本地檔案時：

- **只需要下載** `layui.js`、`layui.css`、`font/` 目錄
- **不需要**另外下載 jQuery
- 在 HTML 中只需引用 `lib/layui/layui.js`，jQuery 會隨之自動載入
- 程式碼中使用 `layui.$` 或 `layui.jquery` 即可操作 jQuery

### CDN 資源必須本地化

離線/內網環境不能使用外部 CDN。所有 layui 資源應放在 `src/public/lib/layui/` 下：

```
src/public/lib/
├── layui/
│   ├── css/layui.css
│   ├── layui.js
│   └── font/（iconfont.eot, svg, ttf, woff, woff2）
```

HTML 引用改為相對路徑：
```html
<link rel="stylesheet" href="lib/layui/css/layui.css">
<script src="lib/layui/layui.js"></script>
```

### layui.use() 模組載入

使用 `layui.use(['element', 'layer', 'jquery'], callback)` 載入所需模組。jQuery 模組名稱是 `'jquery'`，但因為已內建，不需要額外 script 標籤。

### 動態填充 <select>/<option> 後必須呼叫 form.render('select')

當用 JS 以 `createElement('option')` + `appendChild()`（或 `innerHTML=''` 重建）方式**動態產生下拉選項**時，layui 的 `<select>` 是它自己渲染的自訂 UI（`.layui-select`），原生 `<select>` 的 DOM 變動**不會自動同步**。若不呼叫 `form.render('select')`：
- 選單可能顯示錯誤、樣式未套用，或選項數與實際不符。
- 這是「下拉選單看起來能點但內容不對 / 無法選擇」類 bug 的最常見原因之一。

**正確做法**：每次改完 `<select>` 的 option（初始填充、月份變更時重算日期、依年份重算等）之後，都呼叫一次 `form.render('select')`。月份/日期的联动模式範例：
```javascript
var monthSel = document.getElementById('baziMonth');
var daySel   = document.getElementById('baziDay');
function fillMonths(){ /* 產生 1~12 月 option */ }
function fillDays(){ /* 依月份/閏年重算日數 option */ }
fillMonths();
fillDays();
form.render('select');                 // ✅ 載入時刷新
monthSel.addEventListener('change', function(){
  fillDays();
  form.render('select');               // ✅ 每次變更都刷新
});
```
**檢查清單**：任何用 JS 動態改過 `<select>` option 的頁面，確認 `form.render('select')` 在「初始填充」與「每個 change/re-render handler」之後都有呼叫。

### fillMonths/fillDays 與 form.render 必須在同一個 layui.use callback 內（空下拉 monthOpts=0）

當頁面用 `layui.use(['form'], function(){ ... })` 載入 form 模組時，**所有動態 option 填充（fillMonths / fillDays）與 `form.render('select')` 都必須放在同一個 callback 內、且 fill 在 render 之前**。若把 fill 寫在 callback 外（或 callback 之前），callback 內的 `form.render('select')` 會用「還沒填好的原生 `<select>`」重新渲染假下拉 → 選項全空（monthOpts=0）。

**錯誤寫法**：
```javascript
fillMonths();          // ❌ 在 callback 外先填
fillDays();
layui.use(['form'], function(){
  form.render('select'); // ✅ 但此時原生 select 是空的，渲染後也空
});
```

**正確寫法**（與 wuxing.js 的成熟模式一致）：
```javascript
layui.use(['form'], function(){
  fillMonths();          // ✅ callback 內先填
  fillDays();
  form.render('select'); // ✅ 再刷新，選項正常
});
```

**檢查清單**：任何用 `layui.use(['form'])` 的頁面，確認 fillMonths/fillDays **和** form.render('select') 都在同一個 callback 內。wuxing.js 是正確範本（fill + render 全在 callback 內）。

> ⚠️ 教訓來源：2026-09-16 T-33 tool 頁對齊修復，yinyuan/ziwei/hehun 三檔的 fillMonths/fillDays 原本寫在 callback 外，form.render('select') 把已填選項洗成空（monthOpts=0）。移到 callback 內後修復。

### 跨模組全域變數引用要一致（window.X vs 裸 L）

多個獨立 `.js` 檔案透過 `global`/`window` export 資料時，**引用端必須用同一個命名空間**。若 `lunar.js` 用 `global.Lunar = Lunar` export，則 `bazi.js` / `app.js` 都要用 `window.Lunar.xxx`（或先在該檔案內 `var L = window.Lunar`），**不能直接用裸變數 `L.xxx`**——因為全域只有 `window.Lunar`，沒有全域 `L`。裸 `L.isLeap(y)` 在頁面載入時會拋 `TypeError: Cannot read properties of undefined (reading 'isLeap')`，且若該行在函式內被包住，錯誤可能讓整個初始化流程中斷（後續 option 全沒產生）。

**檢查清單**：code review 時搜尋裸大寫變數引用（如 `L.`、`Baz.`），確認它們都有對應的 `window.X = ...` export 或本檔案內的 `var X = window.Y` 宣告。注意 export 名稱與引用名稱要完全一致。

### lunar.js 內部函數不可用裸 L. 引用

lunar.js 的 `solarToLunar()` / `lunarToSolar()` 等**內部函數**（非 export 的 function）在閉包內呼叫 `L.jdn()`, `L.leapMonth()`, `L.monthLen()`, `L.fromJdn()` 時，`L` 並未宣告為局部變數。正確寫法是改用 `Lunar.`（因為 `Lunar` 物件在同一閉包內已建立）。

**錯誤寫法**：
```javascript
function solarToLunar(y, m, d){
    var j = L.jdn(y, m, d);          // ❌ ReferenceError: L is not defined
    var lm = L.leapMonth(yy);        // ❌ 同上
}
```

**正確寫法**：
```javascript
function solarToLunar(y, m, d){
    var j = Lunar.jdn(y, m, d);      // ✅ 同一閉包內的 Lunar 物件
    var lm = Lunar.leapMonth(yy);    // ✅
}
```

**檢查清單**：在 lunar.js 的內部函數中，所有 `L.xxx` 引用都應改為 `Lunar.xxx`。可用 `grep -n " L\\." src/public/js/algo/lunar.js` 快速搜尋剩餘的裸引用。

### FontAwesome CDN 依賴與 emoji 替代方案

動態渲染的 JS 模組（如 `bazi-report.js`）若使用 `<i class="fas xxx">` FontAwesome 圖示，但 index.html **沒有載入 FontAwesome CSS**（CDN link 或本地檔案），卡片標題的圖示會顯示為空白。

**修復策略**：
1. **優先改用 emoji** — 最簡單且斷網可用。將 `card()` 呼叫中的 icon 參數從 `'fa-id-card'` 改為 `'📋'`，然後在 CSS 中為 `.card-header i` 加上顏色（如 `color: var(--lm-primary)`），emoji 會正常顯示。
2. **若必須用 FontAwesome** — 在 index.html `<head>` 中加入 CDN link：
   ```html
   <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
   ```

**檢查清單**：code review 時搜尋所有 `class="fas` 或 `fa-`，確認對應的 CSS 已載入。若專案要求斷網可用，優先改用 emoji。

### 報告區 CSS class 必須在 style.css 中定義

動態渲染模組（如 `bazi-report.js`）產生的 HTML 使用自訂 CSS class（`.card`, `.fade-in`, `.info-grid`, `.chart-bar`, `.yongshen-grid`, `.chenggu-result` 等），這些 class **必須在 `style.css` 中有對應定義**。若 style.css 缺少這些 class：
- 卡片會沒有邊框、陰影、圓角
- 五行柱狀圖不會顯示顏色和寬度
- 基本信息網格會堆疊成一列

**修復策略**：在 style.css 末尾補充所有動態渲染模組需要的 CSS class。參考 `suanming` 專案的修復：
```css
/* ---------- 八字報告卡片（bazi-report.js）---------- */
.card{background:#fff;border:1px solid var(--lm-border);border-radius:var(--lm-radius);box-shadow:var(--lm-shadow);margin-bottom:20px;overflow:hidden;}
.card-header{padding:14px 18px;border-bottom:1px solid var(--lm-border);font-size:17px;font-weight:700;color:var(--lm-ink);}
.card-body{padding:18px;line-height:1.8;}
@keyframes fadeInUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
.fade-in{animation:fadeInUp .5s ease-out both;}
.info-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px 24px;}
.chart-bars{display:flex;flex-direction:column;gap:10px;padding:10px 0;}
/* ...更多 class */
```

**檢查清單**：每次新增動態渲染模組時，確認所有 JS 中使用的 CSS class 都在 style.css 中有定義。可用 `grep -oE "[a-zA-Z_-]+" bazi-report.js | sort -u` 提取 class name 比對。

### 登入頁面版權文字不要用 flex 子元素

登入頁面的 `.login-wrapper` 使用 `display: flex; align-items: center; justify-content: center;` 來垂直置中登入卡片。如果版權文字（`.login-footer`）放在 `.login-wrapper` 裡面作為子元素，flex 會把它們排成**水平並排**而非上下排列。

**正確做法**：
1. 把 `.login-footer` 放在 `.login-wrapper` **外面**，成為 body 的直接子元素。
2. CSS 使用 `position: fixed; bottom: 0; left: 0; right: 0;` 固定在頁面最底部。
3. 顏色建議用白色半透明（`rgba(255,255,255,0.6)`）以配合漸層背景。
4. 加上 `pointer-events: none;` 避免版權文字阻擋點擊。

錯誤範例（並排）：
```html
<div class="login-wrapper">
  <div class="login-card">...</div>
  <div class="login-footer">© 2025 ...</div>  <!-- ❌ 會並排 -->
</div>
```

正確範例（固定底部）：
```html
<div class="login-wrapper">
  <div class="login-card">...</div>
</div>
<div class="login-footer">© 2025 ...</div>  <!-- ✅ 在 wrapper 外面 -->
```
```css
.login-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  text-align: center;
  padding: 16px 0;
  color: rgba(255, 255, 255, 0.6);
  font-size: 13px;
  pointer-events: none;
}
```

### 側邊欄 nav 事件 — lay-id 在子元素上，elem 是父元素

`element.on('nav(sideMenu)')` 觸發時，`elem` 是 `<li>` 元素，但 `lay-id` 通常設在子 `<a>` 上（尤其是嵌套選單的 dd 項目）。直接使用 `elem.getAttribute('lay-id')` 會回傳 null。

**錯誤寫法**：
```javascript
element.on('nav(sideMenu)', function (elem) {
    var layId = elem.getAttribute('lay-id');  // ❌ null，lay-id 在子 <a> 上
    if (!layId) return;
    // ...
});
```

**正確寫法**（使用 jQuery）：
```javascript
element.on('nav(sideMenu)', function (elem) {
    var layId = $(elem).attr('lay-id');
    if (!layId) {
        // 尋找子 <a> 上的 lay-id
        var child = $(elem).find('> a[lay-id]');
        if (child.length) layId = child.attr('lay-id');
    }
    if (!layId) return;
    // ...
});
```

**適用場景**：所有使用 `lay-filter` + `element.on('nav')` 的側邊欄選單。如果選單有巢狀結構（父項目展開子項目），lay-id 幾乎一定在子 `<a>` 上。

**檢查清單**：在 code review 時，檢查所有 `element.on('nav')` 的 handler，確認有處理 lay-id 在子元素上的情況。

### XSS 防護 — 彈窗表單中禁止直接拼接使用者輸入

在 `layer.open` 的 `content` 字串中，所有從後端取得的資料（如 `info.username`、`info.role` 等）**必須經過 HTML escape 後才能拼接進 HTML 字串**。直接拼接會導致 XSS 攻擊。

**錯誤寫法**（第 250 行常見）：
```javascript
'<input type="text" name="username" value="' + (info.username || '') + '">'
```

**正確寫法**：
```javascript
function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}
// 使用：
'<input type="text" name="username" value="' + escapeHtml(info.username || '') + '">'
```

**適用場景**：所有 `layer.open` 的 `content` 字串拼接、所有 `innerHTML` 賦值、所有 `document.write`。只要資料來源是後端 API 回應，就必須 escape。

**檢查清單**：在 code review 時，搜尋所有 `+` 拼接 HTML 字串的地方，確認每個變數都用 `escapeHtml()` 處理過。

### 前端整合五重檢查（「頁面不能用」的常見根因）

當使用者回報「瀏覽器測試還是不能用」或「點了按鈕沒反應」時，按以下順序逐一排查：

1. **外部依賴是否存在** — FontAwesome / Chart.js / CDN 等資源是否真的載入？
   - `grep -i "fontawesome\|fa-" index.html` → 有 `<i class="fas xxx">` 但沒有 CSS link = 圖示空白
   - 修復：加 CDN link，或改用 emoji（斷網可用）
2. **渲染函數是否被呼叫** — submit handler 只做了部分渲染？
   - `grep "renderReport\|renderBazi" app.js` → 確認 submit handler 有呼叫所有需要的渲染函數
   - 常見錯誤：只有簡易結果（`renderBazi`），沒有完整報告（`window.renderReport`）
3. **拼字一致性** — `Bizi.calc()` vs `Bazi.calc()`、`L.isLeap()` vs `window.Lunar.isLeap()`
   - `grep "Bizi\|global\.Baz" src/public/js/*.js` → 搜尋所有 calc() 呼叫
   - export 名稱與引用名稱必須完全一致（大小寫敏感）
4. **CSS class 是否存在** — JS 產生的 HTML 有對應的樣式？
   - `grep "\.card\|\.fade-in\|\.info-grid" css/style.css` → 沒有 = 卡片無樣式
   - bazi-report.js 等動態渲染模組依賴的 CSS class 必須在 style.css 中定義
5. **Script 載入順序** — 依賴檔案是否先於引用端載入？
   - `grep "<script" index.html` → 正確順序：lunar.js → bazi.js → bazi-report.js → app.js
   - 後面的 script 不能引用前面還沒定義的變數/函數

### bazi.js calc() 的 lunar 變數在 dateType='1' 時為 null

`Bazi.calc(y, m, d, hour, sex, dateType)` 中，當 `dateType === '1'`（陽曆輸入）時，`lunar` 變數**不會被賦值**（保持 null）。只有 `dateType === '2'`（農曆輸入）時才會呼叫 `L.lunarToSolar()` 並回傳 lunar 物件。

**常見錯誤**：在 calc() 內部直接讀取 `lunar.month` / `lunar.day` 做稱骨計算，會 fallback 到預設值 month=1, day=1（農曆正月初一），導致 cheng_gu 算錯。

**正確做法**：需要 lunar 資料時，明確呼叫 `L.solarToLunar(y, m, d)`：
```javascript
var lunarForChengGu = null;
if(dateType === '2') {
    lunarForChengGu = lunar; // already converted from lunarToSolar
} else {
    lunarForChengGu = L.solarToLunar(y, m, d); // solar input -> need conversion
}
// 使用 lunarForChengGu.month / .day
```

**檢查清單**：在 bazi.js 的 calc() 中，所有需要 lunar month/day 的地方（稱骨、農曆顯示等），確認有處理 dateType='1' 時 lunar=null 的情況。

### LUNAR_INFO[0]（年 1900）閏月值錯誤導致農曆年份偏移 +1

自製 lunar.js 的 `LUNAR_INFO` 陣列中，**索引 0（對應年 1900）的低 4 位元若設為非零值**（如 `8`），表示 1900 年有閏月。但歷史上年 1900 並無閏月，正確值應為 `0`。這會導致所有農曆年份計算偏移 +1 年。

**經典案例：**
- `LUNAR_INFO[0] = 0x04bd8` → 低 4 位 = 8（錯誤）
- `LUNAR_INFO[0] = 0x04ae0` → 低 4 位 = 0（正確）

**症狀：**
- `solarToLunar(1981, 5, 2)` 返回 `{year:1982, month:7, day:18}` ❌
- 正確應為 `{year:1981, month:7, day:18}` ✅

**驗證方法：**
```bash
# 快速檢查 LUNAR_INFO[0] 低 4 位是否為 0
node -e "var w={}; eval(require('fs').readFileSync('src/public/js/algo/lunar.js','utf-8')); var L=w.Lunar; console.log('LUNAR_INFO[0]:', '0x' + L.info[0].toString(16)); console.log('Leap month:', (L.info[0] & 0xf) === 0 ? 'none ✅' : 'ERROR: ' + (L.info[0] & 0xf));"
```

**修復後驗證關鍵日期：**
- `solarToLunar(1981, 1, 27)` → `{year:1981, month:1, day:1}`（辛酉年正月初一）
- `solarToLunar(1980, 2, 16)` → `{year:1980, month:1, day:1}`（庚申年正月初一）

> ⚠️ **檢查清單**：每次修改 lunar.js 的 LUNAR_INFO 陣列後，務必驗證索引 0 的低 4 位 = 0。可用 `scripts/verify-lunar-epoch.sh` 快速檢查。

### 月份選單回歸偵測器（check-month-select.sh，2026-09-18 新增）
「fillDays 有、fillMonths 無」是 suanming 多次重現的歷史缺陷（T-31 / jl-delegation-workflow 陷阱7）。改/新增 `src/public/js/tool/*.js` 後、交 QA 前跑一次自動偵測器，提前攔截而非部署後才發現：
```bash
scripts/check-month-select.sh          # 預設掃描 src/public/js
scripts/check-month-select.sh /tmp/some-js   # 指定目錄（測試用）
```
- exit `0`=無缺陷、`1`=發現問題。已自動排除 tests/ 與 algo/。
- **三種模式**：P1=有 fillDays 卻無 fillMonths；P2=有 Month select id 卻從未填充 option；P3=有動態 fill 卻沒有 form.render('select')（Layui 假下拉未同步）。
- 正控測試：在 /tmp/ms-test/js/tool/ 造故意壞掉的檔案，確認抓出 P1/P2/P3 且 exit=1，測完 rm -rf /tmp/ms-test。

### Node.js eval 快速驗證法（不依賴瀏覽器）：
```js
var fs = require('fs');
// 1. Mock Bazi/Lunar globals
var Bazi = { ganWuxing:{...}, calc:function(){ return {...} } };
// 2. Mock document.getElementById
global.document = { getElementById: function(id){ return { innerHTML:'', style:{} }; } };
// 3. eval bazi-report.js content
var code = fs.readFileSync('js/bazi-report.js','utf8');
global.window = {}; // needed for window.renderReport assignment
eval(code);
// 4. Call renderReport and check output
window.renderReport(Bazi.calc(1981,5,2,12,1,'solar'));
console.log('HTML length:', document.getElementById('report-area').innerHTML.length);
```
此法可快速驗證渲染邏輯是否正確，不需啟動瀏覽器。

### Node.js eval lunar.js 的完整技巧
lunar.js 使用 IIFE `(function(global){ ... })(window);` 將 Lunar 物件掛在 `global.Lunar`（即 `window.Lunar`）。在 Node.js 中 eval 時：
1. **必須先建立 `global.window = {}`**，否則 IIFE 的 `(window)` 參數會拋 ReferenceError
2. **存取 Lunar 物件用 `global.window.Lunar`**，不是 `Lunar`（因為 Lunar 只在 window 物件內）
3. **完整範例**：
```js
var fs = require('fs');
global.window = {};
eval(fs.readFileSync('./src/public/js/algo/lunar.js', 'utf-8'));
var result = global.window.Lunar.solarToLunar(1981, 5, 2);
console.log(JSON.stringify(result)); // {year:1982, month:7, day:18}
```

### rsync exit=23 的含義與處理方式
rsync exit code 23 = "partial transfer due to error"。常見原因：
- **chgrp/chown 權限錯誤**：目標目錄擁有者不是 root，但 rsync 嘗試改變 group/owner 時失敗
- **檔案刪除失敗**：`--delete` 模式下，舊檔案的 unlink() 因權限被拒

**處理方式**：
1. 檢查 stderr 是否有 `Operation not permitted` 或 `Permission denied`
2. **如果檔案實際已複製成功**（用 `ls -la` 確認），exit=23 可忽略
3. **如果需要完全乾淨的佈署**：先 `chown root:root /var/www/html/`，再執行 rsync，最後改回 `chown www-data:www-data`
4. **替代方案**：用 `cp -r` 或 `tar` 取代 rsync

### Chrome browser_exec 失敗時的替代方案
當 Chrome 沒在跑時，browser_exec 會返回 "Chrome isn't running"。此時可用 headless Chrome dump DOM：
```bash
google-chrome --headless=new --no-sandbox --dump-dom http://localhost/index.html > /tmp/page.html
# 然後 grep 檢查關鍵元素是否存在
grep -c 'report-area' /tmp/page.html
```
此法不需 Chrome GUI，適合 CI/CD 或 headless server。

### 農曆轉換：優先使用成熟開源庫而非自製 lunar.js

自製的 `lunar.js`（基於 JDN + baseJdn 累加）容易因 **baseJdn 基準日錯誤**導致所有農曆轉換偏移。經典案例：1900/01/31 被標註為「農曆己卯年初一」，但實際是庚子年臘月，導致 1981/05/02 被算成「農曆 1982 年七月十八」（年份 +3、月日全錯），正確應為「辛酉年三月廿八」。

**推薦方案：使用 [6tail/lunar-javascript](https://github.com/6tail/lunar-javascript)**
- ✅ 功能完整：天干地支、生肖、24 節氣、八字排盤、稱骨算命
- ✅ 經過大量測試驗證，支援 1900-2100 年
- ✅ 零依賴，可直接嵌入瀏覽器
- ✅ npm: `lunar-javascript`（v1.7.7+）
- ✅ CDN: `https://cdnjs.cloudflare.com/ajax/libs/lunar-javascript/1.7.7/lunar.min.js`

**使用方式：**
```javascript
// 陽曆 -> 農曆
const Lunar = require('lunar-javascript'); // 或直接用 script tag
const solar = Lunar.Solar.fromDate(new Date(1981, 4, 2)); // month=0-indexed!
console.log(solar.getLunarYear(), '年', solar.getMonthInChinese(), '月', solar.getDayInChinese());
// 輸出：1981 年 三月 廿八

// 農曆 -> 陽曆
const lunar = Lunar.Lunar.fromDate(1981, 3, 28, false);
console.log(lunar.getYear(), '/', lunar.getMonth(), '/', lunar.getDay());

// 干支、生肖、節氣等
console.log(solar.getYearInGanZhi(), '年'); // 辛酉年
console.log(solar.getShengXiao());          // 雞
```

**嵌入專案步驟：**
1. `npm install lunar-javascript` → 複製 `node_modules/lunar-javascript/dist/index.js` 到 `src/public/lib/lunar/`
2. 在 HTML 中引用：`<script src="lib/lunar/index.js"></script>`
3. 將 `bazi.js` 中的 `L.solarToLunar()` / `L.lunarToSolar()` 改為 `Lunar.Solar.fromDate().getLunar()` 等 API
4. 更新 `bazireport.php` 使用對應的 PHP lunar 庫或移植關鍵函數

**檢查清單：**
- [ ] 新庫已嵌入 `src/public/lib/lunar/`
- [ ] bazi.js 中所有 `L.` 引用改為 `Lunar.` API
- [ ] bazireport.php 回傳的農曆欄位與前端一致
- [ ] 邊界值測試通過（立春前後、閏月、節氣日）
- [ ] 與參考網站（suanming.com.tw）結果比對一致