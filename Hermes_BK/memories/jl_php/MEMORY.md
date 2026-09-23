§ 部署鐵律 (2026-08-03): 部署時專注於伺服器設定與檔案佈署（.htaccess、index.php、權限配置），嚴禁大量修改程式碼作為變通手段。若需改程式碼才能跑，代表部署流程或伺服器設定有問題——檢查：(1) Apache mod_rewrite 是否啟用 (2) AllowOverride 是否設定 (3) .htaccess 是否正確。程式碼修改只限修復真正錯誤。
§ 佈署流程最後一步必須執行 graphify . 生成知識圖譜（無 LLM API key 用 --code-only）。生成後執行 graphify cluster-only 產生 GRAPH_REPORT.md。

§ suanming 專案背景 + PHP 職責 (2026-09-18): PHP 8 + MySQL 8 + Layui v2.9+ 命理網站，工作範圍僅 src/api/ 與 src/config/。連線解析 src/config/.env（User: webapp / Host: localhost），嚴禁 Hardcode 帳密。純帳密驗證（Session/Cookie），**嚴禁 JWT**。API 輸出相容 layui JSON：{"code":0,"msg":"success","count":N,"data":[...]}。每組功能模組建獨立 PHP API 統一處理 CRUD。部署用 deployment-iron-rules skill（已分發至此 profile）。
§ 共用 JS 相對路徑連結崩潰教訓 (2026-09-19)：articles.js/app.js 等「共用資料檔」內文章卡片連結若用相對路徑（如 url:'blog/detail.html?id=xxx'），瀏覽器相對於「點擊時所在頁面目錄」解析，從 /cate/、/type/ 子目錄點會變成 /cate/blog/detail.html → 404。curl-only 巡檢必漏。對策：共用資料檔連結一律用絕對路徑 `/blog/detail.html`（根相對）。已寫入 jl-delegation-workflow「陷阱8」。
§
記憶主動管理原則：有新偏好/修正/環境事實即存；見零散重複 entry 或 >70% 時趁手斂為少數高訊號 entry，勿等滿載或等使用者提。能成技能(skill)或工具(terminal/script)者一律移出記憶，記憶只留不可程序化的領域知識與教訓。
