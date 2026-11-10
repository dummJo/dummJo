#!/usr/bin/env python3
"""Build the Vincinian SVG assets for the profile README.

The Hallmark Blueprint theme on its brownline sheet, read as a Leonardo
notebook: parchment and sepia ink in light mode, a night sepia sheet in dark
mode, the cheetah as a red-chalk (sanguine) study. The README swaps the two
with <picture>. Type is Cormorant Garamond and IBM Plex Mono (both SIL OFL),
subset to the glyphs each file uses and embedded, because an SVG served as an image cannot
fetch a webfont and would otherwise fall back to whatever the viewer has.

    python3 scripts/build_assets.py --fonts <dir with the .woff2 files>

The woff2 files come from the @fontsource npm packages:
cormorant-garamond-latin-{600-normal,500-normal,400-italic},
ibm-plex-mono-latin-500-normal. The build stops if a text pair falls below
WCAG AA (4.5:1) or a meaningful line below 3:1.
"""

import argparse
import base64
import io
from math import atan2, cbrt, cos, hypot, pi, radians, sin
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ASSETS = Path(__file__).resolve().parent.parent / "assets"

FONT_FILES = {
    "display": ("Cormorant Garamond", 600, "normal", "cormorant-garamond-latin-600-normal.woff2"),
    "body": ("Cormorant Garamond", 400, "italic", "cormorant-garamond-latin-400-italic.woff2"),
    "label": ("Cormorant Garamond", 500, "normal", "cormorant-garamond-latin-500-normal.woff2"),
    "mono": ("IBM Plex Mono", 500, "normal", "ibm-plex-mono-latin-500-normal.woff2"),
}


# ---------------------------------------------------------------- colour

