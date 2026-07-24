"""
ordinal_ramp.py
────────────────
Single-hue OKLCH ordinal ramp for the per-year map legend. Years are ordinal
(swapping their order changes the meaning), so per the dataviz skill this uses
one hue with monotone lightness steps rather than N categorical hues.

Parameters (L_LIGHT/L_DARK/CHROMA/HUE) were tuned and validated at N=9
(2018-2026) with scripts/validate_palette.js --ordinal: all checks pass
(adjacent ΔL >= 0.06, light-end contrast >= 2:1 vs a white/near-white surface,
single hue). If the active year count grows much past ~10-11 (i.e. this
project runs unattended for several more years), re-validate — the fixed
0.76-0.23 lightness span divided across more steps will eventually pack
adjacent years too close together to read as distinct on the map.
"""

import math

L_LIGHT = 0.76
L_DARK  = 0.23
CHROMA  = 0.105
HUE_DEG = 258


def _oklch_to_hex(L: float, C: float, h_deg: float) -> str:
    h = math.radians(h_deg)
    a = C * math.cos(h)
    b = C * math.sin(h)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3

    r  =  4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g  = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    def to_srgb(c: float) -> float:
        c = max(0.0, min(1.0, c))
        return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055

    def to255(c: float) -> int:
        return round(max(0.0, min(1.0, c)) * 255)

    r255, g255, b255 = to255(to_srgb(r)), to255(to_srgb(g)), to255(to_srgb(bb))
    return f"#{r255:02x}{g255:02x}{b255:02x}"


def year_color_ramp(n: int) -> list[str]:
    """N hex colors, light (oldest) -> dark (newest), single blue hue."""
    if n <= 1:
        return [_oklch_to_hex(L_LIGHT, CHROMA, HUE_DEG)]
    step = (L_LIGHT - L_DARK) / (n - 1)
    return [_oklch_to_hex(L_LIGHT - i * step, CHROMA, HUE_DEG) for i in range(n)]
