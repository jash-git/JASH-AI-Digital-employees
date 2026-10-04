lunar.js LUNAR_INFO bit mapping: months stored from Dec→Jan in bits 15-4. Month m maps to bit (m+3). Formula: ((info >> (m+3)) & 1) ? 30 : 29. Common bug: using (12-m) or (m-1) causes all lunar conversions to be wrong.
§
用戶偏好串行微步執行：不用求快，每次只執行一個微步並監控品質。鐵則：(1) 先分析問題再規劃微步——每步必須在監控時程內可完成 (2) 每次只指派一個子代理執行單一微步 (3) 單一工作連續兩次失敗 → 繼續拆分或改用其他優解 (4) 穩定輸出品質 > 速度。
§
（決策取徑：權衡選項時以「對日後維護與開發的長期利益」為優先準則，重架構整潔／文件正確性勝過快速新增功能。例：評估未完成項目時把清理根目錄垃圾檔、修訂過時 gap-analysis.md 排在前於一次性功能補完 L4-M4。）
§
用戶對委派流程的嚴格要求（2026-09-19）：(1) jl_ui/jl_php 開發完必須由 jl_qa **獨立審查**才算數，QA REJECTED=退回重修；只有 QA PASS 後 jl_lead 才親自部署+瀏覽器實測+通知驗收。**jl_lead 不得自行 grep/瀏覽器核對完就標 DONE**（球員兼裁判嚴重違規），審查關不可跳過。(2) 連結／完整性驗證必須用真實瀏覽器實際點擊，不得只用 curl 斷言全站 OK、報告不得過度宣稱完成度。此與「串行微步執行」「都要紀錄下來」偏好一致。
§
yifanzi 部署扁平化（/var/www/html/yifanzi/，API/css/js/fonts 全平鋪根目錄，無 assets/ 或 api/ 子目錄）。src/public/*.html 資源引用必須用扁平相對路徑：css/layui.css、js/layui.js、js/lunar.js、同目錄 bazi.php——不能用 ../../assets/ 或 ../api/（部署後 404）。welcome.html（已 DONE）漏改仍 ../../assets/，部署後全 404；index.html 已修正。驗證 curl http://localhost/yifanzi/<resource> 應全 200。lunar.js 全域變數是 Solar（非 window.Lunar.Solar），正確鏈 Solar.fromYmdHms(y,m,d,h,mi,s).getLunar().getEightChar()。生肖依年柱地支在標準地支序索引對照（子鼠丑牛寅虎卯兔辰龍巳蛇午馬未羊申猴酉雞戌狗豬）。