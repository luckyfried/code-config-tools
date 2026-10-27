"""Writes the studio environment the card lacquer reflects: site/vendor/env/studio.hdr.

A dim, warm room seen from the table, in the table's own axes (x to the right, y toward the
top of the screen, z up toward the camera), laid out the way Three.js reads an
equirectangular map. A flat card mirrors the dark ceiling, so its ink stays rich; a card
tilted a few degrees mirrors a softbox or a strip light and flashes with it. Standard
library only, and the same bytes on every run:

    python3 scripts/make_env.py
"""

import math
from pathlib import Path

W, H = 512, 256
OUT = Path(__file__).resolve().parents[1] / "site" / "vendor" / "env" / "studio.hdr"


def rgbe(r, g, b):
    top = max(r, g, b)
    if top < 1e-32:
        return bytes((0, 0, 0, 0))
    m, e = math.frexp(top)
    scale = m * 256.0 / top
    return bytes((int(r * scale), int(g * scale), int(b * scale), e + 128))


def soft(value, edge):
    """1 inside (value below zero), 0 outside, with a soft shoulder `edge` wide."""
    return max(0.0, min(1.0, 0.5 - value / edge))


def radiance(x, y, z):
    """Light arriving from the direction (x, y, z) in table axes; z is up off the felt."""
    r, g, b = (0.045, 0.036, 0.028) if z > -0.05 else (0.015, 0.013, 0.011)
    if z <= 0:
        return r, g, b
    # The softbox, up and toward the top of the table.
    k = soft(math.hypot(x / 1.5, y - 0.62) - 0.16, 0.06)
    r, g, b = r + 6.0 * k, g + 5.6 * k, b + 4.9 * k
    # A long strip behind the camera, low.
    k = soft(abs(y + 0.03) - 0.045, 0.02) * soft(abs(x) - 0.5, 0.06)
    r, g, b = r + 3.2 * k, g + 3.0 * k, b + 2.8 * k
    # Two side strips.
    for side in (-1, 1):
        k = soft(abs(x - side * 0.32) - 0.04, 0.02) * soft(abs(y - 0.25) - 0.5, 0.06)
        r, g, b = r + 2.4 * k, g + 2.3 * k, b + 2.1 * k
    # A cool panel low toward the bottom of the table, for the rim.
    k = soft(math.hypot(x, z - 0.2) - 0.25, 0.08) * (1 if y < -0.6 else 0)
    r, g, b = r + 0.8 * k, g + 1.0 * k, b + 1.4 * k
    return r, g, b


def main():
    rows = bytearray()
    for j in range(H):
        # Three.js maps the top row to +y of its sampling direction and the column to atan2(z, x).
        theta = (j + 0.5) / H * math.pi
        for i in range(W):
            phi = (i + 0.5) / W * 2 * math.pi - math.pi
            tx = math.sin(theta) * math.cos(phi)
            ty = math.cos(theta)
            tz = math.sin(theta) * math.sin(phi)
            rows += rgbe(*radiance(tx, ty, tz))
    header = f"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y {H} +X {W}\n".encode()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(header + bytes(rows))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
