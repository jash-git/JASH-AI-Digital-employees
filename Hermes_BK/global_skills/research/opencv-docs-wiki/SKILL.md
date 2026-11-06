---
name: opencv-docs-wiki
description: "Regenerate/maintain the per-version OpenCV docs wiki."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [wiki, knowledge-base, opencv, documentation, bulk-generation]
    category: research
---

# OpenCV Docs Wiki (generator-driven)

Location: `/home/vblinux/llm-wiki-home/opencv/`. Built on the `llm-wiki` skill pattern but
driven by a deterministic, idempotent generator so all versions stay in sync.

## When to use
User wants an OpenCV knowledge base from docs.opencv.org (per-version module coverage), or asks
to extend/regenerate this specific wiki. Load `llm-wiki` skill for the underlying conventions
(wikilinks, frontmatter, index/log, lint) — this skill adds the OpenCV-specific generator.

## Query & answer FROM the wiki (wiki-first mode)
When the user prefixes a question with a trigger (`Wiki:`, `[Wiki]`, or "用 OpenCV wiki 回答我")
or otherwise asks to prioritize this wiki, treat the wiki as the authoritative source:
1. `WIKI=/home/vblinux/llm-wiki-home/opencv` (hardcoded here; NOT the default ~/wiki).
2. Orient: read SCHEMA.md + index.md + last ~20 lines of log.md.
3. Find pages: grep index.md sections, then `search_files <term> path=$WIKI file_glob="*.md"`.
4. Read relevant pages with read_file; synthesize an answer CITED to wiki pages (`[[page]]`).
5. If the answer is NOT in the wiki: say so plainly and offer to ingest it from docs.opencv.org
   (add a raw article + module/concept page), rather than answering from memory or the open web.
6. File only valuable answers (deep dives / comparisons) into queries/; trivial lookups stay in chat.
7. Append a short note to log.md when you answer from the wiki (optional, low volume).

Default (no trigger): I may answer OpenCV questions from general knowledge or the web. The trigger
forces wiki-first + citation. Prefer the trigger whenever accuracy/version-matters (e.g. 5.x split).

## Architecture
```
opencv/
├── SCHEMA.md            # domain config; tag taxonomy (module/calibration/imgproc/...)
├── index.md / log.md    # catalog + action log (rebuilt/appended by generator)
├── scripts/build_modules.py   # THE generator — all curated content lives here
├── raw/articles/        # Layer-1 immutable inventories (one per version) w/ sha256
│   ├── opencv-modules-4.12.md
│   ├── opencv-modules-3.4.md
│   └── opencv-modules-5.0.md
├── version-{4x,3x,5x}.md    # one landing page per version (module inventory + highlights)
└── entities/            # one page per (module x version): <mod>-<ver>.md  (212 pages)
```
Grain = **per-version module overview** (scope + key API groups + representative functions +
usage + version notes). NOT per-function (that would be ~2500 pages of noise).

### External sources (raw/papers/ + raw/repos/ + raw/articles/ + resources/)
Books / official curricula / docs / code repos / web tutorials are ingested separately from the
generator. Full procedure + size-caveat decisions: `references/ingesting-repos.md`.
- Raw PDFs → `raw/papers/<name>.pdf` (immutable) with a companion `raw/papers/<name>.md` frontmatter
  (`source_url`, `ingested`, `sha256` over the whole file). Do NOT reproduce full book text.
- Code repos → download the GitHub **archive zip** (`raw/repos/<owner>-<repo>.zip`) — never the raw
  blob URL (fails on large files, returns HTML); see recipe below. Companion note at
  `raw/repos/<owner>-<repo>.md` (`source_url`, `ingested`, sha256 of the zip).
