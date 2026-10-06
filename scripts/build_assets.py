#!/usr/bin/env python3
"""Build the Clean Signal SVG assets for the profile README.

Every asset ships in a dark and a light variant; the README swaps them
with <picture> and prefers-color-scheme. Run from anywhere:

    python3 scripts/build_assets.py

The palette is checked against WCAG AA before anything is written, and
the build stops if a pair falls short.
"""

from math import cos, hypot, pi, radians, sin
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"

SANS_DISPLAY = ("'Aptos Display', Aptos, 'Segoe UI Variable Display', 'Segoe UI', "
                "Inter, 'Helvetica Neue', Arial, sans-serif")
SANS = ("Aptos, 'Segoe UI Variable Text', 'Segoe UI', Inter, 'Helvetica Neue', "
        "Arial, sans-serif")
MONO = ("'Aptos Mono', 'Cascadia Mono', Consolas, 'SFMono-Regular', "
        "ui-monospace, monospace")

# Two core hues (mint = clean fundamental, amber = harmonics) on neutral ink/paper.
# *_text variants exist where the stroke tone is too light to carry small type.
THEMES = {
    "dark": dict(
        page="#0d1117",          # GitHub dark canvas, for contrast checks only
        card="#10171e", border="#1d2832",
        fg="#eaf3ef", muted="#9aabb4",
        mint="#3ddc97", mint_text="#3ddc97",
        amber="#f2b544", amber_text="#f2b544",
        slate="#6b7d88", trace="#f4fff9",
        btn="#3ddc97", on_btn="#0c1419",
    ),
    "light": dict(
        page="#ffffff",          # GitHub light canvas, for contrast checks only
        card="#f5f8f6", border="#dfe7e3",
        fg="#0f1a20", muted="#4c5b63",
        mint="#109a68", mint_text="#0b7d54",
        amber="#c27c06", amber_text="#8f5a00",
        slate="#7a8a94", trace="#0f1a20",
        btn="#0b7d54", on_btn="#ffffff",
    ),
}


# ---------------------------------------------------------------- contrast

def _luminance(hex_colour):
    h = hex_colour.lstrip("#")
    channels = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def check_palette():
    """Text needs 4.5:1 (WCAG 1.4.3); meaningful strokes need 3:1 (1.4.11)."""
    rules = [
        ("text", "card", ("fg", "muted", "mint_text", "amber_text"), 4.5),
        ("text", "page", ("muted",), 4.5),               # footer legend
        ("graphic", "card", ("mint", "amber", "slate"), 3.0),
        ("graphic", "page", ("mint", "amber", "slate"), 3.0),  # footer waves
        ("text", "btn", ("on_btn",), 4.5),                       # primary button label
        ("text", "card", ("fg",), 4.5),                          # secondary button label
    ]
    failures = []
    for name, t in THEMES.items():
        for kind, bg, keys, need in rules:
            for k in keys:
                ratio = contrast(t[k], t[bg])
                ok = ratio >= need
                print(f"  {name:5} {kind:7} {k:10} on {bg:4}  {ratio:5.2f}:1  "
                      f"(need {need})  {'ok' if ok else 'FAIL'}")
                if not ok:
                    failures.append(f"{name}.{k} on {bg}")
    if failures:
        raise SystemExit("contrast check failed: " + ", ".join(failures))


# ---------------------------------------------------------------- helpers

def polyline(points):
    return "M" + " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def path_length(points):
    return sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:]))


def smoothstep(edge0, edge1, x):
    u = min(max((x - edge0) / (edge1 - edge0), 0.0), 1.0)
    return u * u * (3 - 2 * u)


def phasor(cx, cy, r, t, stroke=3.0, dot=4.0):
    """Three-phase phasor set, L1 drawn at 90 degrees, 120 degrees apart."""
    parts = []
    for angle, key in ((90, "mint"), (-30, "amber"), (210, "slate")):
        x = cx + r * cos(radians(angle))
        y = cy - r * sin(radians(angle))
        parts.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{t[key]}" '
            f'stroke-width="{stroke}" stroke-linecap="round"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{dot}" fill="{t[key]}"/>')
    return "".join(parts)


