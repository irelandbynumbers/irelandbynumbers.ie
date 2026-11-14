"""Migration charts, from CSO population and migration estimates."""
import plotly.graph_objects as go

from ibn import cso, figures, style
from ibn.chart import Chart, Source

TOPIC = "migration"

NOTES = ["Migration is estimated from the Labour Force Survey and other sources, not counted, and the CSO revises "
         "the estimates after each census. Each year runs from May to the following April.",
         "Figures are published in thousands, rounded to the nearest hundred people."]

PLACES = {
    "United Kingdom (1)": "United Kingdom",
    "EU14 excl Irl (countries in the EU pre 2004 excluding UK & Ireland)": "Rest of the EU before 2004",
    "EU15 to EU27 (accession countries joined post 2004)": "EU countries that joined from 2004",
    "United States": "United States",
    "Canada": "Canada",
    "Australia": "Australia",
    "Other countries (23)": "Rest of the world",
}


# How each group reads in a sentence.
PHRASE = {
    "United Kingdom": "the United Kingdom",
    "Rest of the EU before 2004": "the other countries that were EU members before 2004",
    "EU countries that joined from 2004": "the EU countries that joined from 2004",
    "United States": "the United States",
    "Canada": "Canada",
    "Australia": "Australia",
    "Rest of the world": "countries outside the EU, the UK, the US, Canada and Australia",
}


def build():
    flows()
    by_place()


def flows():
    df = cso.fetch("PEA03")
    d = df[(df["Age Group"] == "All ages") & (df["Sex"] == "Both sexes")]
    d = d.pivot_table(index="Year", columns="Inward or Outward Flow", values="VALUE").reset_index()
    d = d.rename(columns={"Immigrants: All origins": "immigrants", "Emigrants: All destinations": "emigrants",
                          "Net migration": "net_migration"})[["Year", "immigrants", "emigrants", "net_migration"]]
    for c in ["immigrants", "emigrants", "net_migration"]:
        d[c] = (d[c] * 1000).round().astype(int)
    fig = figures.lines(d, "Year", {"immigrants": "Immigrants", "emigrants": "Emigrants", "net_migration": "Net migration"},
                        colours=[style.BLUE, style.ORANGE, style.INK_3], label_last=False)
    fig.update_layout(showlegend=True, legend=style.legend_top(), margin=dict(t=40))
    fig.add_hline(y=0, line=dict(color=style.INK_3, width=1))
    y = d.iloc[-1]
    peak = d.loc[d.emigrants.idxmax()]
    Chart(
        id="migration-flows", topic=TOPIC,
        title="People moving to and from Ireland",
        subtitle=f"Estimated number of people who moved to Ireland (immigrants) and who left (emigrants) "
                 f"in the twelve months to April, {d.Year.min()} to {d.Year.max()}.",
        sources=[Source.cso("PEA03", "Estimated Migration (Persons in April)")],
        notes=NOTES + ["Net migration is immigrants minus emigrants. A negative figure means more people left than arrived."],
        key_fact=f"In the twelve months to April {y.Year}, an estimated {y.immigrants:,} people moved to Ireland "
                 f"and {y.emigrants:,} left. Emigration was highest in {peak.Year}, at {peak.emigrants:,}.",
        data=d, figure=fig,
    ).write()


def by_place():
    df = cso.fetch("PEA18")
    year = df.Year.max()
    d = df[(df.Sex == "Both sexes") & (df.Year == year) & df.Country.isin(PLACES)]
    d = d.pivot_table(index="Country", columns="Origin or Destination", values="VALUE").reset_index()
    d = d.rename(columns={"Immigrants: All origins": "immigrants", "Emigrants: All destinations": "emigrants",
                          "Net migration": "net_migration"})
    d["place"] = d.Country.map(PLACES)
    for c in ["immigrants", "emigrants", "net_migration"]:
        d[c] = (d[c] * 1000).round().astype(int)
    d = d.sort_values("emigrants").reset_index(drop=True)
    fig = go.Figure()
    for col, label, colour in [("immigrants", "Arrived from", style.BLUE), ("emigrants", "Left for", style.ORANGE)]:
        fig.add_trace(go.Bar(y=d.place, x=d[col], name=label, orientation="h", marker=dict(color=colour, cornerradius=3),
                             hovertemplate=f"<b>%{{y}}</b><br>{label.lower()}: %{{x:,}}<extra></extra>"))
    fig.update_layout(style.base_layout(barmode="group", bargap=0.25, bargroupgap=0.05, showlegend=True,
                                        legend=style.legend_top(), margin=dict(l=8, r=24, t=40, b=32),
                                        xaxis=style.value_axis(tickformat="~s"),
                                        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=12))))
    top = d.sort_values("emigrants").iloc[-1]
    Chart(
        id="migration-by-place", topic=TOPIC, height=520,
        title="Where people came from and went to",
        subtitle=f"Estimated number of immigrants by the country or region they came from, and emigrants by where they went, "
                 f"in the twelve months to April {year}.",
        sources=[Source.cso("PEA18", "Estimated Migration (Persons in April)")],
        notes=NOTES + ["The groups are the ones the CSO publishes. Rest of the EU before 2004 means the 14 countries that were "
                       "EU members before 2004, other than Ireland and the United Kingdom. Rest of the world covers every other country."],
        key_fact=f"In the twelve months to April {year}, the largest group of emigrants, {top.emigrants:,} people, "
                 f"went to {PHRASE[top.place]}.",
        data=d[["place", "immigrants", "emigrants", "net_migration"]], figure=fig,
    ).write()
