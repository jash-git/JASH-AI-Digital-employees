# Bulk Ingest: Link Discovery & Source Recovery

Depth for when a batch ingest must go beyond the URLs handed over, or when a
source hides its real files. Pair with the "Bulk Ingest" section of SKILL.md.

## Follow each landing page's own resource tree

A course page, syllabus, blog index, or department site is a hub: every link on
it points at more in-domain material. When asked to also gather related sources
from a site (not just the given URLs), do this instead of ingesting only the
handed-over links:

1. Extract the page and pull every in-body URL (`re.findall(r'https?://[^\s)"\]]+', body)`).
2. Keep the on-topic ones; drop nav/footer/legal links.
3. For sites with a sitemap or category structure, follow it to enumerate the full
   set (e.g. per-chapter notes under one course root) before declaring ingest complete.
4. Dedupe by URL; save each new capture as its own raw file with frontmatter + sha256.

This turns one landing page into a coherent cluster instead of isolated clips.

## Recover PDF links hidden in HTML tables

Some sites list downloadable files inside an HTML `<table>` (a "download zone").
`web_extract` returns the table's *text* but strips the anchor `href`s, so the
direct file URL is not visible in the extracted markdown — you cannot re-fetch it
from that capture alone. Recover it by:
- reading the page source directly (browser tool / curl) to find the href pattern, or
- following the site's sitemap / category page, which usually exposes the real URLs.

If a direct link can't be recovered, keep the index/landing page as the raw record
and note in log.md that the underlying files were not captured — never invent URLs.

## Decide what to skip (avoid a junk pile)

Not every discovered link is wiki-worthy. Skip and record in log.md:
- Pure-math or off-domain pages when the wiki is domain-scoped.
- Thin preview-only pages (e.g. cloud-drive landing pages that only say "cannot preview").
- Product catalogs / spec sheets with no conceptual content.

Recording skips keeps a later session from re-ingesting the same dead ends.