def oklch(l, c, h):
    """OKLCH (L in %, C, h in degrees) to an sRGB hex string."""
    l /= 100
    a, b = c * cos(radians(h)), c * sin(radians(h))
    l_ = (l + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (l - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (l - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
           -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
           -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)

    def enc(x):
        x = min(max(x, 0.0), 1.0)
        x = 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
        return round(x * 255)
    return "#" + "".join(f"{enc(v):02x}" for v in rgb)


# Light is the theme's brownline sheet (references/themes/blueprint.md); dark is
# the same sheet at night, derived here: the ground and the ink swap ends of the
# sepia scale, the red pencil lifts so it still reads on the dark ground.
SHEETS = {
    "dark": dict(            # night sepia
        paper=oklch(24, 0.03, 60), paper3=oklch(20, 0.025, 60),
        ink=oklch(90, 0.04, 80), ink2=oklch(84, 0.045, 78), muted=oklch(74, 0.04, 70),
        chalk=oklch(66, 0.14, 35), rule_a=0.85, rule2_a=0.32, page="#0d1117",
    ),
    "light": dict(           # brownline
        paper=oklch(86, 0.045, 80), paper3=oklch(82, 0.045, 78),
        ink=oklch(28, 0.05, 50), ink2=oklch(28, 0.05, 50), muted=oklch(45, 0.05, 55),
        chalk=oklch(45, 0.19, 28), rule_a=0.85, rule2_a=0.32, page="#ffffff",
    ),
}


def _lum(hex_):
    ch = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def check_palette():
    fails = []
    for name, t in SHEETS.items():
        pairs = [("ink on paper", t["ink"], t["paper"], 4.5),
                 ("ink2 on paper", t["ink2"], t["paper"], 4.5),
                 ("muted on paper", t["muted"], t["paper"], 4.5),
                 ("paper on ink (primary button)", t["paper"], t["ink"], 4.5),
                 ("ink line on page (footer)", t["ink"], t["page"], 3.0),
                 ("chalk line on paper (cheetah)", t["chalk"], t["paper"], 3.0)]
        for label, fg, bg, need in pairs:
            r = contrast(fg, bg)
            print(f"  {name:5} {label:30} {r:5.2f}:1 (need {need}) {'ok' if r >= need else 'FAIL'}")
            if r < need:
                fails.append(f"{name}: {label}")
    if fails:
        raise SystemExit("contrast check failed: " + "; ".join(fails))


# ---------------------------------------------------------------- fonts

class Fonts:
    def __init__(self, directory):
        self.dir = Path(directory)

    def face(self, role, text):
        """An @font-face rule for one role, subset to the characters in text."""
        family, weight, style, fname = FONT_FILES[role]
        font = TTFont(self.dir / fname, recalcTimestamp=False)   # keep builds byte-identical
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["kern", "liga", "lnum"]
        opts.name_IDs = []
        opts.notdef_outline = True
        sub = subset.Subsetter(opts)
        sub.populate(text=text + " ")
        sub.subset(font)
        buf = io.BytesIO()
        font.flavor = "woff2"
        font.save(buf)
        data = base64.b64encode(buf.getvalue()).decode()
        alias = f"bp-{role}"
        return (f'@font-face{{font-family:"{alias}";font-weight:{weight};font-style:{style};'
                f'src:url(data:font/woff2;base64,{data}) format("woff2")}}',
                f'"{alias}", "{family}", Georgia, serif' if role != "mono"
                else f'"{alias}", "{family}", ui-monospace, monospace')


# ---------------------------------------------------------------- the cheetah

# One cheetah drawn as line ink, running right, paws on y=56, in a 120 x 60 box.
# Deep chest, tucked waist, long legs, small head with the tear mark. Two gallop
# poses swapped by opacity: legs extended, then gathered under the body.
CHEETAH_BODY = {
    "a": ("M22,24 C40,16 66,14 88,20",                                  # back
          "M88,33 C78,38 64,33 52,31 C40,30 30,32 24,31",               # chest to belly
          "M22,24 C18,26 18,30 24,31"),                                 # rump
    "b": ("M24,22 C40,10 64,10 86,18",
          "M86,32 C76,36 64,30 52,28 C40,28 32,31 26,30",
          "M24,22 C20,24 20,28 26,30"),
}
CHEETAH_LEGS = {
    "a": ("M86,32 L100,44 L114,48", "M82,34 L94,47 L106,54",
          "M28,30 L14,42 L2,46", "M32,32 L22,46 L10,54"),
    "b": ("M84,31 L76,45 L70,56", "M80,33 L70,46 L60,53",
          "M28,29 L42,44 L52,56", "M32,31 L48,42 L58,50"),
}
CHEETAH_HEAD = ("M88,20 C94,16 98,13 104,12",                              # neck, top
                "M88,33 C95,29 100,24 105,20",                              # neck, under
                "M104,11 C110,8 116,10 117,14 C118,18 112,21 105,20",       # head
                "M106,10 L107,6 L110,9",                                    # ear
                "M111,15 C111,17 110,19 108,21",                            # tear mark
                "M22,25 C10,27 4,35 2,27")                                  # tail
CHEETAH_DOTS = ((38, 22), (48, 20), (58, 19), (68, 19), (78, 21),
                (44, 26), (54, 25), (64, 25), (74, 26))


def cheetah(t, pose="run", sw=2.0, hatch=False):
    """The cheetah group. 'run' swaps the two gallop poses; 'a' or 'b' holds one;
    'both' lays the gathered pose faintly over the extended one, the way the
    Vitruvian figure carries two stances in one drawing."""
    ink = t["chalk"]   # Leonardo's animal studies are red chalk
    common = (f'fill="none" stroke="{ink}" stroke-width="{sw}" '
              f'stroke-linecap="round" stroke-linejoin="round"')
    head = "".join(f'<path d="{d}"/>' for d in CHEETAH_HEAD)
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="1.4" fill="{ink}" stroke="none"/>' for x, y in CHEETAH_DOTS)
    eye = f'<circle cx="112" cy="13" r="1.3" fill="{ink}" stroke="none"/>'

    def frame(key, attrs):
        body = "".join(f'<path d="{d}"/>' for d in CHEETAH_BODY[key])
        legs = "".join(f'<path d="{d}"/>' for d in CHEETAH_LEGS[key])
        return f'<g {attrs}>{body}{legs}</g>'

    if pose == "run":
        frames = frame("a", 'class="pose-a"') + frame("b", 'class="pose-b"')
    elif pose == "both":
        frames = frame("b", 'opacity="0.38"') + frame("a", "")
    else:
        frames = frame(pose, "")
    shade = ""
    if hatch:   # left-handed hatching: strokes fall from upper left to lower right
        shade = "".join(f'<line x1="{x}" y1="{y}" x2="{x + 3.2}" y2="{y + 4.6}" stroke-width="{sw * 0.5}" opacity="0.7"/>'
                        for x, y in ((25, 25), (28, 24.4), (31, 24), (34, 23.7), (80, 25), (83, 25.6), (86, 26.4),
                                     (91, 21), (94, 19.2), (97, 17.6)))
    return f'<g {common}>{frames}{head}{shade}{dots}{eye}</g>'


GALLOP_CSS = """
.pose-a{animation:gallop .34s steps(1,end) infinite}
.pose-b{animation:gallop .34s steps(1,end) infinite reverse;opacity:0}
@keyframes gallop{0%{opacity:1}50%{opacity:0}100%{opacity:1}}
@media (prefers-reduced-motion: reduce){
  .pose-a,.pose-b,.run,.draw,.drift{animation:none!important}
  .pose-b{opacity:0}.pose-a{opacity:1}
}"""


# ---------------------------------------------------------------- pieces

def svg(w, h, body, title, style):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{title}">\n<title>{title}</title>\n'
            f'<style>{style}</style>\n{body}\n</svg>\n')


def rgba(hex_, a):
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{a})"


