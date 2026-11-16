"""Charts that compare Ireland (the State) with Northern Ireland.

Most use the joint tables the CSO and NISRA publish from the 2021 census in
Northern Ireland and the 2022 census in Ireland, which put the two on the
same definitions where they can."""
import plotly.graph_objects as go

from . import figures, style

IE, NI = "Ireland", "Northern Ireland"
COLOURS = {IE: style.BLUE, NI: style.PURPLE}
CENSUS_NOTE = ("From the joint tables the CSO and NISRA published from the 2022 census in Ireland and the 2021 census in "
               "Northern Ireland. The two censuses were a year apart, and some questions were asked differently.")
STATE_NOTE = "Ireland here means the State, not the whole island."


def lines(d, x, value_format=",.0f", suffix="", prefix="", y_range=None):
    """Ireland and Northern Ireland over time, as two labelled lines."""
    return figures.lines(d, x, {"ireland": IE, "northern_ireland": NI}, colours=[COLOURS[IE], COLOURS[NI]],
                         value_format=value_format, suffix=suffix, prefix=prefix, y_range=y_range)


def grouped_bars(d, label, value_format=".0f", suffix="%"):
    """Horizontal bars, one pair per row of `d` (columns ireland and northern_ireland)."""
    fig = go.Figure()
    for col, name in [("ireland", IE), ("northern_ireland", NI)]:
        fig.add_trace(go.Bar(y=d[label], x=d[col], name=name, orientation="h",
                             marker=dict(color=COLOURS[name], cornerradius=3),
                             text=[f"{format(v, value_format)}{suffix}" for v in d[col]], textposition="outside",
                             cliponaxis=False, textfont=dict(color=style.INK_2, size=11),
                             hovertemplate=f"<b>%{{y}}</b>, {name}: %{{x:.1f}}{suffix}<extra></extra>"))
    fig.update_layout(style.base_layout(
        barmode="group", bargap=0.25, bargroupgap=0.05, showlegend=True,
        legend=dict(style.legend_top(), traceorder="normal"), margin=dict(l=8, r=48, t=40, b=32),
        xaxis=style.value_axis(ticksuffix=suffix),
        yaxis=style.axis(automargin=True, autorange="reversed", tickfont=dict(color=style.INK_2, size=12))))
    return fig


def census_shares(df, category, keep, rename=None, total=None):
    """Percentages from a joint census table, one row per category in `keep`,
    with columns ireland and northern_ireland. Percentages are worked out from
    the counts, leaving out `total` and anything not in `keep`."""
    stat = [s for s in df["Statistic Label"].unique() if not s.lower().startswith(("percentage", "precentage"))][0]
    c = df[df["Statistic Label"] == stat]
    area = "Ireland and Northern Ireland"
    w = c.pivot_table(index=category, columns=area, values="VALUE")
    w = w.loc[keep]
    w = w.rename(index=rename or {})
    pct = (w / w.sum() * 100).round(1)
    out = pct.rename(columns={IE: "ireland", NI: "northern_ireland"}).reset_index().rename(columns={category: "category"})
    counts = w.rename(columns={IE: "ireland_people", NI: "northern_ireland_people"}).reset_index(drop=True)
    return out.join(counts.astype(int))
