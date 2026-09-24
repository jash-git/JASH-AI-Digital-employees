---
name: subfolder-deploy-fix
description: Subfolder static site 404s? Make internal links relative.
category: software-development
tags: [static-site, subfolder-deploy, base-tag, relative-path, absolute-path, 404, path-normalize]
---

# 靜態站子資料夾部署修復（subfolder-deploy-fix）

## 何時使用
- 一個原本設計成放「網域根」的靜態網站（連結全是 `/index.html`、`/img/logo.png`），要部署到**子資料夾**（如 `http://host/suanming/`）。
- 現象：首頁能開，但 Logo 破圖、點任何導覽列/內頁連結全 404。
- ❌ 不要用在：網站本來就放網域根（那就不需要改）；或後端是動態路由的 SPA（那是 router 問題，不是路徑前綴）。

## 根因（最重要的一點）
HTML `<base href="/suanming/">` **只對「相對」URL 生效**。網站若用**絕對路徑**（`/img/logo.png`、`/index.html`），瀏覽器會相對於「網域根」解析，**完全忽略 base**：
- `/img/logo.png` → `http://host/img/logo.png` ❌（實際在 `http://host/suanming/img/logo.png`）→ 404
- `<base>` 再對也救不了絕對路徑。

**解法**：把內部連結從「絕對」改成「相對」（去掉開頭 `/`、移除 `../`），base 才锚得住。相對路徑會相對於 base 解析，無論頁面在幾層子目錄都正確。

## 驗證根因（先確認，別急著改）
用 curl 直接比對絕對 vs 相對解析：
```bash
curl -sI http://host/img/logo.png        # 多半 404（絕對→網域根）
curl -sI http://host/suanming/img/logo.png  # 多半 200（實際位置）
```
兩者結果相反 = 就是這個 bug。再確認 `curl http://host/suanming/index.html | grep '<base'` 有 base。

## 工具：scripts/path-normalize.py
批量把內部連結改相對，保留 `<base>`、跳過第三方套件與 Node 測試檔，並自動做後驗證。
```bash
python3 scripts/path-normalize.py --root src/public --base /suanming/        # dry-run（預設）
python3 scripts/path-normalize.py --root src/public --base /suanming/ --apply # 寫入磁碟
```
- HTML：`href=`/`src=` 去掉開頭 `/`、移除 `../`；**永遠不動 `<base>` 元素**。
- JS：只對白名單 web URL（`/img/...`、`*.html`…）去斜線，避免誤傷正則片段。
- 跳過：`lib/`（第三方）、`js/tests/`、`*-test.js`（用檔案系統路徑）。
- 不碰：`https://`、`http://`、`#fragment`、`javascript:`、`data:`、單斜線 `/`。

## 兩個必犯的坑（本次實測踩到，寫進流程防重來）
1. **腳本印「APPLIED」但其實沒寫入**：改 `write_file`/`patch` 時若漏掉真正的寫入邏輯（只有 print、沒有 `open(...).write()`），dry-run 與 apply 行為一模一樣。→ 改完先 `grep -n "\.write\|open(" script.py` 確認有寫入，再跑 --apply。
2. **寬鬆正則會毀檔**：用「任何 `/` 開頭字面量」的 blanket regex 改 JS，會誤傷 `.replace(/'/g,'&#39;')` 這類正則片段（把 `/'/g` 改為 `'g`），破壞 HTML 跳脫。→ **一律用白名單**（只碰已知資源前綴/副檔名）+ **先 dry-run 看 diff** + **apply 後跑驗證**（grep 剩餘絕對路徑、node --check JS）。

## 部署與驗收流程
1. `--root` 指向網站根（如 `src/public`），先 dry-run 檢查 diff 是否只動內部連結。
2. `--apply` 寫入，確認輸出「All base tags intact」+「Internal absolute paths remaining: 0」。
3. Node syntax check：`for f in $(find src/public/js -name '*.js' ! -path '*tests*' ! -name '*-test.js'); do node --check "$f"; done`。
4. 打包上傳：**只傳 `src/public` 裡面的內容**（不要帶上 `src/`、`public/` 外層資料夾）到子資料夾根（如 `/var/www/html/suanming/`）。這是本專案最高頻的上傳錯誤。
5. 瀏覽器實測：用 CDP Chrome 載入首頁，確認 Logo `currentSrc` 含子資料夾前綴、`complete=true`、Console 0 錯誤。別只用 curl 斷言全站 OK（curl 把相對路徑解析到網域根會誤報 200）。

## 與既有技能的關係
- `site-link-audit`：修完後跑，確認沒有「相對路徑跨目錄崩潰」的殘留缺陷。兩者互補——本技能負責「改絕對→相對 + base 生效」，link-audit 負責「改完後的跨頁連結回歸守門」。
- `deployment-check.sh`：主管比對 src vs deploy md5 的機械化工具，可接在本流程第 3 步之後。

## 維護
若網站用不同子資料夾名稱或深度（如 `/a/b/site/`），改 `--base` 即可，邏輯不需動。若發現新的誤傷模式（如 CSS `url()`、data URI），在 `is_web_url()` 白名單擴充。
