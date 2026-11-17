"""Small chart helpers shared by several topics."""
import plotly.graph_objects as go

from . import style

def hbars(d, label, value, value_format=".0f", suffix="%", colour=None):
    fig = go.Figure(go.Bar(y=d[label], x=d[value], orientation="h", marker=dict(color=colour or style.BLUE, cornerradius=3),
                           text=[f"{format(v, value_format)}{suffix}" for v in d[value]], textposition="outside",
                           cliponaxis=False, textfont=dict(color=style.INK, size=12),
                           hovertemplate=f"<b>%{{y}}</b>: %{{x:{value_format}}}{suffix}<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=48, t=8, b=32), bargap=0.35,
                                        xaxis=style.value_axis(ticksuffix=suffix),
                                        yaxis=style.axis(automargin=True, autorange="reversed",
                                                         tickfont=dict(color=style.INK_2, size=12))))
    return fig


OECD_NAMES = {"Korea (the Republic of)South Korea": "South Korea", "Netherlands (the)": "Netherlands",
              "United Kingdom of Great Britain and Northern Ireland (the)": "United Kingdom"}


def oecd_trust(institution, year=None):
    """Share of people who trust an institution in each country in the OECD
    Trust Survey, as republished by the CSO (TRA312): a table of country, geo
    and value, highest first, with geo "IE" for Ireland and the EU code for
    the OECD average, so ibn.eu.bars colours them."""
    from . import cso, eurostat
    df = cso.fetch("TRA312")
    df = df[df["Trust in people and institutions"] == institution].dropna(subset=["VALUE"])
    year = year or int(df.Year.max())
    d = df[df.Year == year].rename(columns={"OECD Countries": "country", "VALUE": "value"})
    d["country"] = d.country.replace(OECD_NAMES)
    d["geo"] = d.country.map({"Ireland": "IE", "OECD average": eurostat.EU}).fillna("")
    return year, d.sort_values("value", ascending=False).reset_index(drop=True)[["country", "geo", "value"]]
