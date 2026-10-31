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
