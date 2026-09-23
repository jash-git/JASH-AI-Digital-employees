# graphify Pitfalls & Troubleshooting

## Installation

If `graphify` CLI is not found:
```bash
uv tool install --upgrade graphifyy -q
```
Verify with: `uv tool run --from graphifyy python -c "import graphify"`

## Corpus Size Warning

If detect returns `total_files > 500` OR `total_words > 2,000,000`, graphify will ask to narrow to a subfolder.
**Fix:** Pass the specific subdirectory path instead of `.` — e.g., `/graphify VPOS_Avalonia`.

## Subdirectory Detection

`detect()` scans the path you pass. If you pass the project root, it includes ALL subdirectories.
To analyze only a subfolder, call detect on that path:
```python
result = detect(Path('VPOS_Avalonia'))  # not detect(Path('.'))
```

## AST Extraction Timeout

AST extraction on large codebases (300+ files) can exceed the default 300s timeout.
**Fix:** Use `timeout=600` or higher in terminal calls.
If it times out, check if `.graphify_ast.json` was written. If not, re-run.
The cache prevents re-extraction on retry (only uncached files are processed).

## Shrink Guard (to_json Refusal)

`to_json()` refuses to overwrite `graph.json` when the new graph has fewer nodes than the existing one.
This commonly happens when:
- You previously ran on the full project root, then switch to a subdirectory
- An `--update` run produces fewer nodes due to file deletions or dedup

**Fix:** Delete the old `graph.json` before re-building:
```bash
rm -f graphify-out/graph.json
```
Then re-run Steps 4-5.

## Empty Semantic File for Code-Only Corpus

When a corpus has no docs/papers/images (code-only), you MUST write an empty semantic file:
```python
Path('graphify-out/.graphify_semantic.json').write_text(
    json.dumps({'nodes':[],'edges':[],'hyperedges':[],'input_tokens':0,'output_tokens':0}),
    encoding='utf-8'
)
```
Without this, Part C merge will hit `FileNotFoundError`.

## Zero-Node Files Warning

graphify may warn: "50 source file(s) produced zero nodes and are absent from the graph."
Common culprits: `.json`, `.sql`, `.js`, `.axaml` files that have no AST nodes for the supported languages.
This is informational — these files won't appear in the graph. No action needed unless they should have been extracted.
