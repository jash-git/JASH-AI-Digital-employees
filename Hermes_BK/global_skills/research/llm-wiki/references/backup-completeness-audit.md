# Backup Completeness Audit

Verify that every external source a wiki references is actually preserved locally in
`raw/`. This answers the user's standing concern: *"I can't confirm sources stay online,
so back up everything."* A recorded URL or a transcription note is **not** a backup — only
a local file survives a source site vanishing.

Run this whenever ingesting sources, when the user asks whether their materials are backed
up, or as part of any lint / health-check.

## Procedure

1. **Inventory `raw/` by tier.** List every file and classify it:
   - `.md` transcriptions (web articles, lecture notes)
   - `.pdf` / `.zip` binaries (original documents, source-code repos)
   - data-corpus files (`.jsonl`, `.csv`) holding whole corpora

2. **Extract external URLs from pages.** Grep `concepts/`, `entities/`, `comparisons/`,
   `queries/`, and `raw/articles/` for `https?://…`, dedupe by domain. Pages that cite a
   live URL but keep all content self-contained via `^[raw/...]` provenance markers are
   fine — the risk is a page whose substance lives only at an external link.

3. **Match each URL to a local file.** Resolve by filename slug, domain, or the
   `^[raw/…]` / `sources:` frontmatter provenance on the citing page. Any source with no
   matching local file is an **open gap**.

4. **Classify and close each gap.** Use the decision table below: download the real file
   into the right `raw/` subfolder, or — if it cannot be fetched now (rate limit, paywall)
   — record the URL and mark the source explicitly as *not yet backed up*. Never mark a
   source backed up when only a link exists.

5. **Verify binaries are real, not empty/corrupt.** `%PDF` header for PDFs, `unzip -t` for
   zips, non-zero size. A 0-byte or truncated download is worse than none (looks backed up).

6. **Report per tier.** State what is preserved as transcription vs binary vs data corpus,
   and list any open gaps with their URLs so they can be re-fetched later.

## Preservation-Tier Decision Table

| Source type | Preserve as | Why / notes |
|---|---|---|
| Web article with text layer | `raw/articles/<name>.md` transcription + `source_url` frontmatter | Content survives even if the site dies. |
| PDF with text layer | `raw/papers/<name>.pdf` **binary** (+ optional `.md`) | Keep the binary; extract text separately for pages. |
| Scanned PDF / screenshot (no text) | `raw/papers/<name>.pdf` **binary only** | Can't OCR here → still save the file; note "needs OCR" and record URLs. The current environment's inability to read it does not justify skipping preservation. |
| Source-code repository | `raw/repos/<name>.zip` (full clone/zip) | Preserve runnable code, not just a link. |
| Structured corpus (thousands of rows) | `raw/<data>.jsonl/.csv` + re-runnable generator script | Whole corpus local; don't rely on per-row pages alone. |

## Pitfalls

- **A URL in a notes/清单 file is not a backup.** It only documents where to fetch from
  later. If the site is gone, that note is useless — you need the bytes.
- **Don't substitute a transcription for the original.** A `.md` summary of a PDF loses
  everything the PDF has that the summary didn't capture. Keep both when possible; never
  replace the binary with only a summary.
- **Rate limits are usually self-inflicted.** Hammering a source with rapid/parallel
  requests trips anti-bot throttling and makes even small downloads fail. Space requests,
  retry once or twice, and confirm each file's header before declaring success. (A loop
  that curls bare filenames instead of full URLs silently creates no files — always build
  the complete `scheme://host/path`.)
- **Same book, different mirror = still one source.** Two PDFs of the identical title/author
  from different mirrors are redundant copies; note the relationship rather than presenting
  them as distinct works.
