---
name: tw-law-wiki-query
description: "Taiwan law wiki only; no fabrication; cite source."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [wiki, taiwan-law, legal, research, no-fabrication]
    category: research
    related_skills: [llm-wiki]
---

# 台灣法律 Wiki 查題（限 wiki、不編造）

Answer Taiwan-related questions using ONLY this vault. No outside knowledge, no fabrication, always cite source.

## When to Use
User asks a Taiwan question and signals it must come from the Taiwan law wiki only. Trigger phrases (繁體中文):
- 「用台灣法律wiki查」
- 「只從wiki回答」
- Any phrasing where the user wants the answer sourced strictly from this vault.

## Wiki Location
`/home/vblinux/llm-wiki-home/tw-law` (also set as `WIKI_PATH` in `~/.hermes/.env`).
A directory of interlinked markdown:
- `entities/` — 1343 laws + 10415 orders (one page per statute/order, flat dir)
- `concepts/` — 25 curated pages: core-statute guides + high-frequency domain navigators (稅務稽徵、勞動條件與勞工保護、金融監督、食品與藥物安全) + reference-tools page
- `index.md`, `SCHEMA.md`, `log.md`

## Strict Rules (non-negotiable)
1. **Only this vault.** Draw facts solely from files under this path. Do NOT pull in general knowledge, web results, or memory about Taiwanese law unless the user explicitly asks for outside context.
2. **If not found → say 「沒有」.** If the wiki has no relevant page/term, answer plainly that it is not covered. Never invent a statute name, article number, regulation title, or rule to fill a gap.
3. **Cite at the end.** When you find corresponding data, append correct source attribution after the answer:
   - Origin of every page: 法務部全國法規資料庫（MOJ, law.moj.gov.tw）under 政府數據開放授權.
   - Point to the specific page(s): e.g. `[[銀行法.md]]`, or a concept page like `[[金融監督.md]]`.

## How to Query
1. Read `index.md` (sectioned catalog) to locate relevant pages/sections.
2. For this 10k+ page vault, also run `search_files "<term>" path="$WIKI" file_glob="*.md"` — the index alone may miss leaf command pages.
3. `read_file` the matching entity/concept pages.
4. Synthesize a concise answer from those pages only.
5. Append source attribution (Rule 3).
6. If nothing matches, reply 「沒有（wiki 內無相關資料）」and stop — do not speculate or hedge into outside knowledge.

## Notes
- Raw sources under `raw/` are immutable; never edit them. Corrections belong in wiki pages.
- The vault is refreshed from MOJ via the lianghsun/tw-law dataset. See `log.md` for update history and `scripts/generate_corpus.py` to rebuild.
- To refresh with new laws: re-download from MOJ/HuggingFace, verify sha256 in `raw/laws/_SOURCE.md`, then run the generators (see `llm-wiki` skill).
- **Concrete live-pull procedure** (`scripts/fetch_moj_live.py`, added 2026-11-02): MOJ open API
  endpoints `https://law.moj.gov.tw/api/ch/law/json` and `/ch/order/json` return a **ZIP** (not raw
  JSON) containing `ChLaw.json` / `ChOrder.json` = `{"UpdateDate":..., "Laws":[{LawLevel,LawName,
  LawURL,LawCategory,LawModifiedDate,...,LawForeword,LawArticles:[{ArticleType,ArticleNo,ArticleContent}]}]}`.
  The script converts MOJ fields → corpus schema (name/text/category/level/doc_type/update_date) using
  the same logic as `lianghsun/tw-law-sync`, then writes `ch_law_full_text.jsonl` / `ch_order_full_text.jsonl`
  to a target dir. Re-run generators (`generate_corpus.py` + `generate_concepts.py` +
  `generate_order_concepts.py`) to rebuild all pages.
- **Gotchas:** (0) `generate_corpus.py` REWRITES `raw/laws/_SOURCE.md` from its own generic template,
  wiping manually-added MOJ live API + curl + sha256 detail. After every rebuild, restore the rich
  `_SOURCE.md` (keep source/curl/sha256/本次異動/備份 bullets) via patch — don't let it degrade.
  (1) MOJ endpoints return ZIP — unzip, take the single `.json`. (2) On this VM Python's
  `urllib` fails with `SSL: CERTIFICATE_VERIFY_FAILED … Missing Subject Key Identifier` against MOJ's cert;
  use **curl** for downloads (the script already shells out to curl). (3) HF dataset `lianghsun/tw-law`
  updates weekly but lags MOJ by weeks/months — re-downloading it often yields byte-identical files; pull
  live from MOJ when you need genuinely current law. (4) Always diff new vs current raw before replacing, and
  back up old `raw/laws/*.jsonl` to `raw/laws/_backup_<date>/`.
