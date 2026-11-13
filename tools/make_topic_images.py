"""Draw the topic thumbnails on the homepage (images/topic-*.svg).

Simple illustrations in the house colours, not charts, so they never go out
of date. Subtopic tiles use real chart thumbnails instead (tools/thumbnails.js).

Usage: python3 tools/make_topic_images.py
"""
import json
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "images")
BG, INK, GREY, LIGHT = "#f3f2ee", "#0b0b0b", "#c9c7c0", "#fafaf8"
BLUE, DARK, PALE, ORANGE, AQUA, GOLD = "#2a78d6", "#104281", "#b7d3f4", "#eb6834", "#1baf7a", "#c9930e"
W, H = 600, 400


def svg(body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{title}">'
            f'<title>{title}</title><rect width="{W}" height="{H}" fill="{BG}"/>{body}</svg>\n')


def population():
    geo = json.load(open(os.path.join(ROOT, "analysis", "ibn", "ireland_counties.geojson"), encoding="utf-8"))
    lon0, lon1, lat0, lat1 = -10.7, -5.3, 51.35, 55.45
    k = math.cos(math.radians(53.4))
    sx = (H - 40) / (lat1 - lat0)
    w = (lon1 - lon0) * k * sx
    ox = (W - w) / 2

    def pt(lon, lat):
        return f"{ox + (lon - lon0) * k * sx:.1f},{20 + (lat1 - lat) * sx:.1f}"

    paths = []
    for f in geo["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        d = "".join("M" + "L".join(pt(*c) for c in ring) + "Z" for poly in polys for ring in poly)
        ni = f["id"] == "Northern Ireland"
        paths.append(f'<path d="{d}" fill="{LIGHT if ni else BLUE}" stroke="{GREY if ni else "#fff"}" stroke-width="{1 if ni else 1.4}"/>')
    return svg("".join(paths), "Map of Ireland's counties")


def housing():
    body = [f'<rect x="0" y="330" width="{W}" height="70" fill="#e8e7e3"/>']
    # crane
    body.append(f'<g stroke="{GREY}" stroke-width="6" fill="none"><path d="M470 330V70M400 80H560M470 80L540 80"/>'
                f'<path d="M530 80V150" stroke-width="2"/></g><rect x="518" y="150" width="24" height="18" fill="{GOLD}"/>')
    houses = [(40, 90, BLUE), (140, 120, ORANGE), (270, 100, AQUA), (380, 140, DARK)]
    for x, hh, c in houses:
        w = 100 if x != 140 else 120
        top = 330 - hh
        body.append(f'<path d="M{x} 330V{top}L{x + w / 2} {top - 55}L{x + w} {top}V330Z" fill="{c}"/>')
        body.append(f'<rect x="{x + w / 2 - 12}" y="{330 - 46}" width="24" height="46" fill="#fff" opacity=".9"/>')
        for wx in (x + 14, x + w - 34):
            body.append(f'<rect x="{wx}" y="{top + 16}" width="20" height="20" fill="#fff" opacity=".85"/>')
    return svg("".join(body), "Houses and a crane")


def cost_of_living():
    b = []
    b.append(f'<rect x="215" y="120" width="40" height="80" rx="4" fill="#fff" stroke="{GREY}" stroke-width="3"/>'
             f'<rect x="215" y="140" width="40" height="22" fill="{BLUE}"/>')                     # milk
    b.append(f'<ellipse cx="300" cy="160" rx="60" ry="34" fill="{GOLD}"/>'
             f'<path d="M262 150q38 -14 76 0" stroke="#fff" stroke-width="3" fill="none" opacity=".7"/>')  # bread
    b.append(f'<circle cx="372" cy="170" r="28" fill="#c93a3a"/><path d="M372 142q4 -16 16 -20" stroke="{INK}" stroke-width="3" fill="none"/>')  # apple
    b.append(f'<path d="M160 190H440L410 320H190Z" fill="{ORANGE}"/>'
             f'<path d="M200 190Q300 70 400 190" stroke="{DARK}" stroke-width="10" fill="none"/>')
    for x in (230, 270, 310, 350, 390):
        b.append(f'<path d="M{x} 210V300" stroke="#fff" stroke-width="5" opacity=".5"/>')
    b.append(f'<circle cx="480" cy="290" r="50" fill="{AQUA}"/><text x="480" y="309" font-family="Helvetica, Arial, sans-serif" '
             f'font-size="56" font-weight="700" fill="#fff" text-anchor="middle">€</text>')
    return svg("".join(b), "A shopping basket and a euro coin")


def economy():
    b = [f'<path d="M80 330H520" stroke="{GREY}" stroke-width="4"/>']
    for i, hgt in enumerate([70, 95, 85, 130, 160, 150, 200]):
        b.append(f'<rect x="{100 + i * 58}" y="{330 - hgt}" width="38" height="{hgt}" rx="3" fill="{BLUE if i < 6 else DARK}"/>')
    b.append(f'<path d="M110 230L170 200L230 215L290 160L350 130L410 140L480 80" stroke="{ORANGE}" stroke-width="7" '
             f'fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
             f'<path d="M455 76L486 76L480 106" stroke="{ORANGE}" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    return svg("".join(b), "Bars rising with a line")


def education():
    b = [f'<rect x="0" y="330" width="{W}" height="70" fill="#e8e7e3"/>']
    b.append(f'<rect x="150" y="190" width="300" height="140" fill="{BLUE}"/>'
             f'<path d="M135 195L300 120L465 195Z" fill="{DARK}"/>'
             f'<rect x="270" y="70" width="60" height="70" fill="{DARK}"/><path d="M262 75L300 40L338 75Z" fill="{ORANGE}"/>'
             f'<circle cx="300" cy="105" r="14" fill="#fff"/>'
             f'<rect x="280" y="260" width="40" height="70" rx="20" fill="{AQUA}"/>')
    for x in (175, 225, 345, 395):
        for y in (215, 270):
            b.append(f'<rect x="{x}" y="{y}" width="30" height="30" fill="#fff" opacity=".85"/>')
    b.append(f'<path d="M60 350Q100 330 140 350V385Q100 365 60 385Z" fill="#fff" stroke="{GREY}" stroke-width="3"/>'
             f'<path d="M140 350Q180 330 220 350V385Q180 365 140 385Z" fill="#fff" stroke="{GREY}" stroke-width="3"/>')
    return svg("".join(b), "A school building and an open book")


def crime():
    b = [f'<rect x="0" y="330" width="{W}" height="70" fill="#e8e7e3"/>']
    # a car
    b.append(f'<path d="M90 300V250Q95 232 115 228L170 222L215 170Q225 160 245 160H345Q365 160 378 172L425 222L470 230Q495 236 498 260V300Z" fill="{BLUE}"/>'
             f'<path d="M232 220L258 180H300V220ZM318 220V180H350Q360 180 368 188L398 220Z" fill="#fff" opacity=".85"/>'
             f'<circle cx="170" cy="305" r="30" fill="{INK}"/><circle cx="170" cy="305" r="12" fill="{GREY}"/>'
             f'<circle cx="420" cy="305" r="30" fill="{INK}"/><circle cx="420" cy="305" r="12" fill="{GREY}"/>')
    # a padlock
    b.append(f'<path d="M478 120V95a32 32 0 0 1 64 0V120" stroke="{DARK}" stroke-width="12" fill="none"/>'
             f'<rect x="462" y="118" width="96" height="78" rx="10" fill="{ORANGE}"/>'
             f'<circle cx="510" cy="150" r="10" fill="#fff"/><rect x="506" y="152" width="8" height="24" fill="#fff"/>')
    return svg("".join(b), "A car and a padlock")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in [("population", population), ("housing", housing), ("cost-of-living", cost_of_living),
                     ("economy", economy), ("education", education), ("crime", crime)]:
        with open(os.path.join(OUT, f"topic-{name}.svg"), "w", encoding="utf-8") as f:
            f.write(fn())
        print("wrote", f"images/topic-{name}.svg")
