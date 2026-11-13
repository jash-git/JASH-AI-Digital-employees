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
- Background crawling needs background:true on the terminal tool. nohup and bare `&` are rejected by the shell wrapper and abort before launching.
- The crawl log is corrupted with null bytes (\u0000) and can print phantom "DONE" lines or merged counts. Never parse it for progress — trust the on-disk file count and the background DONE notification.
- Killing a mid-crawl process leaves stray top-level directories (writes that missed their section prefix). Before re-running: kill all `python crawl_docs.py` processes, delete any top-level dir that is not a known section, then wipe the target section (`rm -rf <outroot>/<section>`).
- For API trees use --subpaths so files land in namespaced dirs (e.g. `api/avalonia/controls/button.md`). Flat mode falls back to `-2`/`-3` suffixes that are hard to read and easy to lose track of.
- Namespace landing pages (`/api/<ns>/`) slug to top-level `<ns>.md`. Regenerate MANIFEST by walking the whole tree, not just section subdirs, or you silently drop them.
- Every file's frontmatter sha256 must equal sha256 of its body (the text after the closing `---`). The validator checks this against `sha256(body.rstrip("\n"))` — it strips trailing newlines before hashing. **Hash exactly what the validator strips:** build each file as `frontmatter + "\n\n" + body_no_trailing_newline + "\n"` and hash the body WITHOUT its trailing newline. A mismatch on ALL files is almost always this hashing-consistency bug, not bad conversion; a mismatch on ONE file points at genuinely broken/placeholder content for that page.
- combined_sha256 in MANIFEST is computed over every body concatenated in path-sorted order — recompute it whenever files change to keep drift detection valid.
- **Some sites hide content pages from crawlers.** php.net/manual/en/ is the case: every index page links only to nav, so BFS never reaches individual `function.X.php` / `ref.Y.php` pages. Use the authoritative source repo instead — for PHP that's the official `php/doc-en` DocBook XML tree (what php.net builds from). Clone it and convert with `PG-lib/scripts/convert_phpdocen.py --src <repo> --out raw/articles/php-manual`. It handles doc-en's dual entity styles (DTD `<!ENTITY>` + DocBook `<entity name=>`) via regex+recursive expansion, renders methodsynopsis/parameter tables/code blocks/examples. ~11k granular pages incl. per-class members; skip <60-alnum stubs by quality gate.

## Verification
- Validator prints `fm_bad=0 sha_mismatch=0` and section counts sum to the find total.
- MANIFEST.md pages_captured equals the on-disk .md count (excluding MANIFEST.md).
- combined_sha256 changes only when content changes; re-run the validator later to detect drift.