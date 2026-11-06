# Extracting Legacy-CJK Text Layers (No /ToUnicode)

Some Chinese PDFs (common from gongkong / 超星-style distributors) embed a **real text layer** using standard Adobe CJK font encodings such as `/Encoding /GBK-EUC-H` (H = horizontal, V = vertical) but ship **no `/ToUnicode` map**. pymupdf, pdfminer.six, pdftotext, and Ghostscript all return zero characters because they cannot map the 2-byte glyph codes to Unicode. Browsers (Edge/Chrome) render them via the built-in CJK code table — which is why a user can select-and-copy Simplified Chinese even though no standard tool extracts it.

The raw bytes inside the text strings ARE the GBK/EUC code units, so decoding with Python's `gbk` / `gb18030` codec recovers the characters.

## Recipe

```python
import re, zlib

def unesc(s):
    return s.replace(b'\\\\', b'\\').replace(b'\\(', b'(').replace(b'\\)', b')')

raw = open(path, 'rb').read()
blocks = []
for m in re.finditer(rb'stream\r?\n(.*?)endstream', raw, re.S):
    try:
        dec = zlib.decompress(m.group(1))   # FlateDecode content streams only
    except Exception:
        continue                              # DCT(JPEG)/CCITT image streams raise -> not text
    for blk in re.findall(rb'BT.*?ET', dec, re.S):
        parts = []
        for s in re.finditer(rb'\((?:[^()\\]|\\.)*\)', blk):   # literal ( ... ) strings
            parts.append(unesc(s.group(0)[1:-1]))
        for h in re.finditer(rb'<([0-9A-Fa-f]+)>', blk):        # hex <...> strings (TJ arrays)
            hh = h.group(1)
            if len(hh) % 2: hh = hh[:-1]
            parts.append(bytes.fromhex(hh.decode()))
        blob = b''.join(parts)
        try:
            blocks.append(blob.decode('gbk'))
        except Exception:
            pass

text = '\n'.join(b for b in blocks if any('\u4e00' <= c <= '\u9fff' for c in b))
```

## Caveats / pitfalls

- **Only FlateDecode streams carry text.** DCTDecode (JPEG) and CCITTFaxDecode (Group 4) are image encodings — zlib raises on them, so skip. A page whose content stream is only an image `Do` operator has no extractable text even if it looks like it should.
- **Decompress before counting operators.** Never scan raw PDF bytes for `BT`/`Tj`/`TJ` or `( ... )` strings: those ASCII byte sequences appear as false positives inside FlateDecode-compressed binary. Decompress first, then parse `dec`.
- **Keep 2-byte alignment — decode per block.** Decode each block's bytes as one unit; a stray odd-length or non-text byte desyncs every following GBK pair into mojibake. Concatenating all blocks then decoding once is the common failure mode.
- **Page ordering.** `BT.*?ET` scans the whole decompressed stream. For correct per-page output, map content streams to pages via `/Contents` in the xref rather than scanning the entire file and hoping order is preserved.
- **This is an alternative for one PDF subtype**, not a general replacement for pymupdf/marker. If the font *does* have a `/ToUnicode`, use the normal extractor — faster and more accurate.
