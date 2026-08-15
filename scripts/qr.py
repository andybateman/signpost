#!/usr/bin/env python3
"""
Minimal QR encoder — byte mode, error correction level M, versions 1-10.

Written rather than pulled in because every other script here is stdlib-only,
and a build that needs `pip install` before it will run is a build that stops
working the first time someone comes back to it on a clean machine. Scope is
deliberately narrow: the careers board encodes job URLs of 40-90 characters,
which version 10 covers three times over.

Output is the module matrix as a list of '0'/'1' row strings, ready to be
embedded in the vacancy data and drawn as SVG rectangles by the board.

scripts/test_qr.py checks the output by reading it back with an independent
decoder, which is the only test worth having here.
"""

# ── GF(256) arithmetic, primitive polynomial 0x11D ────────────────────────
EXP = [0] * 512
LOG = [0] * 256
_x = 1
for _i in range(255):
    EXP[_i] = _x
    LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    EXP[_i] = EXP[_i - 255]


def _mul(a, b):
    if a == 0 or b == 0:
        return 0
    return EXP[LOG[a] + LOG[b]]


def _generator(nsym):
    """Generator polynomial for nsym error correction codewords."""
    poly = [1]
    for i in range(nsym):
        poly = _poly_mul(poly, [1, EXP[i]])
    return poly


def _poly_mul(p, q):
    out = [0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            out[i + j] ^= _mul(a, b)
    return out


def _ec_codewords(data, nsym):
    """Reed-Solomon remainder for one block."""
    gen = _generator(nsym)
    rem = list(data) + [0] * nsym
    for i in range(len(data)):
        coef = rem[i]
        if coef:
            for j, g in enumerate(gen):
                rem[i + j] ^= _mul(g, coef)
    return rem[len(data):]


# ── Version tables, error correction level M ──────────────────────────────
# version: (ec codewords per block, [(block count, data codewords), ...])
VERSIONS = {
    1:  (10, [(1, 16)]),
    2:  (16, [(1, 28)]),
    3:  (26, [(1, 44)]),
    4:  (18, [(2, 32)]),
    5:  (24, [(2, 43)]),
    6:  (16, [(4, 27)]),
    7:  (18, [(4, 31)]),
    8:  (22, [(2, 38), (2, 39)]),
    9:  (22, [(3, 36), (2, 37)]),
    10: (26, [(4, 43), (1, 44)]),
}

# Centre coordinates of the alignment patterns, by version.
ALIGNMENT = {
    1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30],
    6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50],
}

EC_LEVEL_BITS = 0b00  # level M


def _data_capacity(version):
    return sum(count * data for count, data in VERSIONS[version][1])


def _pick_version(length):
    """Smallest version whose data capacity fits length bytes in byte mode."""
    for version in sorted(VERSIONS):
        count_bits = 8 if version < 10 else 16
        needed = 4 + count_bits + 8 * length
        if needed <= _data_capacity(version) * 8:
            return version
    raise ValueError(f"{length} bytes is beyond version 10 at EC level M")


def _bitstream(data, version):
    """Mode indicator, character count, payload, terminator and padding."""
    count_bits = 8 if version < 10 else 16
    bits = "0100" + format(len(data), f"0{count_bits}b")
    bits += "".join(format(b, "08b") for b in data)

    capacity = _data_capacity(version) * 8
    bits += "0" * min(4, capacity - len(bits))           # terminator
    bits += "0" * (-len(bits) % 8)                        # pad to a byte

    codewords = [int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)]
    for i in range(_data_capacity(version) - len(codewords)):
        codewords.append(0xEC if i % 2 == 0 else 0x11)    # alternating pad
    return codewords


def _interleave(codewords, version):
    """Split into blocks, add error correction, and interleave both."""
    nsym, groups = VERSIONS[version]

    blocks, pos = [], 0
    for count, size in groups:
        for _ in range(count):
            blocks.append(codewords[pos:pos + size])
            pos += size

    ec_blocks = [_ec_codewords(b, nsym) for b in blocks]

    out = []
    for i in range(max(len(b) for b in blocks)):
        for b in blocks:
            if i < len(b):
                out.append(b[i])
    for i in range(nsym):
        for b in ec_blocks:
            out.append(b[i])
    return out


# ── Matrix ────────────────────────────────────────────────────────────────
def _blank(size):
    return [[None] * size for _ in range(size)]


def _place_function_patterns(m, version):
    size = len(m)

    def finder(top, left):
        for r in range(-1, 8):
            for c in range(-1, 8):
                y, x = top + r, left + c
                if 0 <= y < size and 0 <= x < size:
                    edge = r in (0, 6) and 0 <= c <= 6
                    side = c in (0, 6) and 0 <= r <= 6
                    core = 2 <= r <= 4 and 2 <= c <= 4
                    m[y][x] = 1 if (edge or side or core) else 0

    finder(0, 0)
    finder(0, size - 7)
    finder(size - 7, 0)

    for i in range(8, size - 8):                          # timing patterns
        bit = 1 if i % 2 == 0 else 0
        m[6][i] = bit
        m[i][6] = bit

    centres = ALIGNMENT[version]
    for r in centres:
        for c in centres:
            # the three finder corners have no alignment pattern
            if (r, c) in ((6, 6), (6, size - 7), (size - 7, 6)):
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    ring = max(abs(dr), abs(dc))
                    m[r + dr][c + dc] = 1 if ring != 1 else 0

    m[size - 8][8] = 1                                     # dark module


