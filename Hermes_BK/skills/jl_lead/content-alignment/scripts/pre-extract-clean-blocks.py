#!/usr/bin/env python3
"""Pre-extract clean HTML blocks from a single-line reference file for verbatim migration.

Problem this solves (class-level, recurring in content-alignment tasks):
When migrating article/tool HTML verbatim from a reference source into target pages,
sub-agents commonly use `ref.find('id="X"')` .. `ref.find('id="Y"')` as extraction
boundaries. But when the reference file's content is almost entirely on ONE line, the
next section's id often sits INSIDE the next opening tag (e.g. `<h3 id="asszx">`,
`<hr><h2 id="szwmpppbzxj">`). Slicing at that id leaves a DANGLING partial tag
(`<hr><h2 `, `<h3 `) at the block end -> HTML defect in the target page.

Fix: extract up to (but not including) the NEXT section's FULL opening h-tag, searching
only AFTER the current anchor's own closing '>'. Result blocks have clean endings.

Usage:
  python pre-extract-clean-blocks.py <reference.html> <out_dir>/ [anchor:start next_tag] ...

Example:
  python pre-extract-clean-blocks.py docs/reference-ziwei-original.html docs/extracted \
      M6 '<h3 id="asszx">' '<h3' \
      M7 '<h2 id="smpjdyd"' '<h2' \
      M8 '<h2 id="cjwtjd"' '<h2'
  # last block (M9) may omit next_tag to run to </article> or EOF.
"""
import re
import sys
from pathlib import Path


def extract(ref: str, start_anchor: str, next_h_tag: str | None = None):
    s = ref.find(start_anchor)
    if s < 0:
        raise ValueError(f"start anchor not found: {start_anchor!r}")
    gt = ref.find('>', s)          # end of current opening tag (search starts AFTER this)
    if gt < 0:
        raise ValueError(f"no closing '>' for anchor: {start_anchor!r}")
    if next_h_tag:
        m = re.search(next_h_tag, ref[gt + 1:])
        e = gt + 1 + m.start() if m else len(ref)
    else:
        # run to </article> if present, else EOF
        art = ref.find('</article>', gt)
        e = (art if art >= 0 else len(ref))
    return ref[s:e]


def main():
    args = sys.argv[1:]
    ref_path = Path(args[0])
    out_dir = Path(args[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    rest = args[2:]

    ref = ref_path.read_text(encoding="utf-8")

    written = []
    for i in range(0, len(rest), 3):
        name, anchor, tag = rest[i], rest[i + 1], rest[i + 2]
        block = extract(ref, anchor, None if tag == "EOF" else tag)
        # sanity: no dangling partial h-tag at the end
        stripped = block.rstrip()
        dangling = stripped.endswith(("<h2 ", "<h3 "))
        out_path = out_dir / f"{name}.html"
        out_path.write_text(block, encoding="utf-8")
        written.append((name, len(block), dangling))

    for name, length, dangling in written:
        flag = "DANGLING!" if dangling else "ok"
        print(f"[{flag}] {name}.html  ({length} chars)")


if __name__ == "__main__":
    main()
