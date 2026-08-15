#!/usr/bin/env python3
"""
Round-trip test for qr.py.

The encoder is hand-written, so "it renders something square" is not evidence.
This encodes a corpus spanning every supported version and reads each symbol
back with an independent decoder (OpenCV's QRCodeDetector), which is the test
that matters: a phone camera has to get the URL back out.

The decoder is a development dependency, not a project one -- nothing in the
build pipeline needs it. Install it in a scratch virtualenv:

    python3 -m venv /tmp/qrtest
    /tmp/qrtest/bin/pip install opencv-python-headless numpy
    /tmp/qrtest/bin/python scripts/test_qr.py
"""

import random
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qr  # noqa: E402

try:
    import cv2
    import numpy as np
except ImportError:
    print("skipped: needs opencv-python-headless and numpy (see the docstring)")
    sys.exit(0)


def to_image(rows, scale=10, quiet=6):
    """Render a matrix as a black-on-white image.

    The quiet zone is wider than the four modules the spec requires, and the
    scale generous: at 8 pixels per module with a bare 4-module margin the
    detector misses symbols that are perfectly valid -- including ones from
    the reference encoder -- and the test then measures OpenCV, not this file.
    """
    size = len(rows) + 2 * quiet
    img = np.ones((size, size), np.uint8) * 255
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            if cell == "1":
                img[r + quiet, c + quiet] = 0
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)


def corpus():
    """Job-URL-shaped strings at every length that changes version."""
    yield "A"
    yield "https://careers.sparknz.co.nz/careers/SearchJobs"
    yield "https://careers.sparknz.co.nz/careers/JobDetail/Finance-Analyst/65320"
    yield "https://careers.sparknz.co.nz/careers/JobDetail/Platforms-Engineer/63696"

    # Filler is varied rather than one repeated character on purpose: a long
    # run of the same byte makes a symbol that detectors struggle with -- the
    # reference encoder's output fails to scan on those too, so testing with
    # them measures the detector, not this encoder.
    rng = random.Random(20260815)
    alphabet = string.ascii_letters + string.digits + "-_/"
    filler = "".join(rng.choice(alphabet) for _ in range(240))

    base = "https://careers.sparknz.co.nz/careers/JobDetail/"
    for n in (1, 13, 14, 25, 26, 41, 42, 61, 62, 84, 85, 105, 106,
              121, 122, 150, 151, 180, 181, 213):
        yield ("https://x.co/" + filler)[:max(1, n)]
    for _ in range(40):
        yield base + filler[:rng.randint(1, 140)] + str(rng.randint(1000, 99999))


def main():
    detector = cv2.QRCodeDetector()
    seen_sizes, failures, total = set(), [], 0

    for text in corpus():
        total += 1
        rows = qr.encode(text)
        seen_sizes.add(len(rows))
        decoded, _, _ = detector.detectAndDecode(to_image(rows))
        if decoded != text:
            failures.append((len(text), len(rows), decoded[:40]))

    versions = sorted((size - 17) // 4 for size in seen_sizes)
    print(f"{total} symbols, versions {versions[0]}-{versions[-1]} "
          f"({len(versions)} distinct)")
    for length, size, got in failures:
        print(f"  FAIL len={length} size={size} decoded={got!r}")
    print("failures:", len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
