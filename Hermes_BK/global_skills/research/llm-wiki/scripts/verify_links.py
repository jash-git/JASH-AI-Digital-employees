#!/usr/bin/env python3
"""Audit wikilinks across an llm-wiki vault.

Scans the wiki's page directories for .md files, resolves every [[slug]] against
filenames (without extension) found anywhere in those dirs, and reports broken
links plus any page with fewer than --min-outbound outbound links.

Usage:
    python scripts/verify_links.py [WIKI_PATH]      # default: $WIKI_PATH or ~/wiki

Exit code is non-zero when broken links are found, so it doubles as a lint gate.
Run this rather than hand-counting links before reporting an ingest done.
"""
import os, re, sys, argparse

DEFAULT_DIRS = ("entities", "concepts", "comparisons", "queries")


def collect_pages(root, dirs):
    pages = []
    for d in dirs:
        base = os.path.join(root, d)
        if not os.path.isdir(base):
            continue
        for fn in os.listdir(base):
            if fn.endswith(".md"):
                pages.append(os.path.join(base, fn))
    return pages


def valid_slugs(pages):
    """Every resolvable slug = a page filename without .md (also slug/index.md -> slug)."""
    slugs = set()
    for p in pages:
        base = os.path.basename(p)[:-3]
        if base.endswith("/index"):
            base = base[:-6]
        slugs.add(base)
    return slugs


def outbound(txt):
    return [s.strip() for s in re.findall(r"\[\[([^\]]+)\]\]", txt)]


def main():
    ap = argparse.ArgumentParser(description="llm-wiki wikilink audit")
    ap.add_argument("path", nargs="?", default=os.environ.get("WIKI_PATH", os.path.expanduser("~/wiki")))
    ap.add_argument("--dirs", default=",".join(DEFAULT_DIRS))
    ap.add_argument("--min-outbound", type=int, default=2)
    args = ap.parse_args()

    dirs = [d for d in args.dirs.split(",") if d]
    pages = collect_pages(args.path, dirs)
    slugs = valid_slugs(pages)

    broken, low = [], []
    for p in pages:
        with open(p, encoding="utf-8") as f:
            outs = set(outbound(f.read()))
        bad = [s for s in outs if s not in slugs]
        rel = os.path.relpath(p, args.path)
        if bad:
            broken.append((rel, sorted(bad)))
        if len(outs) < args.min_outbound:
            low.append((rel, len(outs)))

    print(f"Scanned {len(pages)} pages across {dirs}.")
    print("Broken wikilinks:", "NONE" if not broken else broken)
    print(f"Pages with <{args.min_outbound} outbound links:", "NONE" if not low else low)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