def card(w, h, t):
    return (f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" '
            f'fill="{t["card"]}" stroke="{t["border"]}"/>')


def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}" role="img" aria-label="{title}">\n'
            f'<title>{title}</title>\n{body}\n</svg>\n')


# ---------------------------------------------------------------- banner

def banner(t):
    """A harmonic-rich current settles into a clean 50 Hz sine past an active filter."""
    w, h = 960, 352
    x0, x1, base, amp, cycles = 64, 896, 262, 26, 6
    lam = (x1 - x0) / cycles
    filter_x = 475

    pts = []
    for i in range(int(x1 - x0) + 1):
        x = x0 + i
        th = 2 * pi * (x - x0) / lam
        distortion = 1 - smoothstep(330, 620, x)
        v = sin(th) + distortion * (0.30 * sin(5 * th) + 0.18 * sin(7 * th) + 0.10 * sin(11 * th))
        pts.append((x, base - amp * v))
    wave = polyline(pts)
    length = path_length(pts)
    dash = 90
    dur = "7s"

    ticks = "".join(
        f'<line x1="{x0 + k * lam / 2:.1f}" y1="{base - 4}" x2="{x0 + k * lam / 2:.1f}" '
        f'y2="{base + 4}"/>' for k in range(cycles * 2 + 1))

    body = f'''<defs>
  <linearGradient id="clean" gradientUnits="userSpaceOnUse" x1="{x0}" y1="0" x2="{x1}" y2="0">
    <stop offset="0" stop-color="{t["amber"]}"/>
    <stop offset="0.36" stop-color="{t["amber"]}"/>
    <stop offset="0.66" stop-color="{t["mint"]}"/>
    <stop offset="1" stop-color="{t["mint"]}"/>
  </linearGradient>
</defs>
{card(w, h, t)}

<!-- scope axis: the wave reads as a measurement, not a decoration -->
<g stroke="{t["slate"]}" stroke-width="1" opacity="0.55">
  <line x1="{x0}" y1="{base}" x2="{x1}" y2="{base}"/>
  {ticks}
</g>
<line x1="{filter_x}" y1="206" x2="{filter_x}" y2="304" stroke="{t["slate"]}"
      stroke-width="1.2" stroke-dasharray="4 5"/>

<path id="wave" d="{wave}" fill="none" stroke="url(#clean)" stroke-width="2.6"
      stroke-linejoin="round" stroke-linecap="round"/>

<!-- oscilloscope trace sweeping left to right -->
<g opacity="0">
  <animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;0.04;0.71;0.75;1"
           dur="{dur}" repeatCount="indefinite"/>
  <path d="{wave}" fill="none" stroke="{t["trace"]}" stroke-width="3.4" stroke-linecap="round"
        stroke-dasharray="{dash} {length + 200:.0f}" stroke-dashoffset="{dash}">
    <animate attributeName="stroke-dashoffset" values="{dash};{dash - length:.1f};{dash - length:.1f}"
             keyTimes="0;0.75;1" dur="{dur}" repeatCount="indefinite"/>
  </path>
  <g>
    <animateMotion dur="{dur}" repeatCount="indefinite" keyPoints="0;1;1" keyTimes="0;0.75;1"
                   calcMode="linear"><mpath xlink:href="#wave"/></animateMotion>
    <circle r="11" fill="{t["mint"]}" opacity="0.28"/>
    <circle r="4.5" fill="{t["trace"]}"/>
  </g>
</g>

<!-- phasor mark, rotating counter-clockwise as phasors do -->
<g transform="translate(852,100)">
  <circle r="44" fill="none" stroke="{t["border"]}" stroke-width="1.5"/>
  <g>
    <animateTransform attributeName="transform" type="rotate" from="0" to="-360"
                      dur="24s" repeatCount="indefinite"/>
    {phasor(0, 0, 36, t)}
  </g>
  <circle r="3" fill="{t["fg"]}"/>
</g>

<text x="64" y="128" fill="{t["fg"]}" font-family="{SANS_DISPLAY}" font-size="76"
      font-weight="600" letter-spacing="-0.5">Adam Muhammad</text>
<text x="64" y="184" fill="{t["muted"]}" font-family="{SANS}" font-size="30">Engineered to outrun.</text>

<g font-family="{MONO}" font-size="17">
  <text x="{x0}" y="334" fill="{t["amber_text"]}">h5 · h7 · h11</text>
  <text x="{filter_x}" y="334" fill="{t["muted"]}" text-anchor="middle">active filter</text>
  <text x="{x1}" y="334" fill="{t["mint_text"]}" text-anchor="end">50 Hz fundamental</text>
</g>'''
    return svg(w, h, body, "Adam Muhammad. Engineered to outrun.")


