"""Charts that compare Ireland with the other EU countries, from Eurostat data."""
import pandas as pd
import plotly.graph_objects as go

from . import eurostat, figures, style

NOTE = ("The EU average is for the 27 current member states, weighted by population or by the size of each economy, "
        "as Eurostat calculates it.")


def ordinal(n):
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def latest(df, value="value"):
    """The latest year with figures for Ireland and for at least 20 of the 27
    countries, as a table of country, geo and value, highest first."""
    d = df[df.geo.isin(eurostat.EU27 + [eurostat.EU])].dropna(subset=[value])
    counts = d[d.geo.isin(eurostat.EU27)].groupby("time").geo.nunique()
    years = [y for y in counts[counts >= 20].index if not d[(d.time == y) & (d.geo == "IE")].empty]
    with_eu = [y for y in years if not d[(d.time == y) & (d.geo == eurostat.EU)].empty]
    year = int(max(years))
    if with_eu and max(with_eu) >= year - 1:   # prefer a year with an EU average, unless it is out of date
        year = int(max(with_eu))
    y = d[d.time == year].copy()
    y["country"] = [eurostat.country(g) or label for g, label in zip(y.geo, y.geo_label)]
    y = y.sort_values(value, ascending=False).reset_index(drop=True)
    return year, y[["country", "geo", value]].rename(columns={value: "value"})


def rank(d, higher_is="highest"):
    """Ireland's place among the countries in `d` (EU average left out), as
    '3rd highest', counting from the top of the sorted table."""
    c = d[d.geo != eurostat.EU].reset_index(drop=True)
    n = int(c.index[c.geo == "IE"][0]) + 1
    total = len(c)
    if n == 1:
        return f"the {higher_is} of the {total} EU countries", n, total
    if n == total:
        low = {"highest": "lowest", "lowest": "highest"}[higher_is]
        return f"the {low} of the {total} EU countries", n, total
    if n > total / 2:
        low = {"highest": "lowest", "lowest": "highest"}[higher_is]
        return f"the {ordinal(total - n + 1)} {low} of the {total} EU countries", n, total
    return f"the {ordinal(n)} {higher_is} of the {total} EU countries", n, total


def bars(d, value_format=".1f", suffix="", prefix=""):
    """Horizontal bars for each country, highest at the top, with Ireland in
    orange and the EU average in dark grey."""
    d = d.iloc[::-1]
    colours = [style.ORANGE if g == "IE" else style.INK_3 if g == eurostat.EU else style.CONTEXT for g in d.geo]
    fig = go.Figure(go.Bar(
        y=d.country, x=d.value, orientation="h", marker=dict(color=colours, cornerradius=3),
        text=[f"{prefix}{format(v, value_format)}{suffix}" for v in d.value], textposition="outside", cliponaxis=False,
        textfont=dict(color=style.INK_2, size=11),
        hovertemplate=f"<b>%{{y}}</b>: {prefix}%{{x:{value_format}}}{suffix}<extra></extra>"))
    fig.update_layout(style.base_layout(
        margin=dict(l=8, r=56, t=8, b=32), bargap=0.25,
        xaxis=style.value_axis(ticksuffix=suffix, tickprefix=prefix),
        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=11))))
    return fig


def ireland_and_eu(df, value_format=".1f", suffix="", y_range=None):
    """Ireland and the EU average over time, as two labelled lines."""
    w = df[df.geo.isin(["IE", eurostat.EU])].pivot_table(index="time", columns="geo", values="value").reset_index()
    w = w.rename(columns={"time": "year", "IE": "ireland", eurostat.EU: "eu_average"}).dropna(subset=["ireland"])
    w["year"] = w.year.astype(int)
    fig = figures.lines(w, "year", {"ireland": "Ireland", "eu_average": "EU average"}, colours=[style.ORANGE, style.INK_3],
                        value_format=value_format, suffix=suffix, y_range=y_range)
    return w, fig


def table(df, value):
    """Every country and year, wide, for the data file."""
    d = df[df.geo.isin(eurostat.EU27 + [eurostat.EU])].copy()
    d["country"] = [eurostat.country(g) or label for g, label in zip(d.geo, d.geo_label)]
    w = d.pivot_table(index="time", columns="country", values=value).reset_index().rename(columns={"time": "year"})
    w["year"] = w.year.astype(int)
    return w


def rank_chart(id, topic, title, subtitle, source, df, fact, notes=(), value_format=".1f", suffix="", prefix="",
               higher_is="highest", height=None):
    """A ranked bar chart of the latest year for every EU country, written as a Chart.

    `fact(year, ie, eu, place)` returns the key fact, where ie and eu are the
    values for Ireland and the EU average (None if Eurostat gives none) and
    place is Ireland's rank as words ("the 3rd highest of the 27 EU countries")."""
    from .chart import Chart
    year, d = latest(df)
    r = d.set_index("geo").value
    ie, ev = r["IE"], r.get(eurostat.EU)
    place, _, _ = rank(d, higher_is)
    Chart(
        id=id, topic=topic, height=height or (640 if eurostat.EU in r else 620),
        title=title, subtitle=subtitle.format(year=year), sources=[source],
        notes=list(notes) + ([NOTE] if ev is not None else []),
        key_fact=fact(year, ie, ev, place),
        data=d.rename(columns={"value": "value_" + str(year)}), figure=bars(d, value_format, suffix, prefix),
    ).write()


def lines_chart(id, topic, title, subtitle, source, df, fact, notes=(), value_format=".1f", suffix="", y_range=None):
    """Ireland and the EU average over time, written as a Chart, with every
    country's figures in the data file."""
    from .chart import Chart
    w, fig = ireland_and_eu(df, value_format, suffix, y_range)
    Chart(
        id=id, topic=topic, title=title,
        subtitle=subtitle.format(first=int(w.year.min()), last=int(w.year.max())), sources=[source],
        notes=list(notes) + [NOTE, "The data file has the figures for every EU country."],
        key_fact=fact(w), data=table(df, "value"), figure=fig,
    ).write()