def sheet(w, h, t):
    """The notebook page: ground plus a square keyline and a second one 5px in."""
    return (f'<rect width="{w}" height="{h}" fill="{t["paper"]}"/>'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" fill="none" '
            f'stroke="{rgba(t["ink"], t["rule_a"])}"/>'
            f'<rect x="5.5" y="5.5" width="{w - 11}" height="{h - 11}" fill="none" '
            f'stroke="{rgba(t["ink"], t["rule2_a"])}"/>')


def dimension(t, x0, x1, y, tick=14):
    """A dimension string: hairline, 45-degree ticks and extension lines at both ends."""
    c = rgba(t["ink"], t["rule_a"])
    d = tick / 2 / 1.414
    return (f'<g stroke="{c}" stroke-width="1">'
            f'<line class="draw" x1="{x0}" y1="{y}" x2="{x1}" y2="{y}"/>'
            f'<line x1="{x0}" y1="{y - 18}" x2="{x0}" y2="{y + 18}"/>'
            f'<line x1="{x1}" y1="{y - 18}" x2="{x1}" y2="{y + 18}"/>'
            f'<line x1="{x0 - d}" y1="{y + d}" x2="{x0 + d}" y2="{y - d}"/>'
            f'<line x1="{x1 - d}" y1="{y + d}" x2="{x1 + d}" y2="{y - d}"/></g>')


def study(t, cx, cy, r=104, side=168, k=1.72):
    """The cheetah set in a circle and a square, after the Vitruvian figure: the
    square stands on the circle's lowest point, the extended stride reaches the
    circle, the gathered stride sits inside the square."""
    c = rgba(t["ink"], 0.55)
    c2 = rgba(t["ink"], t["rule2_a"])
    sq_x, sq_y = cx - side / 2, cy + r - side
    return (f'<g fill="none" stroke-width="1">'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke="{c}"/>'
            f'<rect x="{sq_x}" y="{sq_y}" width="{side}" height="{side}" stroke="{c}"/>'
            f'<line x1="{cx}" y1="{cy - r - 8}" x2="{cx}" y2="{cy + r + 8}" stroke="{c2}"/>'
            f'<line x1="{cx - r - 8}" y1="{cy}" x2="{cx + r + 8}" y2="{cy}" stroke="{c2}"/></g>'
            f'<g transform="translate({cx - 60 * k:.1f},{cy - 30 * k + 4:.1f}) scale({k})">'
            f'{cheetah(t, pose="both", sw=1.25, hatch=True)}</g>')


# ---------------------------------------------------------------- assets
# Banner, heads and footer use a narrow viewBox with large type on purpose: a
# README image scales with the column, to about 0.45x on a phone, and the type
# has to stay readable there.

