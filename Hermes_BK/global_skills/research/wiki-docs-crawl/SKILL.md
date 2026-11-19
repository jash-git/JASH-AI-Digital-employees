---
name: wiki-docs-crawl
description: Capture docs sites into the wiki as validated markdown.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [docs-crawl, wiki-ingest, markdown, sitemap]
    related_skills: [llm-wiki]
---

# Wiki Docs Crawl Skill

Capture an external documentation site into a wiki's `raw/articles/` tree as clean Markdown with frontmatter (source_url, ingested, sha256 of body), validate every file, and regenerate a MANIFEST.md with a combined checksum. Handles hand-authored docs pages plus auto-generated `/api/**` reference trees. Not a one-page fetcher — it ingests whole sites.

## When to Use
- User wants to archive/ingest a full docs site (e.g. `docs.<vendor>.net`) into the wiki as Markdown.
- Need an API reference tree (`/api/**`) captured alongside hand-authored pages.
- Want a verifiable manifest + combined sha256 to detect future drift.

Don't use for: fetching and summarizing a single page (use web_extract), or sites behind login (stop and ask).

## Prerequisites
- Python 3 with `markdownify`, `beautifulsoup4`, `lxml`, `requests`. Recreate the ingest venv if missing:
  `python3 -m venv <venv> && <venv>/bin/pip install markdownify beautifulsoup4 lxml requests`
- Durable tools live at `PG-lib/scripts/crawl_docs.py` (needs the venv) and `PG-lib/scripts/wiki_ingest_validate.py` (pure stdlib). Both take paths as arguments, so they work on any wiki root. Activate the venv before running the crawler.

## How to Run
Canonical crawl (hand-authored + API), launched through the terminal tool with background:true:
`terminal(command=". <venv>/bin/activate && python PG-lib/scripts/crawl_docs.py --sitemap <url> --outroot <wiki>/raw/articles/<site> --only docs,controls,xpf,troubleshooting,api --subpaths --workers 24", background=True)`

Validate + regenerate manifest:
`terminal(command="python PG-lib/scripts/wiki_ingest_validate.py <wiki>/raw/articles/<site> --manifest")`

## Procedure
1. Confirm reachability and scope **before** committing. Check for a usable sitemap (`<base>/sitemap.xml`, not only under the docs path) and count URLs per section. If there is no usable sitemap, enumerate via BFS from the index/section indexes following internal links with a site-specific converter (see references/feasibility-check.md). Pre-fetch 3–5 canonical pages first: if they return 200 with real body text, proceed; if most canonical pages 404 globally, stop and flag the site as not capturable now rather than launching a multi-hour crawl against it. Choose sections to capture; add `--subpaths` for any `/api/**` tree.
2. Launch the crawl with background:true. Never use nohup or a bare `&`.
3. Monitor by counting files on disk (`terminal(command="find <outroot>/<section> -type f -name '*.md' | wc -l")`), not by parsing the crawl log — see Pitfalls. Wait for the background DONE notification.
4. Run the validator with --manifest. Every section must report `fm_bad=0 sha_mismatch=0`. A non-zero fail count means some URLs returned non-200; inspect before finishing.
5. Confirm MANIFEST pages_captured equals `find <outroot> -name '*.md' | wc -l` (excluding MANIFEST.md itself).

