---
name: content-ingestion
description: Convert scraped article HTML into in-memory JS data arrays.
version: 1.0.0
metadata:
  hermes:
    tags: [content-migration, scraping, html-parse, data-model]
---

# Content Ingestion — Scraped HTML → Structured Data Model

Use when you need to port an existing website's article/blog/case-study content into a **static frontend that renders from an in-memory JS array** (e.g. `window.BLOG = [...]`), rather than from a database or CMS.

For the reverse operation — auditing an **existing** `data.js` for TOC-vs-body dead anchors, truncated body, and other content-migration defects — see `references/toc-integrity-audit.md`.

## The class of problem

A target site has N articles as server-rendered HTML pages (`/blog/{id}`). Your clone stores them as structured objects in a `.js` file that the frontend iterates and renders. You must:
1. Fetch each page's HTML.
2. Extract the article body into typed blocks (heading / paragraph / quote).
3. Escape for JS string literals.
4. Insert into the existing data array, matching its exact shape.

## Step 1 — Inspect the target data model FIRST

Before writing anything, read an existing entry in the destination file to match its **exact** field names and structure. Common fields: `id`, `title`, `date` (format matters — e.g. `YYYY/MM/DD` vs `YYYY-MM-DD`), `img`/`thumbnail` (path relative to a known base, often `blog/thumb_*.webp` or a default), `excerpt`, `toc`, `body[]`.

Also read the **renderer** (`detail.js` / list template) so you know:
- How each body type maps to HTML (`h2`→`<h2>`, `quote`→`<blockquote>`, else `p`).
- Where `img` is resolved (so the path matches what the renderer expects).
- Whether `toc`/`excerpt` are optional or required.

## Step 2 — Fetch and probe structure

Fetch a few pages. Identify the **article container** (`<article>...</article>` is most reliable; fall back to a known marker like an update-time string). Within it, extract block-level elements in document order:
- Headings: `<h1>/<h2>/<h4>` → `{type:'h2', text}` (map all heading levels to the model's heading type).
- Paragraphs: `<p>` → `{type:'p', text}`.
- Blockquotes/quotes if present → `{type:'quote', text}`.

Strip tags, collapse whitespace (`\s+`→space), trim. **Skip structural noise** like TOC headings that exist only on the source page for navigation.

## Step 3 — Convert with a script (don't hand-type)

Write one Python script that loops over all fetched files and emits the JS array entries in the exact format. Key details:
- **Escape** backslashes and double-quotes before embedding in string literals.
- Build `excerpt` from the first substantive paragraph (truncate to a fixed length).
- Build `toc` from heading texts (cap at N, e.g. 5).
- Use a **default image** when source pages carry no thumbnail (`blog/thumb_default.webp`).
- Emit via `python3 script.py > generated_entries.js`, then insert the block into the destination file.

## Step 4 — Insert and verify

Insert the generated block right before the closing `];` of the array (add a trailing `,` to the last existing entry). Then:
1. `node -c <file>` or load in Node to confirm valid JS syntax.
2. md5-compare src vs deployed copy after `sudo cp`.
3. Render with headless Chrome (`google-chrome --headless=new --dump-dom`) and assert the expected article count / cards appear — not just that the file loaded.

## Pitfalls
- **Date format drift**: source may be `YYYY-MM-DD`; destination model may want `YYYY/MM/DD`. Normalize explicitly.
- **img path mismatch**: if the renderer resolves `../img/` + entry.img, a wrong base silently shows broken images. Match existing entries' convention exactly.
- **Empty excerpt fallback**: guard against 0-length excerpts for short articles.
- **Over-extracting navigation**: skip TOC headings, metadata lines, and footer boilerplate that leaked into the article region.
