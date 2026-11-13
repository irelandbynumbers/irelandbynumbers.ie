# Ireland by Numbers

Source for [irelandbynumbers.ie](https://irelandbynumbers.ie), official Irish statistics in clear, interactive charts and maps.

Built with [Quarto](https://quarto.org). Every push to `main` builds the site and publishes it to the `gh-pages` branch, and every pull request is checked to make sure the site still builds. Preview locally with `quarto preview`.

## How a chart is made

Each topic has a script, `analysis/<topic>/make_charts.py`, with a `build()` function that fetches its data, draws each chart with Plotly and writes it with `ibn.chart.Chart`:

```python
from ibn import cso, figures
from ibn.chart import Chart, Source

def build():
    df = cso.fetch("PEA01")          # saved to analysis/data/cso/PEA01.csv
    ...
    Chart(id="population-total", topic="population",
          title="...", subtitle="...",
          sources=[Source.cso("PEA01", "Population Estimates")],
          notes=["How the figure is measured, and any breaks in the series."],
          data=rows_as_plotted, figure=figures.lines(...)).write()
```

That writes `charts/<id>.html` (the chart's own page, with its source and notes, a table view, PNG and CSV downloads and an embed code), `charts/<id>.csv`, and an entry in `charts/index.json`. A topic page shows the chart with `{{< chart <id> >}}`.

```sh
pip install -r analysis/requirements.txt
python3 analysis/build.py              # rebuild every chart from the saved data
python3 analysis/build.py --refresh    # fetch the latest data first
python3 analysis/build.py housing      # one topic
python3 tools/cso_find.py search "dwelling completions"   # find a CSO table
quarto preview
```

`analysis/ibn/` holds the shared parts: `style.py` (colours and layout, shared with [Fianaise](https://github.com/fianaise/fianaise.ie)), `figures.py` (line charts and county maps with a time slider), `cso.py` (fetching CSO tables) and `chart.py` (the chart page). A new topic needs an entry in `topics.yml`, a folder with `index.qmd`, and a line in the navbar in `_quarto.yml`.

## Writing style

Plain, neutral sentences that state what the data shows. No first person, few colons, and bold or bullet points only where they help. Titles without commas, for example "Housing in numbers".

## Domains

`CNAME` points GitHub Pages at irelandbynumbers.ie. irelandbynumbers.org forwards to it from a separate repository, `irelandbynumbers/irelandbynumbers.org`, that holds only a redirect page.

DNS for irelandbynumbers.ie is four A records for `@` pointing to 185.199.108.153, 185.199.109.153, 185.199.110.153 and 185.199.111.153, and a CNAME for `www` pointing to irelandbynumbers.github.io.

Charts and text are CC BY 4.0. Code is MIT licensed (see `LICENSE-code`).
