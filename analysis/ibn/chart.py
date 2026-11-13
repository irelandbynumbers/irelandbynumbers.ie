"""Write a chart as its own page, with its data, ready to embed.

Each chart becomes three things in charts/:

    charts/<id>.html   the chart's own page: title, interactive chart, source,
                       notes, and buttons to download a PNG or the data, or
                       copy an embed code. Topic pages show it in an iframe
                       ({{< chart <id> >}}), and anyone can embed it the same way.
    charts/<id>.csv    the data drawn in the chart, exactly as plotted.
    charts/index.json  one entry per chart (title, topic, sources, files),
                       read by the chart shortcode and the All charts page.

Usage, in a topic script:

    from ibn.chart import Chart, Source
    Chart(id="population-ireland", topic="population", title=..., subtitle=...,
          sources=[Source.cso("PEA01", "Population Estimates (Persons in April)")],
          notes=["..."], data=df, figure=fig).write()
"""
import html
import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import date

import plotly
import plotly.offline

from . import style

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHARTS = os.path.join(ROOT, "charts")
SITE = "https://irelandbynumbers.ie"

CC_BY = ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/")

TOPICS = {}      # slug -> display name, filled from topics.yml
_REGISTRY = []   # charts written in this run


def load_topics():
    """Topic slugs and names, from the list the homepage also uses."""
    import yaml  # PyYAML, installed with the analysis requirements
    with open(os.path.join(ROOT, "topics.yml"), encoding="utf-8") as f:
        for t in yaml.safe_load(f):
            TOPICS[t["path"].strip("/")] = t["title"]
    return TOPICS


@dataclass
class Source:
    publisher: str
    title: str
    url: str
    licence: str = CC_BY[0]
    licence_url: str = CC_BY[1]

    @classmethod
    def cso(cls, code, title):
        from .cso import table_url
        return cls("Central Statistics Office (CSO)", f"{title} ({code})", table_url(code))

    def html(self):
        lic = f'<a href="{self.licence_url}">{html.escape(self.licence)}</a>' if self.licence_url else html.escape(self.licence)
        return (f'{html.escape(self.publisher)}, <a href="{html.escape(self.url)}">{html.escape(self.title)}</a>'
                f' <span class="lic">({lic})</span>')

    def text(self):
        return f"{self.publisher}, {self.title}"


@dataclass
class Chart:
    id: str
    topic: str
    title: str
    subtitle: str
    sources: list
    data: object            # pandas DataFrame, the rows as plotted
    figure: object          # plotly Figure
    notes: list = field(default_factory=list)   # short paragraphs (may hold simple HTML)
    height: int = 460       # plot height in pixels
    kind: str = "chart"     # "chart" or "map"

    def write(self):
        assert self.topic in TOPICS, f"{self.id}: unknown topic {self.topic!r} (see topics.yml)"
        assert self.sources, f"{self.id}: every chart needs a source"
        os.makedirs(CHARTS, exist_ok=True)
        lib = _plotly_lib()
        self.data.to_csv(os.path.join(CHARTS, f"{self.id}.csv"), index=False)
        with open(os.path.join(CHARTS, f"{self.id}.html"), "w", encoding="utf-8") as f:
            f.write(self._page(lib))
        _REGISTRY.append(dict(
            id=self.id, topic=self.topic, title=self.title, subtitle=self.subtitle, kind=self.kind,
            page=f"/charts/{self.id}.html", csv=f"/charts/{self.id}.csv",
            sources=[dict(publisher=s.publisher, title=s.title, url=s.url, licence=s.licence) for s in self.sources],
            built=date.today().isoformat(),
        ))
        print("wrote", f"charts/{self.id}.html", "and .csv")

    def _page(self, lib):
        fig = self.figure.to_plotly_json()
        meta = dict(id=self.id, title=self.title, subtitle=self.subtitle,
                    source="Data from " + "; ".join(s.text() for s in self.sources),
                    credit=f"irelandbynumbers.ie/charts/{self.id} · CC BY 4.0")
        notes = "".join(f"<p>{n}</p>" for n in self.notes)
        sources = "; ".join(s.html() for s in self.sources)
        topic_name = TOPICS[self.topic]
        title = html.escape(self.title)
        sub = html.escape(self.subtitle)
        fig_json = plotly.io.to_json(fig, validate=False).replace("</", "<\\/")
        return TEMPLATE.format(
            title=title, sub=sub, id=self.id, site=SITE, lib=lib, height=self.height,
            topic=self.topic, topic_name=html.escape(topic_name), sources=sources,
            notes_block=(f'<details class="notes"><summary>About this data</summary>{notes}</details>' if notes else ""),
            fig=fig_json, meta=json.dumps(meta).replace("</", "<\\/"),
            font=style.FONT.replace('"', "'"), ink=style.INK, ink2=style.INK_2, ink3=style.INK_3, grid=style.GRID,
        )


