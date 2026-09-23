# TOC Integrity Audit — Detecting Dead Anchors & Truncated Body

Session-specific detail for auditing an **existing** `data.js` article array (the reverse of ingestion) after a content-migration step. Use when the user reports "TOC lists a chapter that doesn't exist in the body" / dead anchors / truncated articles.

## The failure class

The renderer (`detail.js`) builds two INDEPENDENT arrays from each entry:
- `toc[]` → TOC nav links, anchor = `#sec-{encoded heading text}`
- `body[]` with `type==='h2'` → actual `<h2>` anchors rendered in the article

If `toc` and `body-h2` disagree, clicking a TOC link jumps to a non-existent `#sec-...` anchor (dead anchor — page stays put, no error). This is a **data-quality problem**, not a code bug.

## Root cause pattern (this project)

When porting articles from the source site into `data.js`, the `body[]` array was sometimes written with only the FIRST h2 block; subsequent chapters were dropped. Result: `toc` has 2-3 entries but `body` has only 1 h2 → every TOC entry after the first is dead.

## Detection script (Node, no deps)

```js
// scripts/toc-audit.js — run from project root
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync('src/public/js/blog/data.js', 'utf-8');
const ctx = { window: {} };
new vm.Script(code).runInNewContext(ctx);
const BLOG = ctx.BLOG;

function h2s(entry) {
  return (entry.body || []).filter(b => b.type === 'h2').map(b => b.text);
}
for (const a of BLOG) {
  const toc = a.toc || [];
  const bodyH2 = h2s(a);
  // dead anchors: TOC entries with no matching h2 in body
  const missing = toc.filter(t => !bodyH2.includes(t));
  if (missing.length) console.log(`DEAD ANCHOR id=${a.id} (${a.title})\n  toc: ${JSON.stringify(toc)}\n  body-h2: ${JSON.stringify(bodyH2)}\n  missing: ${JSON.stringify(missing)}`);
}
```

Run with `node scripts/toc-audit.js`. It prints every entry whose TOC has entries absent from the rendered body.

## Broader audit dimensions (run together)

Don't only check TOC. For each article also verify:
1. **excerpt** non-empty
2. **img** present (renderer resolves `img/` + a.img — double-slash bug if a.img starts with `/`)
3. **body length**: an entry that has h2s but where body is suspiciously short (only 1 block) while toc lists many chapters → truncated content
4. **TOC vs body-h2** consistency (dead anchors above)

## Fix directions (choose with the user — do NOT guess)

- **A. Restore from source**: if the original article still exists on the source site / archive, re-fetch and rebuild `body[]`. Best outcome.
- **B. Neutralize dead anchors** (fastest, safe): trim `toc` to match existing `body-h2`, or repoint extra TOC entries to real sections. Fixes the broken-click UX without fabricating content.
- **C. Expand content**: write missing chapters. ⚠️ For domain-heavy sites (命理/medical/legal), NEVER fabricate — this produces misinformation. Only do C if you have authoritative source material.

## Verification after fix

1. `node scripts/toc-audit.js` → zero DEAD ANCHOR lines.
2. `node -c src/public/js/blog/data.js` (valid JS).
3. Deploy: `sudo cp` to test path, md5-compare src vs deployed copy.
4. Headless Chrome: load an article page, click each TOC link, assert the URL fragment resolves to a real `<h2>` anchor — not just that the file loaded.

## Key lesson

"Source code correct ≠ deployed ≠ browser-usable." A grep of `src/` cannot detect (a) a developer who forgot to deploy, or (b) a double-slash path bug. Always md5-compare src vs deployed AND render in headless Chrome before marking DONE.
