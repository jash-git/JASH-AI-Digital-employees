---
name: yifanzi-iztro-calc
description: "Build 紫微 pages using iztro.min.js calc functions correctly."
version: 0.1.0
author: jl_ui, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [yifanzi, iztro, ziwei, frontend, astrology]
---

# yifanzi iztro 紫微計算整合

在 yifanzi 專案建立紫微斗數工具頁（ziwei.html）時，用 iztro.min.js 做排盤計算的正確用法與已知坑。

## When to Use
- 新增任何需要紫微斗數排盤的前端頁面（ziwei/liuyao/qimen/liuren/solar-time/lunar-calendar/tarotdraw）
- 需要從出生陽曆日期+性別排出十二宮主星、身主/命主、農歷年份
- 參考已過 QA 的 bazi.html 設計系統與 CRUD 串接模式

## Prerequisites
- `assets/js/iztro.min.js`（787KB，暴露全域 `iztro`）
- `assets/js/lunar.js`（暴露全域 `Solar`，lunar-javascript）
- `src/public/bazi.html` 設計系統範本（CSS variables、layui card、響應式）
- `src/api/ziwei.php` API（GET list / POST / PUT / DELETE，raw body JSON）

## How to Run
1. 讀 bazi.html + index.html + src/config/README.md line 60 確認 payload 結構
2. 在瀏覽器實測 iztro API（不要猜），用 file:// mirror 驗證
3. 建立 ziwei.html，沿用 bazi.html 設計系統與 CRUD 模式
4. 部署鏡射實測：console error=0、iztro 載入、排出十二宮主星、CRUD 對 wei.php 發請求
5. task_board.json T03 → REVIEW + 附實測結果

## iztro API 實際用法（已瀏覽器實測）

### ⚠️ 關鍵：函數在 astro 命名空間，不在 iztro 頂層
```
typeof window.iztro === 'object'   // true
window.iztro.astro.getSoulAndBody(...)   // ✅ 正確
window.iztro.getSoulAndBody(...)          // ❌ is not a function
```
命名空間：`astro`（排盤計算）、`data`、`star`（星曜索引）、`util`。

### getMajorStarBySolarDate — 主星（唯一能直接用的整檔函數）
```js
iztro.astro.getMajorStarBySolarDate('1990-08-07T13:00')
// → "紫微,破軍" （逗號分隔字串，ISO 格式 YYYY-MM-DDTHH:mm）
```
注意：此函數對不同時辰回傳相同結果（疑似只依日柱），不能用來分佈十二宮。

### getSoulAndBody — 命主/身主（可用）
```js
iztro.astro.getSoulAndBody({ solarDate: '1990-08-07 13:00', timeIndex: 7 })
// → { soulIndex, bodyIndex, heavenlyStemOfSoul, earthlyBranchOfSoul }
```
- `solarDate` 用「空白分隔」格式（YYYY-MM-DD HH:mm），不用 T
- `timeIndex` = 0~11，對應子丑寅卯...亥。公式：`Math.floor(((hour+1) % 24) / 2)`
  - hour=13 → timeIndex=7；hour=9 → timeIndex=4
- bodyIndex 索引對齊地支序 ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']

### astrolabeBySolarDate — ⚠️ 本 minified 版本有 bug（不可用）
```js
iztro.astro.astrolabeBySolarDate('1990-08-07T13:00')
// → TypeError: Cannot read properties of undefined (reading 'push')
```
所有輸入格式（ISO 字串 / Solar object + timeIndex）都失敗。內部 solar2lunar() 需要日期字串，但 palaces push 步驟崩潰。**不要用此函數**。

### getPalaceNames — ⚠️ 回傳空陣列（不可用）
```js
iztro.astro.getPalaceNames('1990-08-07T13:00')
// → ["", "", ...] （12 個空字串）
```

## 可行排盤策略（因 astrolabeBySolarDate 有 bug）
用 getSoulAndBody 取身主/命宮天干地支，再用 lunar.js Solar.getLunar().getYearGan()/getYearZhi() 取農歷干支年份。十二宮主星因無完整排盤函數，用手動構造示範資料（payload.palaces[]），但身主/命主/農歷年份用真實計算。

### 身主（依年支對應之星，標準紫微斗數）
```js
var BODY_STAR_BY_ZHI = {
  '子': '武曲', '丑': '文昌', '寅': '廉貞', '卯': '文曲',
  '辰': '祿存', '巳': '貪狼', '午': '武曲', '未': '文昌',
  '申': '廉貞', '酉': '文曲', '戌': '祿存', '亥': '貪狼'
};
```

### lunar.js Solar 取農歷干支
```js
var solar = Solar.fromYmdHms(1990, 8, 7, 13, 0, 0);
var lunar = solar.getLunar();
lunar.getYearGan() + lunar.getYearZhi()   // → "庚午"
```

## payload 結構（對齊 src/config/README.md line 60）
```js
{
  birth_solar: '1990-08-07 13:00',
  gender: 'male',
  name: '',
  lunar_year: '庚午',
  body_master: '武曲',   // 身主之星名
  soul_master: '戊',     // 命宮天干
  palaces: [
    { name: '命宮', main_stars: ['紫微','天府'], extra_stars: [] },
    // ...共 12 宮，PALACE_ORDER 固定順序
  ]
}
```

## CRUD 串接（對齊 ziwei.php）
- GET → {code:0,msg,count,data}，table.reload({data, count})
- POST raw body JSON payload → {data:[newId]}
- PUT ?id=<id> raw body JSON → {data:[id,true]}
- DELETE ?id=<id> → {data:[true, rows_affected]}
- 用 layui.$.ajax，contentType: 'application/json; charset=utf-8'
- 錯誤用 layer.msg(msg) 顯示後端回傳 msg
- escapeHtml() 轉義所有使用者輸入（name/title）

## Pitfalls
1. iztro 函數在 astro 命名空間下，直接 iztro.getXxx() 會 is not a function
2. astrolabeBySolarDate 和 getPalaceNames 在本版本有 bug/空結果，不要依賴
3. timeIndex 公式是 ((hour+1)%24)/2 floor，不是 hour/2
4. lunar.js 全域變數是 Solar（非 window.Lunar.Solar）
5. datetime-local value 用 'T' 分隔；payload.birth_solar 用空白分隔
6. form.render('select') 必須在動態 fill select 後重渲染
7. table done callback 裡調 loadRecords() 刷新資料

## Verification
- file:///tmp/deploy-test/ziwei.html：console error=0，typeof iztro/lunar/layui 皆 defined
- 填 birth_solar + gender → 排出紫微 → 12 宮格渲染、sumBody/sumSoul/sumLunarYear 有值
- curl POST/PUT/DELETE ziwei.php 回傳格式對齊（400 缺參 / 404 不存在）
