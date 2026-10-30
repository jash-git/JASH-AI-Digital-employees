# Taiwan Law Corpus (MOJ / tw-law dataset)

Domain depth for ingesting Taiwanese law into the wiki. Only needed when working with this corpus;
the general procedure lives in SKILL.md.

## Sources
- **Hugging Face:** `lianghsun/tw-law` — auto-synced from MOJ, weekly updates deduped by `UpdateDate`.
  Configs: `ch_law_full_text`, `ch_order_full_text`, `ch_law_articles`, plus `en_*` variants.
- **Origin:** Ministry of Justice National Laws Database (全國法規資料庫), open API at `law.moj.gov.tw`.
- **Grain for a wiki:** use the `_full_text` config (one row = one complete law/order) for entity
  pages. `*_articles` (one row per article) is finer-grained and much larger — keep as raw, do not
  page per article.

## Category field quirk (costs time if missed)
- The `category` value is a MOJ breadcrumb joined by the **full-width** `＞` (U+FF1E), e.g.
  `行政＞交通部＞郵政目`. It is NOT ASCII `>`, and not `/`. Split on both
  (`re.split(r"[＞/]", cat)`) or grouping collapses to one page per leaf instead of by top-level
  domain. This is the classic bug that floods the wiki with near-duplicate orphan pages.
- Top-level segments map to wiki domains: `憲法/總統/立法/國民大会 -> 憲法`, `行政 -> 行政法`,
  `司法 -> 訴訟程序`, `考試 -> 行政法`, `監察 -> 憲法`. Anything whose first segment is
  `廢止法規` is repealed.

## Repealed vs current
- Detect repeal from the `abandon_note` field (废止备注) OR a category whose first segment is
  `廢止法規`. Flag these in frontmatter (`repealed: true`) and group them separately so users know
  they are historical, not current law.

## Provenance & drift
- Content is Taiwan government-published law under the Government Data Open License — **attribute
  "全國法規資料庫，法務部"** on synthesized pages.
- Store the raw `_full_text` file and record its sha256 (in a `_SOURCE.md` note or raw frontmatter).
  On re-ingest, recompute and compare to detect MOJ changes before updating any page.

## Scope decisions
- `法律` (Acts) is the core; `命令` (Orders — rules/regulations) is roughly 4x larger and lower
  hierarchy — ingest separately on request. English (`en_*`) coverage is sparse: only laws with a
  `has_eng_version` flag have an English counterpart.