def banner(t, F):
    """The notebook page: name, role, the Vitruvian cheetah study, and the career
    as a dimension string from 2019 to 2026 with the cheetah running its length."""
    w, h = 800, 460
    name, tag = "ADAM MUHAMMAD", "Engineered to outrun."
    role, job_label, job = "Vincinian Engineer", "Day job", "Presales Engineer, PTTS"
    note = "study of a cheetah at full stride"
    span = "7 YEARS IN THE FIELD"
    f_disp, fam_disp = F.face("display", name + span)
    f_body, fam_body = F.face("body", tag + note)
    f_lab, fam_lab = F.face("label", role + job_label + job)
    f_mono, fam_mono = F.face("mono", "20196")
    x0, x1, y = 60, 740, 408
    run_px = x1 - x0 - 124
    style = (f_disp + f_body + f_lab + f_mono + GALLOP_CSS +
             f".run{{animation:run 7s linear infinite}}"
             f"@keyframes run{{0%{{transform:translateX(0);opacity:0}}6%{{opacity:1}}"
             f"88%{{opacity:1}}100%{{transform:translateX({run_px}px);opacity:0}}}}"
             f".draw{{transform-box:fill-box;transform-origin:left;animation:draw 1.2s cubic-bezier(.2,.7,.2,1) both}}"
             f"@keyframes draw{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}")
    body = f'''{sheet(w, h, t)}
<text x="40" y="88" font-family='{fam_disp}' font-weight="600" font-size="64" letter-spacing="0.5" fill="{t["ink"]}">{name}</text>
<text x="42" y="142" font-family='{fam_body}' font-style="italic" font-size="38" fill="{t["ink2"]}">{tag}</text>
<line x1="42" y1="172" x2="400" y2="172" stroke="{rgba(t["ink"], t["rule2_a"])}"/>
<text x="42" y="218" font-family='{fam_lab}' font-weight="500" font-size="36" fill="{t["ink"]}">{role}</text>
<text x="42" y="262" font-family='{fam_lab}' font-weight="500" font-size="24" fill="{t["muted"]}">{job_label}</text>
<text x="42" y="294" font-family='{fam_lab}' font-weight="500" font-size="29" fill="{t["ink"]}">{job}</text>
<text x="42" y="334" font-family='{fam_body}' font-style="italic" font-size="22" fill="{t["muted"]}">{note}</text>
{study(t, 626, 236)}
{dimension(t, x0, x1, y)}
<text x="{x0}" y="446" font-family='{fam_mono}' font-weight="500" font-size="26" fill="{t["ink"]}">2019</text>
<text x="{x1}" y="446" font-family='{fam_mono}' font-weight="500" font-size="26" fill="{t["ink"]}" text-anchor="end">2026</text>
<text x="{(x0 + x1) / 2}" y="446" font-family='{fam_disp}' font-weight="600" font-size="30" letter-spacing="1" style="font-variant-numeric:lining-nums" fill="{t["ink"]}" text-anchor="middle">{span}</text>
<g transform="translate({x0 + 4},{y - 57})"><g class="run">{cheetah(t)}</g></g>'''
    return svg(w, h, body, "Adam Muhammad, Vincinian Engineer; day job Presales Engineer at PTTS. Engineered to outrun. "
               "A red-chalk study of a cheetah in a circle and a square, and a career line from 2019 to 2026.", style)


SECTIONS = [
    ("projects", "01", "Things Built"),
    ("toolbox",  "02", "Toolbox"),
    ("years",    "03", "Field Years"),
    ("bench",    "04", "On the Bench"),
    ("contact",  "05", "Start a Project"),
]


def header(t, F, index, title, step, steps):
    """A numbered head with no filled ground: type, a rule, and the cheetah's track.
    The cheetah stands one station further in each head, so it keeps pace with a
    reader scrolling down the profile (a README cannot run a script)."""
    w, h = 720, 92
    f_disp, fam_disp = F.face("display", title.upper())
    f_mono, fam_mono = F.face("mono", index)
    tx0, tx1, ty = 484, 712, 76
    scale = 0.6
    cw = 120 * scale
    x = tx0 + (tx1 - tx0 - cw) * step / (steps - 1)
    rule, rule2 = rgba(t["ink"], t["rule_a"]), rgba(t["ink"], t["rule2_a"])
    stations = "".join(
        f'<line x1="{tx0 + cw / 2 + (tx1 - tx0 - cw) * i / (steps - 1):.1f}" y1="{ty - 4}" '
        f'x2="{tx0 + cw / 2 + (tx1 - tx0 - cw) * i / (steps - 1):.1f}" y2="{ty + 4}" stroke="{rule}"/>'
        for i in range(steps))
    body = f'''<line x1="0" y1="{h - 1}" x2="{w}" y2="{h - 1}" stroke="{rule}" stroke-width="1"/>
<text x="0" y="64" font-family='{fam_mono}' font-weight="500" font-size="26" fill="{t["ink"]}">{index}</text>
<text x="54" y="66" font-family='{fam_disp}' font-weight="600" font-size="44" letter-spacing="0.5" fill="{t["ink"]}">{title.upper()}</text>
<line x1="{tx0}" y1="{ty}" x2="{tx1}" y2="{ty}" stroke="{rule2}" stroke-width="1"/>
<line x1="{tx0}" y1="{ty}" x2="{x + cw / 2:.1f}" y2="{ty}" stroke="{rule}" stroke-width="2"/>
{stations}
<g transform="translate({x:.1f},{ty - 57 * scale:.1f}) scale({scale})">{cheetah(t, sw=2.4)}</g>'''
    return svg(w, h, body, f"{index} {title}", f_disp + f_mono + GALLOP_CSS)


