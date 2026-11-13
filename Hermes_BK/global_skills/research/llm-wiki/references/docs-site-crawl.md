# Bulk Site Capture: Documentation Sites into raw/

Depth for when a source is a full documentation site (hundreds–thousands of pages) and
`web_extract` per-URL is too slow or loses structure. Pair with the "Ingest" section of SKILL.md.

## When to build a crawler instead of using web_extract
Use a dedicated crawler when:
- The site has ≥ ~50 pages reachable from one sitemap, OR
- Pages are large (100KB+ HTML) so per-page extraction is slow, OR
- You need uniform structure across all pages (same frontmatter, same section layout).

`web_extract` stays right for single pages or small clusters. For a full site, a crawler that
reuses one connection pool and converts in bulk is far faster and produces uniform raw files.

## The pipeline
1. **Enumerate from the sitemap.** Download `sitemap.xml`; parse `<loc>` entries; group by top-level
   path segment (e.g. `/docs/`, `/controls/`, `/api/`). This is the authoritative page set — don't
   guess URLs.
2. **Parallel fetch.** Use a thread pool (`ThreadPoolExecutor(max_workers=…)`). Reuse one
   `requests.Session` so TCP connections are reused across requests instead of re-handshaking per page.
3. **Convert HTML→Markdown.** `markdownify.markdownify(html, ...)`. For sites with syntax highlighting
   (Prism/Highlight.js), the default converter collapses multi-line code blocks to one line — iterate
   the highlighted tokens and join with `\n` (see below).
4. **Write raw file + frontmatter.** Save as `<section>/<slug>.md` under `raw/articles/<site>/`. Prepend:
   ```yaml
   ---
   source_url: <original URL>
   ingested: YYYY-MM-DD
   sha256: <hex digest of the body below this block>
   ---
   ```
   Compute sha256 over the **body only** (everything after the closing `---`), not the frontmatter.
5. **Verify integrity.** After the run, re-read each file, strip trailing newlines, and confirm its
   stored sha256 matches a fresh digest of the body. This catches silent truncation/overwrite that a
   page count alone can't reveal.

## Docusaurus-specific extraction notes
Docusaurus (docs.avaloniaui.net and many framework docs) renders pages as static HTML with Prism syntax
highlighting and hashed class names:
- **Main content** lives in `<main class="docMainContainer_TBSr">` inside `.theme-doc-markdown`. Extract
  that subtree; the rest is nav/TOC/footer.
- **Prism code blocks** use `pre[class*="prism-code"]` with one `span.token-line` per line. markdownify's
  default joins them without newlines → rejoin the spans with `\n` to preserve multi-line listings.
- **TOC / admonition labels use HASHED class names** (e.g. `tableOfContentsWrapper_cC_z`,
  `admonitionHeading_3kQ`). Exact-match selectors like `.toc-highlight` or `.admonition-title` will NOT
  match — select by attribute substring: `[class*="tableOfContentsWrapper"]`, `[class*="admonitionHeading"]`.
- **Heading anchors** carry a trailing `[](#anchor "title")` suffix; strip with
  `re.sub(r'\[\([^#][^)]*\)\]', '', md)`.

## Pitfalls
| Symptom | Rule | Why |
|---|---|---|
| TOC / admonition text leaks into raw files | Select by `[class*="substring"]`, not exact class names | Docusaurus hashes class names at build time; the literal name shown in docs is absent from the HTML |
| Code blocks collapse to one line | Iterate `span.token-line` and join with `\n` | Prism emits each source line as a separate token span; markdownify concatenates them without newlines |
| Progress never updates / run looks stuck | Use `cf.as_completed(futures)`, not `ex.map()` | `map` yields results in submission order, so the slowest early task blocks every later print even though workers are already writing files |
| Log shows DONE but file count is short | Don't parse background logs for completion — count files on disk + use background notify | Piping process output through `tr -d '\000'` corrupts lines with null bytes, merging/splitting them; the log becomes unreliable |
| Some pages silently missing / overwritten | When writing into subdirectories by section, prefix the output path with the section dir (`outroot/sec/relpath`) | Dropping the section segment makes differently-named URLs collide on one filename → later writes overwrite earlier ones |
| Crawler dies mid-run and you can't restart cleanly | Kill by PID (pgrep excluding self), not `pkill -f script.py` | `pkill -f` matches its own shell command line and SIGTERMs the controlling process before the crawler is actually dead; a lingering writer then writes stray files that inflate counts |
| Stray files appear in shared dirs after a kill | Confirm every crawler process is dead before cleanup/restart | An abandoned worker keeps writing until it finishes its current page, scattering files into wrong locations and corrupting your count |

## Scope discipline
- Decide up front what "complete" means (which sections/URLs) so you don't capture pages the user didn't ask for.
  Auto-generated API reference dumps are often thousands of near-duplicate member-listings — capture them only if
  the user explicitly wants full fidelity, and record that decision in log.md.
- Record skips in log.md so a later session doesn't re-capture the same dead ends.
