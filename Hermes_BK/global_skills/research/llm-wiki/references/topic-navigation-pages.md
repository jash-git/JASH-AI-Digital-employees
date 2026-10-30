# Topic Navigation Pages

Reusable technique for wikis whose corpus has a **core statute + many companion rules** structure
(acts + regulations, codes + implementing orders, statutes + agency rules). Only needed when the
corpus is large enough that leaf pages are unfindable in `index.md`; the general procedure lives in
SKILL.md.

## The problem it solves
A bulk ingest creates one page per entity (one law, one regulation). For a domain with 1 core act and
hundreds of companion rules, every rule becomes an orphan-ish leaf: `index.md` lists them all but no
reader has the patience to scan hundreds of entries to find the rule for their question. The rules are
also not grouped by what they actually regulate.

## The pattern
Build a small set of **topic navigation pages** — one per high-frequency regulatory domain — that each:
1. Open with a short **hand-written scope note**: what the domain covers and which core act(s) anchor it.
2. Link the **core statute(s)** by full name (the authoritative text lives on its own entity page).
3. List every **companion rule** grouped by sub-agency / functional category, current-only, with a
   count of how many are repealed and set aside.
4. Cross-link sibling topic pages, the domain overview, and `index.md` at the foot.

Each entry is a wikilink to the rule's entity page so a reader drills from the curated list straight to
the full text. The hand-written scope note + core-law links are what make it a synthesis worth keeping;
the grouped rule list is generated programmatically (see below).

## Why this shape
- A future query like "bank capital adequacy rules" lands on one page that already lists every relevant
  rule, instead of the agent rescanning hundreds of commands. This is the compounding payoff.
- Grouping by sub-agency/category mirrors how a domain expert thinks and how the source corpus is
  organized, so the list is scannable rather than alphabetical noise.
- Current-only with a repealed count keeps the page lean; repealed rules stay findable via `index.md`.

## Generating the rule list programmatically
Keep the topic set declarative (a `TOPIC_PAGES` list of `{name, summary}`) so both the generator and
`index.md` read from one source. For each topic:
- Filter companion rules to those whose category breadcrumb's first segment(s) fall in the domain.
- Re-split on the corpus's real separator before coding (see `references/taiwan-law-moj-dataset.md`
  for the MOJ full-width `＞` quirk — splitting on the wrong char collapses grouping).
- Group by the next breadcrumb segment (sub-agency / functional category) and emit one `###` header
  per group with a count, then the wikilinks.
- Emit current rules only; note the repealed count in an italic line above the list.

## When to stop adding topics
Add a topic page only for domains that are genuinely high-frequency (the user will actually query them)
and have enough companion rules to be unfindable on their own. Do not make one per minor sub-domain —
that just moves the scan problem from `index.md` into N topic pages.
