lunar.js LUNAR_INFO bit mapping: months stored from Dec→Jan in bits 15-4. Month m maps to bit (m+3). Formula: ((info >> (m+3)) & 1) ? 30 : 29. Common bug: using (12-m) or (m-1) causes all lunar conversions to be wrong.
§
用戶偏好串行微步執行：不用求快，每次只執行一個微步並監控品質。鐵則：(1) 先分析問題再規劃微步——每步必須在監控時程內可完成 (2) 每次只指派一個子代理執行單一微步 (3) 單一工作連續兩次失敗 → 繼續拆分或改用其他優解 (4) 穩定輸出品質 > 速度。
§
（決策取徑：權衡選項時以「對日後維護與開發的長期利益」為優先準則，重架構整潔／文件正確性勝過快速新增功能。例：評估未完成項目時把清理根目錄垃圾檔、修訂過時 gap-analysis.md 排在前於一次性功能補完 L4-M4。）
§
用戶對委派流程的嚴格要求（2026-09-19）：(1) jl_ui/jl_php 開發完必須由 jl_qa **獨立審查**才算數，QA REJECTED=退回重修；只有 QA PASS 後 jl_lead 才親自部署+瀏覽器實測+通知驗收。**jl_lead 不得自行 grep/瀏覽器核對完就標 DONE**（球員兼裁判嚴重違規），審查關不可跳過。(2) 連結／完整性驗證必須用真實瀏覽器實際點擊，不得只用 curl 斷言全站 OK、報告不得過度宣稱完成度。此與「串行微步執行」「都要紀錄下來」偏好一致。
§
suanming 中斷紀錄（2026-09-20 22:xx 系統更新暫停）：F-04 已 DONE(bazi.js md5=2dfbbdcad4beadf87bd1f146ec1f8f5b; bazi-report.js md5=07bfec18d8fc247f65e074d856f5a067 含 line101 </tr> bug 修復; DoD 辛卯@10→癸未@90)。F-03 M1 整體姻緣總評已完成(md5=b9fc98e7bc3ed8d226abfe439d05d088)但 task_board 仍 TODO。待辦 F03-M2+F03-M3 QA。中斷時仍有進行中子代理 deleg_e29b4524(sa-0-0669afc4, CDP實測中遇 Chrome /json/{id} API異動) + 4 cron watchdog(5121805d45f1/ed17b8bf4311/7df8e814e653/28d903155e2d)需清除。