# Pruning Stored Reference Material (raw/repos/ + raw/papers/)

Reference archives in `raw/` are **not** wiki content. Resource pages describe each source but never
inline-reproduce it, so these zips are local copies that can be reclaimed when they bloat. Repo zips
especially grow unbounded: they bundle prebuilt binaries, installers, videos, model weights, and fonts
that neither belong in the wiki nor can be ingested into a resource page.

## Decision order
1. Quantify each zip's *inside* composition before touching anything (bucketing below). The compressed
   size on disk is what you reclaim; the inside composition drives keep/trim/delete.
2. Classify each source into one tier:
   - **DELETE** — near-pure bloat (prebuilt binaries, installers, download bundles) or a legacy-API
     repo whose real content is tiny and superseded. Reclaim fully.
   - **TRIM** — real code/docs buried under re-downloadable media/weights/fonts/installers. Remove only
     the bloat; keep everything needed to run/read the examples.
   - **KEEP** — unique complementary content (a course, a book, runnable examples) with no equivalent
     in docs.opencv.org. Leave untouched.
3. For every DELETE/TRIM, write the removal log + re-download link BEFORE deleting (see below).
4. Delete/trim, then update provenance atomically: index.md table + per-repo pages + `sources:` front.

## Bucket the inside composition
`unzip -l <zip>` lists entries; sum bytes per extension to see what you would actually lose:
```
unzip -l <zip> | awk 'NR>4{print $NF}' | sed -E 's#.*/##' \
  | grep -oE '\.[a-zA-Z0-9]+$' | sort | uniq -c | sort -rn
```
Bloat (re-downloadable, not ingestible): prebuilt binaries (.dll/.exe/.a/.o/.so/.lib), installer
bundles (.msi/.exe installers, nested .zip/.rar under tool/), video/media (.mp4/.avi/.flv/.gif),
model weights (.caffemodel/.onnx/.pt/.pth/.hdf5/.npz/.bin), large fonts (.ttf/.ttc).
Real content: source code (.py/.cpp/.hpp/.h/.cc) and docs/config (.md/.txt/.xml/.html/.json).

## The over-trim rule (read before trimming)
Cut only bloat that is re-downloadable and cannot be ingested; keep all source, docs, AND the test
images/data the examples load. Trimming dozens of tiny asset files for marginal space breaks example
reproducibility while saving almost nothing — measure reclaimed bytes per category first, and remove
the heavy categories (videos, weights, fonts, installers), not the small images that keep a tutorial
runnable.

## Removal log (required before deleting)
Write `raw/repos/removed-sources.md` listing each DELETE/TRIM with: repo name, original size, why it
was removed, and the GitHub **archive-zip** URL to re-fetch. The archive form is
`https://github.com/<owner>/<repo>/archive/refs/<branch>.zip` — never a `blob/` URL, which returns HTML
for large files instead of the file. For TRIMs, record the new code-only filename and what was cut.
This log is the only recovery path once the zip is gone.

## Provenance update (do all three together)
- `resources/index.md` table: mark deleted rows "ZIP REMOVED" and trimmed rows "TRIMMED / code-only",
  each pointing at removed-sources.md.
- Each per-repo resource page: add a REMOVED/TRIMMED callout + re-download link near the top.
- The page's `sources:` frontmatter must point at something that still exists (the new trimmed zip, or
  removed-sources.md for deleted ones) — never a path to a file you just deleted.