def footer(t, F):
    """Three-phase supply in drafting line types (solid, dashed, dotted), and the
    cheetah standing at the finish post."""
    w, h, lam, amp, base = 720, 150, 180, 20, 50
    labels = ("L1", "L2", "L3")
    f_mono, fam_mono = F.face("mono", "".join(labels))
    dashes = ("", ' stroke-dasharray="10 6"', ' stroke-dasharray="1.5 5"')
    waves = []
    for shift, dash in zip((0, 120, 240), dashes):
        pts = " ".join(f"{x},{base - amp * sin(2 * pi * x / lam - radians(shift)):.1f}"
                       for x in range(0, w + lam + 1, 3))
        waves.append(f'<path d="M{pts}" fill="none" stroke="{t["ink"]}" stroke-width="1.8"'
                     f' stroke-linecap="round"{dash}/>')
    legend, lx = [], 226
    for label, dash in zip(labels, dashes):
        legend.append(f'<line x1="{lx}" y1="128" x2="{lx + 26}" y2="128" stroke="{t["ink"]}" '
                      f'stroke-width="2" stroke-linecap="round"{dash}/>'
                      f'<text x="{lx + 34}" y="135" font-family=\'{fam_mono}\' font-weight="500" '
                      f'font-size="20" fill="{t["ink"]}">{label}</text>')
        lx += 96
    post_x = 700
    style = (f_mono + GALLOP_CSS +
             f".drift{{animation:drift 12s linear infinite}}"
             f"@keyframes drift{{from{{transform:translateX(0)}}to{{transform:translateX(-{lam}px)}}}}")
    body = f'''<defs>
  <linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="#000"/><stop offset="0.1" stop-color="#fff"/><stop offset="0.6" stop-color="#fff"/><stop offset="0.74" stop-color="#000"/></linearGradient>
  <mask id="edges" maskUnits="userSpaceOnUse" x="0" y="0" width="{w}" height="96"><rect width="{w}" height="96" fill="url(#fade)"/></mask>
</defs>
<g mask="url(#edges)"><g class="drift">{"".join(waves)}</g></g>
<line x1="{post_x}" y1="36" x2="{post_x}" y2="100" stroke="{t["ink"]}" stroke-width="1.5"/>
<line x1="{post_x - 5}" y1="105" x2="{post_x + 5}" y2="95" stroke="{t["ink"]}" stroke-width="1.5"/>
<g transform="translate({post_x - 128},{100 - 57})">{cheetah(t, pose="a")}</g>
{"".join(legend)}'''
    return svg(w, h, body, "Three-phase supply, L1 L2 L3, and the cheetah at the finish post", style)


def button(t, F, label, w, primary):
    h = 48
    f_lab, fam = F.face("label", label)
    if primary:
        face = f'<rect width="{w}" height="{h}" fill="{t["ink"]}"/>'
        ink = t["paper"]
    else:
        face = (f'<rect width="{w}" height="{h}" fill="{t["paper"]}"/>'
                f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" fill="none" stroke="{t["ink"]}"/>')
        ink = t["ink"]
    body = (f'{face}<text x="{w / 2}" y="31" text-anchor="middle" fill="{ink}" '
            f'font-family=\'{fam}\' font-weight="500" font-size="21">{label}</text>')
    return svg(w, h, body, label, f_lab)


BUTTONS = [("button-email", "Email a project brief", 232, True),
           ("button-site", "dummjo.dev", 132, False)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True, help="directory holding the four .woff2 files")
    F = Fonts(ap.parse_args().fonts)
    print("palette contrast:")
    check_palette()
    for old in ASSETS.glob("header-*.svg"):   # heads are regenerated from SECTIONS; drop renamed ones
        old.unlink()
    written = []
    for name, t in SHEETS.items():
        files = {f"banner-{name}.svg": banner(t, F), f"footer-{name}.svg": footer(t, F)}
        for i, (slug, index, title) in enumerate(SECTIONS):
            files[f"header-{slug}-{name}.svg"] = header(t, F, index, title, i, len(SECTIONS))
        for slug, label, w, primary in BUTTONS:
            files[f"{slug}-{name}.svg"] = button(t, F, label, w, primary)
        for fname, content in files.items():
            (ASSETS / fname).write_text(content, encoding="utf-8")
            written.append((fname, len(content.encode())))
    print("\nwrote:")
    for fname, size in sorted(written):
        print(f"  {fname:34} {size / 1024:5.1f} KB")


if __name__ == "__main__":
    main()
