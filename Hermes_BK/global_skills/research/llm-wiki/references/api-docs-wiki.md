# Building a Wiki from Programming Documentation

When the wiki's domain is **software-development reference** (languages, frameworks,
APIs) — e.g. ingesting php.net, docs.python.org, api.jquery.com, dev.mysql.com,
learn.microsoft.com/dotnet, docs.avaloniaui.net, developer.android.com — structure the
output as a small fixed *layering* instead of one page per doc heading. This keeps the
graph dense and cross-referenced rather than a flat pile of API dumps.

## Layering (4 tiers)
- **raw/articles/** — immutable captures of each source's landing + core reference page
  (via `web_extract`). One file per source, with `source_url` / `ingested` / `sha256`
  frontmatter. These are the provenance anchors; never edit them.
- **entities/** — one page per technology (php, mysql, jquery, csharp, dotnet,
  avalonia, python, android…). Each: what-it-is, core features, version/ecosystem, and
  ≥2 outbound `[[wikilinks]]`.
- **concepts/** — cross-referenced reference-syntax pages: the queryable core where LLM
  queries actually land (e.g. `sql-syntax-basics`, `php-database-pdo`,
  `jquery-selectors-events`, `avalonia-xaml-controls`). One page per recurring topic;
  include a short working code example and link to its entity + sibling concepts.
- **comparisons/** — selection guides that tie technologies together (e.g. cross-platform
  UI frameworks: Avalonia vs MAUI vs Flutter vs RN), table-first with a conditional verdict.

## Cross-link discipline
- Every page links to ≥2 others via `[[wikilinks]]`. For dev wikis the natural graph is
  entity↔concept: an entity points at its concept pages; a concept points back at its
  entity plus 1–2 sibling concepts.
- Resolve links **by filename across the whole vault**, not within one directory — an
  entity in `entities/` must resolve a `[[concept]]` that lives in `concepts/`. Use
  `scripts/verify_links.py` to check deterministically.

## Page thresholds for docs
- Create an **entity** when a technology is a source's central subject, not a passing mention.
- Create a **concept** only for syntax/topics that recur across 2+ sources or are the main
  lookup target. Do NOT make a page per API method: dump the full surface into raw/ and
  summarize the core in concepts/.
- A **comparison** earns its place when the user is choosing between technologies (选型),
  not merely to list them.

## Verify before reporting done
Run `scripts/verify_links.py` on the wiki: zero broken links, every page meets the
outbound minimum. Do not hand-count — the audit is deterministic and catches cross-directory
links a per-file scan misses.