# ---------------------------------------------------------------- section glyphs

GX0, GX1, GCY, GAMP = 712, 868, 44, 16
GW = GX1 - GX0


def glyph_samples(t):
    """Activity: a sampled signal, one cycle, thirteen samples."""
    out = [f'<line x1="{GX0}" y1="{GCY}" x2="{GX1}" y2="{GCY}" stroke="{t["slate"]}" stroke-width="1.5"/>']
    for i in range(13):
        x = GX0 + i * GW / 12
        y = GCY - GAMP * sin(2 * pi * i / 12)
        out.append(f'<line x1="{x:.1f}" y1="{GCY}" x2="{x:.1f}" y2="{y:.1f}" stroke="{t["mint"]}" stroke-width="2"/>'
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{t["mint"]}"/>')
    return "".join(out)


def glyph_converge(t):
    """OT / IT: two signals whose phase difference closes to zero."""
    lam = GW / 3
    a, b = [], []
    for i in range(GW + 1):
        x = GX0 + i
        th = 2 * pi * i / lam
        phi = 1.4 * (1 - i / GW)
        a.append((x, GCY - GAMP * sin(th + phi)))
        b.append((x, GCY - GAMP * sin(th - phi)))
    common = 'fill="none" stroke-width="2.4" stroke-linecap="round"'
    return (f'<path d="{polyline(a)}" stroke="{t["amber"]}" {common}/>'
            f'<path d="{polyline(b)}" stroke="{t["mint"]}" {common}/>')


def glyph_phasor(t):
    """Field record: the three-phase set the work is built on."""
    cx = GX1 - 24  # right-aligned with the wider glyphs
    return (f'<circle cx="{cx}" cy="{GCY}" r="22" fill="none" stroke="{t["slate"]}" stroke-width="1.2"/>'
            + phasor(cx, GCY, 18, t, stroke=2.4, dot=3))


def glyph_clock(t):
    """Timeline: a clock signal, four periods."""
    p = GW / 4
    hi, lo = GCY - GAMP, GCY + GAMP
    d = f"M{GX0},{lo}"
    for k in range(4):
        x = GX0 + k * p
        d += f" V{hi} H{x + p / 2:.1f} V{lo} H{x + p:.1f}"
    return (f'<path d="{d}" fill="none" stroke="{t["mint"]}" stroke-width="2.4" '
            f'stroke-linejoin="round" stroke-linecap="round"/>')


def glyph_burst(t):
    """Contact: a transmitted burst, carrier under a raised envelope."""
    lam = GW / 9
    pts = []
    for i in range(GW + 1):
        env = sin(pi * i / GW)
        pts.append((GX0 + i, GCY - GAMP * env * sin(2 * pi * i / lam)))
    return (f'<path d="{polyline(pts)}" fill="none" stroke="{t["mint"]}" stroke-width="2.2" '
            f'stroke-linecap="round"/>')


SECTIONS = [
    ("activity",     "01", "Activity",            glyph_samples),
    ("convergence",  "02", "OT / IT Convergence", glyph_converge),
    ("field-record", "03", "Field Record",        glyph_phasor),
    ("timeline",     "04", "Timeline",            glyph_clock),
    ("contact",      "05", "Contact",             glyph_burst),
]


def header(t, index, title, glyph):
    # SVG type scales with the column: ~0.4x on a 360 px phone, ~0.9x on desktop.
    # 36 keeps the title near 14 px on mobile so it never drops below body text weight.
    w, h = 900, 88
    body = (f'{card(w, h, t)}\n'
            f'<text x="32" y="56" fill="{t["mint_text"]}" font-family="{MONO}" font-size="24">{index}</text>\n'
            f'<text x="84" y="57" fill="{t["fg"]}" font-family="{SANS}" font-size="36" '
            f'font-weight="600">{title}</text>\n'
            f'{glyph(t)}')
    return svg(w, h, body, f"{index} {title}")


# ---------------------------------------------------------------- footer

def footer(t):
    """Three-phase supply, L1 L2 L3 at 120 degrees, drifting slowly left."""
    w, h, lam, amp, base = 900, 124, 225, 24, 52
    waves = []
    for shift, key in ((0, "mint"), (120, "amber"), (240, "slate")):
        pts = [(x, base - amp * sin(2 * pi * x / lam - radians(shift)))
               for x in range(0, w + lam + 1, 2)]
        waves.append(f'<path d="{polyline(pts)}" fill="none" stroke="{t[key]}" '
                     f'stroke-width="2.2" stroke-linecap="round"/>')

    legend, x = [], 358
    for label, key in (("L1", "mint"), ("L2", "amber"), ("L3", "slate")):
        legend.append(f'<line x1="{x}" y1="109" x2="{x + 18}" y2="109" stroke="{t[key]}" '
                      f'stroke-width="3" stroke-linecap="round"/>'
                      f'<text x="{x + 25}" y="114" fill="{t["muted"]}">{label}</text>')
        x += 70

    body = f'''<defs>
  <linearGradient id="fade" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#000"/><stop offset="0.12" stop-color="#fff"/>
    <stop offset="0.88" stop-color="#fff"/><stop offset="1" stop-color="#000"/>
  </linearGradient>
  <mask id="edges" maskUnits="userSpaceOnUse" x="0" y="0" width="{w}" height="96">
    <rect width="{w}" height="96" fill="url(#fade)"/>
  </mask>
</defs>
<g mask="url(#edges)">
  <g>
    <animateTransform attributeName="transform" type="translate" from="0 0" to="-{lam} 0"
                      dur="12s" repeatCount="indefinite"/>
    {"".join(waves)}
  </g>
</g>
<g font-family="{MONO}" font-size="15">{"".join(legend)}</g>'''
    return svg(w, h, body, "Three-phase supply, L1 L2 L3")


# ---------------------------------------------------------------- buttons

def button(t, label, w, primary):
    """Link targets for the README. Rendered at height=44 so every one meets the
    44 px tap-target floor on phones, where shields.io badges sit at 20 px."""
    h = 44
    if primary:
        face = f'<rect width="{w}" height="{h}" rx="12" fill="{t["btn"]}"/>'
        ink = t["on_btn"]
    else:
        face = (f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" '
                f'fill="{t["card"]}" stroke="{t["border"]}"/>')
        ink = t["fg"]
    body = (f'{face}\n<text x="{w / 2}" y="28" text-anchor="middle" fill="{ink}" '
            f'font-family="{SANS}" font-size="17" font-weight="600">{label}</text>')
    return svg(w, h, body, label)


BUTTONS = [
    ("button-email", "Email a project brief", 252, True),
    ("button-site",  "dummjo.dev",            136, False),
]


# ---------------------------------------------------------------- build

def main():
    print("palette contrast:")
    check_palette()
    ASSETS.mkdir(exist_ok=True)
    written = []
    for name, t in THEMES.items():
        files = {f"banner-{name}.svg": banner(t), f"footer-{name}.svg": footer(t)}
        for slug, index, title, glyph in SECTIONS:
            files[f"header-{slug}-{name}.svg"] = header(t, index, title, glyph)
        for slug, label, w, primary in BUTTONS:
            files[f"{slug}-{name}.svg"] = button(t, label, w, primary)
        for fname, content in files.items():
            (ASSETS / fname).write_text(content, encoding="utf-8")
            written.append((fname, len(content.encode())))
    print("\nwrote:")
    for fname, size in sorted(written):
        print(f"  {fname:34} {size / 1024:5.1f} KB")


if __name__ == "__main__":
    main()