## Pitfalls
- **Your VM IP gets rate-limited — switch egress.** When a live site throttles your crawler (bursts return 403/429/5xx or a placeholder body while single spaced requests succeed), stop hammering curl/requests from that same IP. Use `web_extract` instead: the tool backend fetches via its own egress, not your VM's IP, so it sidesteps per-IP quotas. It returns cleaned Markdown (post-process for fences/nav); use direct HTTP only when the site isn't throttling or when you need raw HTML for a bs4 converter.
- **web_extract length is not page content length.** For fragmented or freshly-redesigned layouts, web_extract serializes poorly and returns short Markdown even when the page has substantial body — a "short" result does not mean the page is thin (a core tutorial can come back as one line). When a page that should be substantial comes back short, fetch the raw HTML and run a bs4 converter (`convert_main`) on it; single spaced requests still succeed where bursts are throttled.
- **Detect client-side-rendered content before committing to a method.** Inspect the fetched raw HTML for the site's expected static markers (code blocks, `w3-panel`, definition lists). If those markers are absent but the page should contain them, the content loads via JavaScript — static extractors and web_extract both return only nav/placeholder. A browser with JS execution is required; do not burn calls retrying a static method against rendered-only content.
- **Batched extraction loops hit execute_code's ~5-minute cell timeout mid-iteration and lose all in-memory state.** Keep each call to ≤~20–28 items and persist progress after every success (write each file / append to a done-list immediately), never only at the end — a timeout then discards only in-flight items, not completed ones. On resume, treat files already on disk as the authoritative done-set, not any in-memory counter.
- Background crawling needs background:true on the terminal tool. nohup and bare `&` are rejected by the shell wrapper and abort before launching.
- The crawl log is corrupted with null bytes (\u0000) and can print phantom "DONE" lines or merged counts. Never parse it for progress — trust the on-disk file count and the background DONE notification.
- Killing a mid-crawl process leaves stray top-level directories (writes that missed their section prefix). Before re-running: kill all `python crawl_docs.py` processes, delete any top-level dir that is not a known section, then wipe the target section (`rm -rf <outroot>/<section>`).
- For API trees use --subpaths so files land in namespaced dirs (e.g. `api/avalonia/controls/button.md`). Flat mode falls back to `-2`/`-3` suffixes that are hard to read and easy to lose track of.
- Namespace landing pages (`/api/<ns>/`) slug to top-level `<ns>.md`. Regenerate MANIFEST by walking the whole tree, not just section subdirs, or you silently drop them.
- Every file's frontmatter sha256 must equal sha256 of its body (the text after the closing `---`). The validator checks this against `sha256(body.rstrip("\n"))` — it strips trailing newlines before hashing. **Hash exactly what the validator strips:** build each file as `frontmatter + "\n\n" + body_no_trailing_newline + "\n"` and hash the body WITHOUT its trailing newline. A mismatch on ALL files is almost always this hashing-consistency bug, not bad conversion; a mismatch on ONE file points at genuinely broken/placeholder content for that page.
- combined_sha256 in MANIFEST is computed over every body concatenated in path-sorted order — recompute it whenever files change to keep drift detection valid.
- **W3Schools MySQL (`/mysql/`, `scripts/crawl_w3_mysql.py`)** has quirks beyond C#/C++: examples are `<div class="w3-code sqlHigh">` with `<br/>` line breaks (NOT `<pre>`), so code needs a custom converter to ```sql fences; content lives in `div.w3-main` for BOTH layouts — tutorial pages nest the body in `w3-col.l10`, challenge/exam pages put it directly in `w3-row`. Use `w3-main` as the content root (it never contains the sidebar nav, so nav is excluded automatically). Also force `r.encoding="utf-8"` after fetch (W3Schools omits charset on Content-Type → requests defaults to latin-1 and mangles accents like `México`), and decompose only the exact `<a>REMOVE ADS</a>` link — a container-level `get_text()` match for "remove ads" drops whole subtrees including real content.
- **W3Schools JS (`/js/`, `scripts/crawl_w3_js.py`)**: live layout uses single-quoted attributes — the content root is `<div ... id='main'>` (bs4 finds by id regardless of quote style; a grep for `id="main"` misses it). Same converter shape as MySQL but code containers carry class `jsHigh`. **Throttle masquerades as HTTP 404:** W3Schools returns a ~9–10KB block body with status 404 to enforce a rolling per-minute quota, so known-good `.asp` URLs 404 under burst access. Treat 404 as recoverable (add it to the fetch retry-set) and crawl single-worker with backoff; single spaced requests still return 200. When your own IP is exhausted, fall back to `web_extract` (see above). web_extract returns nav-first Markdown — locate the article by its "Try it Yourself" marker (tutorials) or the first real H1 after skipping nav headers (reference pages); code arrives unfenced and glued to intro prose, so fence post-processing is required (see references/w3schools-extract.md).
- **W3Schools CSS (`/css/`, `scripts/crawl_w3_css.py`)**: same layout as JS — content root is `<div id="main">` (the w3-col.l10 div), highlighted code sits in `<div class="w3-code notranslate cssHigh">` inside `.w3-example` (so the generic `.w3-code` handler already fences it as ```css), and "Try it Yourself" links are `tryit.asp?filename=trycss_...` (not `tryc.php`). The nav also carries 60+ `css3_*` chapters, so URL patterns must match `css[A-Za-z0-9_-]+` — not just `css_…` — or you silently drop every css3_ page. **Enumerate the URL set LIVE but fetch content from Wayback:** Wayback rewrites internal hrefs to `web.archive.org/.../https://www.w3schools.com/css/…` URLs, so a path pattern matched against archived HTML never matches — seed enumeration from live pages (relative hrefs match) while content still comes from the throttle-free Wayback snapshot. Live seeds are rate-limited (rolling IP quota returns a 404/throttle body with no css hrefs), so verify each seed returned real content before trusting its links, and retry on failure.
- **Some sites hide content pages from crawlers.** php.net/manual/en/ is the case: every index page links only to nav, so BFS never reaches individual `function.X.php` / `ref.Y.php` pages. Use the authoritative source repo instead — for PHP that's the official `php/doc-en` DocBook XML tree (what php.net builds from). Clone it and convert with `PG-lib/scripts/convert_phpdocen.py --src <repo> --out raw/articles/php-manual`. It handles doc-en's dual entity styles (DTD `<!ENTITY>` + DocBook `<entity name=>`) via regex+recursive expansion, renders methodsynopsis/parameter tables/code blocks/examples. ~11k granular pages incl. per-class members; skip <60-alnum stubs by quality gate.

## Verification
- Validator prints `fm_bad=0 sha_mismatch=0` and section counts sum to the find total.
- MANIFEST.md pages_captured equals the on-disk .md count (excluding MANIFEST.md).
- combined_sha256 changes only when content changes; re-run the validator later to detect drift.