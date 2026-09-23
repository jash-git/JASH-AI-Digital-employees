---
name: web-content-extraction
description: "Extract full article text when web extraction fails."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Research, Extraction, Full-Text, Curl, Scraper]
---

# Web Content Extraction

Use when you need the **full text** of an article, essay, or document — not a
summary or search snippet. Distinct from `blocked-page-recovery` (which targets
403/paywall/WAF pages): here the page *returns* content but standard extraction
(`web_extract`) fails, or returns only boilerplate.

## First gotcha: web_extract's default backend is search-only

The bundled `web_extract` tool uses DuckDuckGo by default, and that backend is
**search-only**. It returns empty results when you pass real URLs to extract page
content (`"success": false` or an empty body). Don't loop on it.

Fix: set a real extraction backend in config
(`web.extract_backend = firecrawl | tavily | exa | parallel`) and retry, **or** go
straight to curl + the browser tool. In practice curl is fastest for static HTML.

## Second gotcha: Google / Bing are not scrapable via curl

`curl https://www.google.com/search?q=...` returns a ~3.5 KB captcha/JS-redirect
interstitial (HTTP 200 but no links). Bing wraps result links in `r.bing.com/rp/…`
redirects and hard-to-parse `data-href` attributes. Neither is reliable for
scraping results via curl alone — use the `web_search` tool to find candidate URLs,
then fetch each candidate directly with curl.

## The recipe (curl-first)

See `references/full-text-extraction.md` for the full worked example and code.

1. **Fetch candidates with a realistic browser UA + headers.** Many sites return
   000/403 without a real UA; Google/Bing need `Accept-Language`:
   ```bash
   UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
   curl -sL -A "$UA" -H "Accept-Language: zh-TW,zh;q=0.9" \
     -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
     -o /tmp/page.html --max-time 40 "$URL"
   ```

2. **Validate the body, not just the status code.** A candidate may return HTTP 200
   with a thin JS shell (Facebook `m.facebook.com` posts are ~1.5 KB; Google is
   ~3.5 KB). Check size AND grep for target keywords before trusting it:
   ```bash
   sed 's/<[^>]*>//g' /tmp/page.html | tr -s ' \t\r' '   ' > /tmp/page.txt
   wc -c /tmp/page.txt; grep -o '.\{0,60\}KEYWORD.\{0,300\}' /tmp/page.txt | head
   ```

3. **Locate the article body by distinctive phrases.** Strip tags → collapse
   whitespace → `grep -o` around an in-body quote (a title line is boilerplate; an
   in-body quote marks the real essay). Finds start/end without parsing HTML.

4. **Verify completeness at the end boundary.** Confirm extraction stops at the
   natural conclusion, not mid-sentence — so you know you have the whole piece, not
   a truncated excerpt.

## When to prefer the browser tool instead

If a source is JS-rendered and curl returns only a shell (SPA / dynamic content),
use the `browser` tool. Its daemon detects Chrome via its own runtime dir +
`DevToolsActivePort`, so manually launching Chrome on port 9222/9333 does NOT get
picked up — let the harness launch it itself.

## Related skills
- `blocked-page-recovery` — for 403 / paywall / WAF pages (fallbacks: Wayback, archive.today, Jina).
- `grounded-citations` — cite recovered copies with provenance.