- Single web page / tutorial index → `raw/articles/<name>.html`.
- One overview page per source in `resources/` — frontmatter `type: summary`, `tags: [resource, …]`,
  `sources: [raw/papers/<name>.md | raw/repos/<name>.zip | raw/articles/<name>.html]`. Include an
  ACCURATE TOC (derive from the archive tree / extracted HTML; don't guess), a topic map cross-linked
  to `[[module-ver]]` pages, and version/accuracy caveats. List every resource page in the "Resources"
  section of index.md. See SCHEMA.md → "Resource Pages".
- **Keep pages lean.** Describe each source's structure + cross-link; do NOT inline-reproduce code or
  book text. Repo zips are often dominated by binaries/media/installers — say what the real content is
  and its rough fraction, and let that drive the description (see references/ingesting-repos.md).
- Image-only PDFs (book previews, scanned slides) have no text layer: `pdftotext`/`pdfinfo` return
  nothing. Describe via bibliographic metadata (title/author/publisher/ISBN) and mark the page
  image-based; OCR only if the user asks.
- Record sources that could NOT be retrieved (401/403/404/gated) in resources/index.md so they can
  be retried later with a fix (correct blob→raw filename, HF credentials, alternate host).

### Pruning stored reference material
`raw/repos/` + `raw/papers/` are local copies of external sources; resource pages describe them but
never inline-reproduce, so bloated zips are reclaimable. Before deleting anything: quantify each zip's
inside composition by extension bucket (binaries/installers/video/model-weights/fonts = bloat; code/docs/
images = real), then tier DELETE / TRIM / KEEP. **Never over-trim** — cut only re-downloadable bloat and
keep all code, docs, and the test images/examples load, or you break reproducibility for a few MB.
Always write `raw/repos/removed-sources.md` (with GitHub archive-zip re-download links) first, then update
index.md + per-repo pages + `sources:` frontmatter together so no page points at a deleted file. Full
procedure + decision table: `references/pruning-repos.md`.

## How to regenerate / extend
- Run via a FRESH interpreter: `python3 scripts/build_modules.py` from the wiki dir. See gotcha #3.
- To add a NEW version: (1) drop its inventory `.md` in raw/articles/ named `opencv-modules-<patch>.md`
  with `[desc](url)` links per entry; (2) add a `<major>x` entry to the `VERSIONS` dict in the
  generator (+ `CONFIDENCE`, and any new module names in `PRIMARY_TAG`/`RELATED`/`ENRICH`). The rest is automatic.
- After edits, re-run generator then run the graph lint (broken links / orphans / min-outbound) —
  see below. Generator clears entities/ + version-*.md first, so it is safe to re-run.

## Graph lint (run after every generation)
Fresh interpreter: scan all `.md`, resolving each `[[link]]` to `<link>.md` **by basename anywhere**
in the vault — links are bare names (`[[core-4x]]`), so match on `os.path.basename(path)[:-3]`, NOT
the relative path. Storing a relative-path key makes every link look broken (hundreds of false
positives). Expect **0 real broken, 0 orphans, every content page >=2 outbound wikilinks and
reachable from index.md**. SCHEMA.md prose mentions of `[[wikilinks]]` inside backticks are false
positives — skip them. Watch: `index.md` exists at root AND in subdirs (e.g. `resources/`), so
basenames are NOT unique keys when keying a scan by name; count pages with path-based filters, not
by basename.

## Gotchas (learned the hard way)
1. **Inventory files MUST contain `[desc](url)` links.** Bare `name. desc` (no link) → parser
   matches nothing → 0 entity pages. Keep real provenance URLs in raw/.
2. **sha256 is over the body AFTER frontmatter only.** Split on bare `---`, take parts[2:].
   Splitting on `\n---` fails (file starts with `---` at offset 0 → empty hash).
3. **execute_code kernel caches stale module imports.** The persistent kernel re-imports an old
   `build_modules` from a prior cell → wrong behavior, no traceback change. Run the generator via
   `terminal`/fresh `python3 script.py`, or use `reset=True`. Direct `import build_modules` in the
   kernel is unreliable.
4. **Cross-link membership uses BARE module names, not `<mod>-<ver>`.** Test `r in valid_names`,
   NOT `f"{r}-{ver}" in valid_names` (off-by-version-suffix bug → empty links everywhere).
5. **Cross-links must be version-aware.** Only link siblings that exist in THAT version: gapi absent
   from 3.x; calib3d splits into geometry/calib/stereo/ptcloud in 5.x (features2d→features);
   aruco removed in 5.x. Generator filters RELATED by `r in valid_names` per version.
6. **Fetching docs.opencv.org:** direct urllib from the agent VM gets 403 rate-limited; use
   `web_extract`. The `/5.x/` index renders its module list JS-only — fetch split pages at the
   correct prefix: `https://docs.opencv.org/5.0/main_modules/api_root.html` and
   `.../extra_modules/api_root.html` (base path is `/5.0/`, not `/5.x/`). 4.x=`/4.12.0/`, 3.x=`/3.4.20/`.
7. **5.x confidence = medium** (brand-new release; cv2 paths for split/rename modules may still be
   stabilizing). Stable lines (4.x, 3.x) = high. Set via the `CONFIDENCE` map.
8. **GitHub API rate limits bite bulk repo work.** Unauthenticated core = 60 req/hr; search API ~15/min.
   To enumerate a user's topic repos use the *search* endpoint (`/search/repositories?q=user:<name>+<term>`,
   `total_count` gives the real count regardless of pagination). Once core is exhausted, keep fetching repo
   **content** via `raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>` — that is static CDN, NOT the
   API, so it is unlimited and does not touch the rate limit. Reserve the few remaining core calls for
   discovery (file trees via `/repos/o/r/contents/`). Branch is usually `main` or `master`; try both.

## Current state (as of 2026-10-30)
3 versions: 4.x (74 entities), 3.x (62), 5.x (76) = 212 entity pages + 3 landing pages, plus
8 hand-written cross-cutting pages: concepts/ (color-conversion, image-filtering,
thresholding-and-morphology, feature-descriptors, camera-calibration-pipeline) and
comparisons/ (face-detectors, object-detection-methods, stereo-matching). Vault = 232 .md files;
index.md "Total pages" = 229. Graph lint passes: 0 real broken links; every content page has >=2
outbound wikilinks and is reachable via index.md.

External sources ingested (raw/papers/ + resources/, 6 pages): opencv-curriculum-fundamentals,
opencv-curriculum-c0, opencv-python-docs, nus-cs4243-opencv (⚠️ legacy v2.1 C-API), and
learning-opencv-2nd-edition. resources/index.md also records sources that could NOT be retrieved
(Learning-OpenCV-3 PDF via raw.githubusercontent, HF dataset gokul9/opencvbooks [401 gated], the
two dead Chinese-book links, scispace [403]).

Optional remaining layers: more comparisons (image interpolation, denoise methods,
Warp/geometric transforms), a queries/ deep-dive set, or per-function API reference if desired.
