#!/usr/bin/env python3
"""Parse an XWD file and write PNG, without ImageMagick.

XWD is the native format of `xwd`. This header parser is deliberately tolerant:
different xwd writers place width/height/bytesPerLine at slightly different
offsets and may use big- or little-endian encoding. We auto-detect by scanning
candidate offsets for a self-consistent set (width, height, bytesPerLine) where
``filesize - bytesPerLine*height`` is a small positive header offset.

Usage:
    python3 assets/xwd_to_png.py <input.xwd> [output.png]

Handles 24-bit and 32-bit ZPixmap windows (the common cases for Xwayland).
"""
import struct
import sys

from PIL import Image


def _u(data, off, endian):
    return struct.unpack(endian + "I", data[off:off + 4])[0]


def find_layout(data):
    """Return (width, height, bytes_per_line, obf, depth) or None."""
    n = len(data)
    for endian in ("<", ">"):
        # Candidate offsets for width/height. Most writers put them at 16/20;
        # some use 4/8. Try a few common positions.
        for w_off, h_off in ((16, 20), (4, 8)):
            width = _u(data, w_off, endian)
            height = _u(data, h_off, endian)
            if not (1 < width < 100000 and 1 < height < 100000):
                continue
            # Scan plausible bytesPerLine offsets; pick the one that yields a
            # small positive pixel-data offset.
            for bpl_off in range(24, 64, 4):
                if bpl_off == w_off or bpl_off == h_off:
                    continue
                bpl = _u(data, bpl_off, endian)
                if bpl < width * 2 or bpl > width * 8 + 16:
                    continue
                obf = n - bpl * height
                if 0 < obf < max(4096, n // 4):
                    depth = round(bpl * 8 / width) if width else 0
                    return width, height, bpl, obf, depth
    return None


def to_png(data, layout, out_path):
    width, height, bpl, obf, depth = layout
    raw = data[obf:]

    if depth == 24:
        # Bottom-up, BGR. Flip vertically then reinterpret as RGB.
        img = Image.frombytes("RGB", (width, height), raw[::-1], "raw", "BGR")
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    elif depth == 32:
        # Bottom-up, BGRA.
        img = Image.frombytes("RGBA", (width, height), raw[::-1], "raw", "BGRA")
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    else:
        raise ValueError(
            "Unsupported depth %d; only 24/32-bit ZPixmap handled" % depth
        )

    img.save(out_path)
    print("SAVED", out_path, img.size, "depth=%d" % depth)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/xwd_out.png"

    data = open(path, "rb").read()
    layout = find_layout(data)
    if not layout:
        print("Could not parse XWD header from", path)
        sys.exit(1)
    to_png(data, layout, out)


if __name__ == "__main__":
    main()
