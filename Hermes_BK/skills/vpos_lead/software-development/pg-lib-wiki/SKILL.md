---
name: pg-lib-wiki
description: Use when debugging/troubleshooting PHP, MySQL/SQL, C#, .NET, Avalonia UI, layui, jQuery, Python or Android — errors, unexpected output, performance bottlenecks, security concerns, or behavior that doesn't match expectations. Consult the PG-lib wiki (/home/vblinux/llm-wiki-home/PG-lib) for root cause and correct syntax/API. For routine new code with clear syntax, skip it to keep speed.
version: 1.0.1
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [pg-lib, wiki, knowledge-base, debugging, php, mysql, csharp, avalonia, layui]
    related_skills: [wiki-docs-crawl, llm-wiki]
---

# PG-lib Wiki（程式開發知識庫）— 除錯優先參考源

本地程式開發知識庫，收錄本團隊主要技術棧的提煉語法與完整原文收錄。**除錯／排解異常時優先查這裡**（錯誤訊息、非預期輸出、效能瓶頸、資安疑慮、行為不符預期），找根因與正確寫法；語法明確的常規開發不必強行查，避免拖慢效率。

## Path
- Root: `/home/vblinux/llm-wiki-home/PG-lib`
- 索引：`index.md`（Entities / Concepts / Comparisons 三大區塊 + Archives）
- 提煉概念頁：`concepts/`（查語法最常落點，每頁 ≥2 外向 `[[wikilinks]]`）
- 實體頁：`entities/`（每種技術一頁：php/mysql/jquery/layui/csharp/dotnet/avalonia/python/android）
- 比較頁：`comparisons/`
- 完整原文原始檔庫：`raw/articles/`（16,000+ 頁，含 php-manual ~11k、mysql-tutorial.org、api.jquery.com、avalonia-docs、docs.python.org、w3schools-csharp、mslearn-csharp-zh-tw…）
- 規範：`SCHEMA.md`（frontmatter / tag taxonomy / 更新政策）；動機記錄：`log.md`

## How to query
1. 先讀 `index.md` 找對 slug（Entities 認識技術、Concepts 查語法）。
2. 找具體函式/語法：`grep -rn '<符號>' concepts/ raw/articles/`（concepts 供快速參考，raw 供溯源）。
3. 要「最新原文」時看 `raw/articles/<site>/MANIFEST.md`（含 combined_sha256，可做漂移偵測）。

## Update workflow（當被要求更新資料時）
完整流程見 `wiki-docs-crawl` 技能。精簡版：
1. 用對應 `scripts/crawl_*.py` 重抓來源到 `raw/articles/<site>/`（平行爬取開 background:true）。
2. `python PG-lib/scripts/wiki_ingest_validate.py <outroot> --manifest` 驗證（fm_bad=0、sha_mismatch=0）。
3. 提煉成新/更新的 `concepts/` 頁，bump `updated`，登記進 `index.md`。
4. `python PG-lib/scripts/verify_links.py` 跑 integrity check（0 broken / orphan）。
5. append 一筆到 `log.md`。

## Contributing conventions
- 每頁 YAML frontmatter（title/created/updated/type/tags/sources）；更新要 bump `updated`。
- 用 `[[wikilinks]]` 互連，每頁 ≥2 外向連結。
- 新增/改頁面後登記到 `index.md` 對應區塊；每個動作 append 到 `log.md`。
- tag 必須來自 `SCHEMA.md` 的 taxonomy；新 tag 先加再使用。

## Honest scope
- `raw/articles/` 是不可變來源素材；提煉後的參考語法在 `concepts/`。改事實以較新的來源為準（見 SCHEMA.md Update Policy）。
