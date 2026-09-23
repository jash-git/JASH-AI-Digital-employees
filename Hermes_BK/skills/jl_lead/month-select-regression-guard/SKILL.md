---
name: month-select-regression-guard
description: suanming 專案月份選單回歸偵測器——掃描 src/public/js 提前攔截「fillDays 有、fillMonths 無」導致下拉空的歷史缺陷（T-31/陷阱7）
category: software-development
tags: [suanming, layui, select, regression, qa]
---

# 月份選單回歸偵測器 (month-select-regression-guard)

## 何時使用
任何修改或新增 `src/public/js/tool/*.js`（日期型工具頁：wuxing/yinyuan/ziwei/hehun/lunar/chepai 等）之後，部署前跑一次。這是攔截「月份選單空下拉」歷史缺陷的自動化守門員。

## 背景（為什麼需要這個）
suanming 專案在 2026-09-16 多次重現同一類 bug：多個日期型工具頁的 `<select id="*Month">` 載入後為空（optCount=0），因為各 JS 只有 `fillDays()` 填「日」、從未填充「月」，導致 calc 收 NaN 無法運算。手動修了 5 檔（wuxing/yinyuan/ziwei/hehun/lunar）。此工具把這個教訓變成**執行機制**——每次改前端自動偵測，不再靠人記。

## 工具位置與用法
```bash
# 預設掃描 src/public/js
scripts/check-month-select.sh

# 指定目錄（測試用）
scripts/check-month-select.sh /tmp/some-js-root
```
- exit code: `0` = 無缺陷，`1` = 發現問題，`2` = 找不到 JS 目錄
- 已自動排除 `tests/` 與 `algo/`（lunar.js/bazi.js 是純計算庫，不碰 select）

## 三種偵測模式（P1/P2/P3）
| 代碼 | 觸發條件 | 含義 |
|---|---|---|
| **P1** | 有 `fillDays()` 卻沒有 `fillMonths` | 月份選單永遠空（optCount=0），calc 收 NaN |
| **P2** | 有 `getElementById('...Month')` 卻從未填充 option | Month select 載入後為空，需確認 load 時填 12 個 month option |
| **P3** | 有動態 fillMonth/fillDay 卻沒有 `form.render('select')` | Layui 假下拉未同步（T-31 教訓） |

## 正確寫法（子代理/開發者必須遵守）
```javascript
// load 時同時填充 month（12 option）與 day 選單，且都在 layui.use callback 內
layui.use(['form'], function(){
  var form = layui.form;
  fillMonths();          // 填 1~12 月
  fillDays(...);         // 依月份/閏年重算日數
  form.render('select'); // ✅ Layui 假下拉同步
});
```

## 驗證（建立後必做）
1. **實測現有專案**：`./scripts/check-month-select.sh` → 應回傳 `✅ 無月份選單缺陷跡象`、exit=0。
2. **正控測試**：在 `/tmp/ms-test/js/tool/` 造故意壞掉的檔案（有 fillDays 無 fillMonths），跑偵測器確認抓出 P1/P2/P3 且 exit=1，測完 `rm -rf /tmp/ms-test`。

## 與既有技能的關係
- 此工具是 `jl-delegation-workflow`「陷阱7（月份選單空下拉）」的**執行版**。派前端任務時，要求子代理改完跑一次本腳本再交 QA。
- 也補強 `layui-development` 的「fillMonths/fillDays 必須同 callback + form.render('select')」教訓——從文字檢查清單升級為可自動跑的守門員。

## 維護
若新增其他前端缺陷模式（如 TOC 錨點不一致、JS 引用路徑斷裂），在 `check-month-select.sh` 擴充對應 grep 模式即可，不必另建新工具。