def write_index():
    """charts/index.json, plus the All charts list (_all-charts.md) the site includes.

    Entries from earlier runs are kept, so one topic script can be run alone.
    """
    path = os.path.join(CHARTS, "index.json")
    old = []
    if os.path.exists(path):
        old = json.load(open(path, encoding="utf-8"))
    new_ids = {c["id"] for c in _REGISTRY}
    charts = [c for c in old if c["id"] not in new_ids] + _REGISTRY
    charts = [c for c in charts if os.path.exists(os.path.join(CHARTS, f"{c['id']}.html"))]
    order = list(TOPICS)
    charts.sort(key=lambda c: (order.index(c["topic"]) if c["topic"] in order else 99, c["id"]))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(charts, f, indent=1, ensure_ascii=False)
        f.write("\n")
    lines = []
    for slug in order:
        group = [c for c in charts if c["topic"] == slug]
        if not group:
            continue
        lines.append(f"\n## [{TOPICS[slug]}](/{slug}/)\n")
        for c in group:
            src = "; ".join(s["publisher"] for s in c["sources"])
            lines.append(f"- [{c['title']}]({c['page']}). {c['subtitle']} *{src}.* [CSV]({c['csv']})")
    with open(os.path.join(ROOT, "_all-charts.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines).strip() + "\n")
    print(f"wrote charts/index.json ({len(charts)} charts)")


def _plotly_lib():
    """One shared copy of plotly.js (and the world outline geo charts ask for) in charts/lib/."""
    version = plotly.offline.get_plotlyjs_version()
    name = f"plotly-{version}.min.js"
    lib = os.path.join(CHARTS, "lib")
    os.makedirs(lib, exist_ok=True)
    if not os.path.exists(os.path.join(lib, name)):
        src = os.path.join(os.path.dirname(plotly.__file__), "package_data", "plotly.min.js")
        shutil.copyfile(src, os.path.join(lib, name))
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "ireland_counties.geojson"),
                    os.path.join(lib, "ireland_counties.geojson"))
    return f"lib/{name}"


