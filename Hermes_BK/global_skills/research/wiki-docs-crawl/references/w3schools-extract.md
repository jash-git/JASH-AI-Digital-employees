# W3Schools Extraction via web_extract

When your VM IP is throttled by w3schools.com, `web_extract` (tool-backend egress) fetches pages that curl/requests from the VM cannot. It returns cleaned Markdown but with quirks; post-process before writing to `raw/articles/w3schools-js/`.

## Output shape
- Full-page Markdown in document order: nav block first (`# Get Certified`, `## JS Tutorial`, link rows, `...`), then the article, then prev/next + footer (`[❮ Previous]…`, `Share Link Copied`, `## Track your progress`).
- Code is NOT fenced and intro prose is often glued to it with no blank line (e.g. `### Example\nThis example uses...\nswitch (...) {`).
- Reference pages (e.g. `js_array_reference.asp`) have no "Try it Yourself" and start with nav like `# References ## W3SCHOOLS REFERENCES`.

## Locate the article
1. If a line contains `Try it Yourself`: walk back from its index to the nearest heading (`^#{1,4}\s`) — that's the title; start there.
2. Else (reference pages): take the first H1/H2 after skipping nav headers (`# Get Certified`, `## JS Tutorial`, `## References`).
3. End at the last `[❮ Previous` line or before `## Track your progress`.

## Fence code blocks
Group into paragraphs (blank-line separated) and classify each:
- A paragraph immediately following a `### Example` / `### Syntax` header is code; one after `### Output` is text.
- Otherwise wrap as ```javascript only if it has ≥2 lines, no line starts with `-`, `*`, `#`, `[` (link), or `\d+.`, and the joined text contains JS tokens (`{`, `}`, `;`, `function`, `=>`, `let/const/var`).
- Split a glued intro sentence from code: if a pending code line is followed by a prose line ending in `:` or `.`, close the fence before it.

## Operational notes
- Keep web_extract calls ≤~20–28 per execute_code cell (5-minute timeout kills mid-loop); save each file immediately and resume from files on disk.
- Set char_limit ≥ 40000; some pages (e.g. Temporal) exceed smaller budgets.
- Build the final file as `frontmatter + "\n\n" + body_no_trailing_newline + "\n"` and sha256 the body WITHOUT its trailing newline, matching wiki_ingest_validate.py.