def _reserve(m, version):
    """Mark the format and version areas so data placement skips them."""
    size = len(m)
    for i in range(9):
        if m[8][i] is None:
            m[8][i] = 0
        if m[i][8] is None:
            m[i][8] = 0
    for i in range(8):
        if m[8][size - 1 - i] is None:
            m[8][size - 1 - i] = 0
        if m[size - 1 - i][8] is None:
            m[size - 1 - i][8] = 0
    if version >= 7:
        for i in range(6):
            for j in range(3):
                m[size - 11 + j][i] = 0
                m[i][size - 11 + j] = 0


def _place_data(m, bits, reserved):
    size = len(m)
    idx = 0
    col = size - 1
    upward = True
    while col > 0:
        if col == 6:      # the vertical timing pattern is not a data column
            col -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for row in rows:
            for c in (col, col - 1):
                if not reserved[row][c]:
                    m[row][c] = int(bits[idx]) if idx < len(bits) else 0
                    idx += 1
        upward = not upward
        col -= 2


MASKS = [
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]

_FINDER_RUN = [1, 0, 1, 1, 1, 0, 1]


def _penalty(m):
    size = len(m)
    score = 0

    lines = [row[:] for row in m] + [[m[r][c] for r in range(size)] for c in range(size)]

    for line in lines:
        run, last = 0, None
        for value in line:
            if value == last:
                run += 1
            else:
                if run >= 5:
                    score += 3 + (run - 5)
                run, last = 1, value
        if run >= 5:
            score += 3 + (run - 5)

        # 1:1:3:1:1 finder-like pattern with four light modules either side
        for i in range(len(line) - 6):
            if line[i:i + 7] == _FINDER_RUN:
                before = line[max(0, i - 4):i]
                after = line[i + 7:i + 11]
                if (len(before) == 4 and sum(before) == 0) or \
                   (len(after) == 4 and sum(after) == 0):
                    score += 40

    for r in range(size - 1):
        for c in range(size - 1):
            block = (m[r][c], m[r][c + 1], m[r + 1][c], m[r + 1][c + 1])
            if len(set(block)) == 1:
                score += 3

    dark = sum(sum(row) for row in m)
    percent = dark * 100 / (size * size)
    score += 10 * (int(abs(percent - 50) / 5))
    return score


def _bch(value, generator, bits):
    """BCH remainder used by both the format and version information."""
    rem = value
    while rem.bit_length() - 1 >= bits:
        rem ^= generator << (rem.bit_length() - generator.bit_length())
    return rem


def _format_bits(mask):
    data = (EC_LEVEL_BITS << 3) | mask
    rem = _bch(data << 10, 0b10100110111, 10)
    return format(((data << 10) | rem) ^ 0b101010000010010, "015b")


def _version_bits(version):
    rem = _bch(version << 12, 0b1111100100101, 12)
    return format((version << 12) | rem, "018b")


def _place_format(m, mask):
    size = len(m)
    # bits[0] is the most significant of the 15; the spec places them in that
    # order, starting at (8,0) and again from the bottom-left corner upward.
    bits = [int(x) for x in _format_bits(mask)]

    for i in range(6):
        m[8][i] = bits[i]
    m[8][7] = bits[6]
    m[8][8] = bits[7]
    m[7][8] = bits[8]
    for i in range(9, 15):
        m[14 - i][8] = bits[i]

    # second copy: 7 modules up the left column, 8 along the top-right row.
    # The module below them at (size-8, 8) is the fixed dark module.
    for i in range(7):
        m[size - 1 - i][8] = bits[i]
    for i in range(7, 15):
        m[8][size - 15 + i] = bits[i]


def _place_version(m, version):
    if version < 7:
        return
    size = len(m)
    bits = [int(x) for x in _version_bits(version)][::-1]
    for i in range(18):
        r, c = i // 3, i % 3
        m[size - 11 + c][r] = bits[i]
        m[r][size - 11 + c] = bits[i]


def encode(text):
    """Encode text as a QR symbol. Returns rows of '0'/'1' strings."""
    data = text.encode("utf-8")
    version = _pick_version(len(data))
    size = version * 4 + 17

    codewords = _interleave(_bitstream(data, version), version)
    bits = "".join(format(cw, "08b") for cw in codewords)
    # remainder bits: versions 2-6 need 7, 7-13 need 0 (14+ is out of scope)
    bits += "0" * (7 if 2 <= version <= 6 else 0)

    base = _blank(size)
    _place_function_patterns(base, version)
    _reserve(base, version)
    reserved = [[cell is not None for cell in row] for row in base]

    best, best_score = None, None
    for mask in range(8):
        m = [row[:] for row in base]
        _place_data(m, bits, reserved)
        for r in range(size):
            for c in range(size):
                if not reserved[r][c] and MASKS[mask](r, c):
                    m[r][c] ^= 1
        _place_format(m, mask)
        _place_version(m, version)
        score = _penalty(m)
        if best_score is None or score < best_score:
            best, best_score = m, score

    return ["".join(str(cell) for cell in row) for row in best]


if __name__ == "__main__":
    import sys
    for row in encode(sys.argv[1] if len(sys.argv) > 1 else "https://example.com"):
        print(row.replace("1", "██").replace("0", "  "))