TEMPLATE = """<!doctype html>
<html lang="en-IE">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | Ireland by Numbers</title>
<meta name="description" content="{sub}">
<link rel="canonical" href="{site}/charts/{id}.html">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{sub}">
<meta property="og:site_name" content="Ireland by Numbers">
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  html, body {{ margin: 0; background: #fff; }}
  body {{ font-family: {font}; color: {ink2}; font-size: 15px; line-height: 1.45; }}
  a {{ color: #1f5fae; }}
  .site {{ display: none; padding: 12px 16px; border-bottom: 1px solid {grid}; font-size: 14px; }}
  .site a {{ text-decoration: none; }}
  .site .brand {{ font-weight: 700; color: {ink}; }}
  .is-top .site {{ display: block; }}
  main {{ max-width: 980px; margin: 0 auto; padding: 14px 16px 12px; }}
  .is-top main {{ padding-top: 24px; }}
  h1 {{ font-size: 1.3rem; line-height: 1.25; margin: 0 0 4px; color: {ink}; }}
  .sub {{ margin: 0 0 8px; }}
  #plot {{ width: 100%; }}
  footer {{ margin-top: 8px; font-size: 13px; color: {ink2}; }}
  footer p {{ margin: 0 0 6px; }}
  .lic {{ color: {ink3}; }}
  details.notes {{ margin: 0 0 8px; }}
  details.notes summary {{ cursor: pointer; color: #1f5fae; }}
  details.notes p {{ margin: 6px 0; }}
  .actions {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }}
  .actions a, .actions button {{
    font: inherit; font-size: 13px; color: {ink}; background: #f3f2ee; border: 1px solid {grid};
    border-radius: 4px; padding: 4px 10px; cursor: pointer; text-decoration: none; }}
  .actions a:hover, .actions button:hover {{ background: #e8e7e3; }}
  .is-top .only-embedded {{ display: none; }}
  .embed textarea {{ width: 100%; height: 64px; font: 12px ui-monospace, monospace; }}
  .credit {{ color: {ink3}; }}
  :focus-visible {{ outline: 3px solid #1f5fae; outline-offset: 2px; }}
  .table-wrap {{ max-height: 420px; overflow: auto; border: 1px solid {grid}; border-radius: 4px; margin: 4px 0 8px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; font-variant-numeric: tabular-nums; }}
  caption {{ text-align: left; padding: 6px 8px; color: {ink}; font-weight: 600; }}
  th, td {{ padding: 4px 8px; border-bottom: 1px solid {grid}; text-align: left; }}
  td.num, th.num {{ text-align: right; }}
  thead th {{ position: sticky; top: 0; background: #f3f2ee; color: {ink}; }}
</style>
<script src="{lib}"></script>
</head>
<body>
<nav class="site"><a class="brand" href="/">Ireland by Numbers</a> &nbsp;›&nbsp; <a href="/{topic}/">{topic_name}</a></nav>
<main>
  <h1>{title}</h1>
  <p class="sub">{sub}</p>
  <div id="plot" role="img" aria-label="{title}. {sub} Select Show table below the chart to read the data as a table." style="height:{height}px"></div>
  <div class="table-wrap" hidden><table><caption>{title}</caption><thead></thead><tbody></tbody></table></div>
  <footer>
    <p>Data from {sources}.</p>
    {notes_block}
    <div class="actions">
      <button type="button" id="table" aria-expanded="false">Show table</button>
      <button type="button" id="png">Download PNG</button>
      <a href="{id}.csv" download>Download data (CSV)</a>
      <button type="button" id="embed">Embed</button>
      <a class="only-embedded" href="{id}.html" target="_top">Open chart page</a>
    </div>
    <div class="embed" hidden>
      <p>Copy this code to show the chart on your own site.</p>
      <textarea readonly></textarea>
    </div>
    <p class="credit"><a href="/">Ireland by Numbers</a> · Chart licensed <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>, free to reuse with credit to Ireland by Numbers and the source above.</p>
  </footer>
</main>
<script>
const FIG = {fig};
const META = {meta};
const CONFIG = {{displayModeBar: false, responsive: true, scrollZoom: false,
  topojsonURL: new URL("lib/topojson/", location.href).href}};
const top_ = window.self === window.top;
if (top_) document.documentElement.classList.add("is-top");
const gd = document.getElementById("plot");
Plotly.newPlot(gd, FIG.data, FIG.layout, CONFIG).then(() => {{
  if (FIG.frames && FIG.frames.length) Plotly.addFrames(gd, FIG.frames);
}});

// Embedded on a page: tell the page how tall the chart is, so the frame fits.
function postHeight() {{
  if (top_) return;
  parent.postMessage({{ibnChart: META.id, height: document.documentElement.scrollHeight}}, "*");
}}
new ResizeObserver(postHeight).observe(document.body);
window.addEventListener("load", postHeight);

// PNG: the chart as shown, with its title, subtitle, source and credit drawn in.
document.getElementById("png").addEventListener("click", () => {{
  const W = 1200, H = Math.round(W * 0.66);
  const layout = JSON.parse(JSON.stringify(gd.layout));
  delete layout.sliders; delete layout.updatemenus; delete layout.title;
  let sub = META.subtitle;
  const s = (gd.layout.sliders || [])[0];
  if (s && s.steps && s.steps[s.active || 0]) sub += " Shown for " + s.steps[s.active || 0].label + ".";
  const wrap = (t, n) => t.replace(new RegExp("(.{{1," + n + "}})(\\\\s|$)", "g"), "$1<br>").replace(/<br>$/, "");
  const m = layout.margin || {{}};
  const T = layout.geo ? 150 : 120, B = (m.b || 0) + 70;
  layout.margin = Object.assign({{}}, m, {{t: T, b: B}});
  const ph = H - T - B;  // plot height; header and footer sit outside it, in paper units
  const note = (text, px, anchor, size, colour) => ({{text, x: 0, xref: "paper", y: px / ph, yref: "paper",
    xanchor: "left", yanchor: anchor, showarrow: false, align: "left", font: {{size, color: colour}}}});
  layout.annotations = (layout.annotations || []).concat([
    note("<b>" + META.title + "</b>", ph + T - 18, "top", 22, "{ink}"),
    note(wrap(sub, 130), ph + T - 52, "top", 15, "{ink2}"),
    note(wrap(META.source, 150), -(B - 32), "bottom", 12, "{ink2}"),
    note(META.credit, -(B - 12), "bottom", 12, "{ink3}")]);
  layout.width = W; layout.height = H;
  Plotly.downloadImage({{data: gd.data, layout: layout, config: CONFIG}},
    {{format: "png", width: W, height: H, scale: 2, filename: META.id}});
}});

// The data as a table, from the same CSV people download.
document.getElementById("table").addEventListener("click", async (e) => {{
  const wrap = document.querySelector(".table-wrap");
  const btn = e.currentTarget;
  if (!wrap.dataset.loaded) {{
    const text = await (await fetch(META.id + ".csv")).text();
    const rows = parseCSV(text.trim());
    const head = rows.shift();
    const isNum = head.map((_, i) => rows.length && rows.every((r) => r[i] === "" || !isNaN(+r[i])));
    const plain = head.map((h) => /year|period|date|quarter|month|code/i.test(h));
    const cell = (tag, v, i) => {{ const el = document.createElement(tag); el.textContent = isNum[i] && !plain[i] && v !== "" && tag === "td" ? (+v).toLocaleString("en-IE") : v; if (isNum[i]) el.className = "num"; return el; }};
    const tr = document.createElement("tr"); head.forEach((h, i) => {{ const th = cell("th", h, i); th.scope = "col"; tr.append(th); }});
    wrap.querySelector("thead").append(tr);
    const body = wrap.querySelector("tbody");
    rows.forEach((r) => {{ const tr = document.createElement("tr"); r.forEach((v, i) => tr.append(cell("td", v, i))); body.append(tr); }});
    wrap.dataset.loaded = "1";
  }}
  wrap.hidden = !wrap.hidden;
  btn.textContent = wrap.hidden ? "Show table" : "Hide table";
  btn.setAttribute("aria-expanded", String(!wrap.hidden));
  postHeight();
}});
function parseCSV(t) {{
  const rows = [[]]; let f = "", q = false;
  for (let i = 0; i < t.length; i++) {{
    const c = t[i];
    if (q) {{ if (c === '"' && t[i + 1] === '"') {{ f += '"'; i++; }} else if (c === '"') q = false; else f += c; }}
    else if (c === '"') q = true;
    else if (c === ",") {{ rows[rows.length - 1].push(f); f = ""; }}
    else if (c === "\\n") {{ rows[rows.length - 1].push(f.replace(/\\r$/, "")); rows.push([]); f = ""; }}
    else f += c;
  }}
  rows[rows.length - 1].push(f);
  return rows;
}}

// Embed code, pointing at this chart's page.
document.getElementById("embed").addEventListener("click", () => {{
  const box = document.querySelector(".embed");
  box.hidden = !box.hidden;
  const url = "{site}/charts/" + META.id + ".html";
  box.querySelector("textarea").value =
    '<iframe src="' + url + '" title="' + META.title.replace(/"/g, "&quot;") +
    '" width="100%" height="' + (document.documentElement.scrollHeight + 20) + '" style="border:0" loading="lazy"></iframe>';
  postHeight();
}});
</script>
</body>
</html>
"""
