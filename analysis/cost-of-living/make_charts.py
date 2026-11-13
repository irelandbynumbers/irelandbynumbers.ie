"""Cost of living charts, from the CSO Consumer Price Index."""
import pandas as pd
import plotly.graph_objects as go

from ibn import cso, figures, style
from ibn.chart import Chart, Source

TOPIC = "cost-of-living"
INDEX = "Consumer Price Index (Base Month December 2023 = 100)"
ANNUAL = "Percentage change over 12 months for Consumer Price Index"


def _cpi():
    df = cso.fetch("CPM20", where={"Statistic Label": [INDEX, ANNUAL]})
    df["date"] = pd.to_datetime(df["Month"], format="%Y %B")
    return df


# Shorter names for the CSO's spending groups, so they fit beside the bars on a phone.
SHORT = {
    "All Items": "All items",
    "Food and non-alcoholic beverages": "Food and soft drinks",
    "Alcoholic beverages, tobacco and narcotics": "Alcohol and tobacco",
    "Housing, water, electricity, gas and other fuels": "Housing and energy",
    "Furnishings, household equipment and routine household maintenance": "Household goods",
    "Recreation, sport and culture": "Recreation and culture",
    "Restaurants and accommodation services": "Restaurants and hotels",
    "Insurance and financial services": "Insurance and finance",
    "Personal care, social protection and miscellaneous goods and services": "Personal care and other",
    "Education services": "Education",
}


def build():
    inflation()
    price_change_by_group()


def inflation():
    df = _cpi()
    d = df[(df["Commodity Group"] == "All Items") &
           (df["Statistic Label"] == ANNUAL)]
    d = d[["date", "VALUE"]].dropna().rename(columns={"VALUE": "inflation"}).sort_values("date")
    d["date"] = d["date"].dt.strftime("%Y-%m")
    fig = figures.lines(d.reset_index(drop=True), "date", {"inflation": "Inflation"}, value_format=".1f", suffix="%",
                        hover_x="%B %Y")
    fig.add_hline(y=0, line=dict(color=style.INK_3, width=1))
    latest = pd.to_datetime(d.date.iloc[-1]).strftime("%B %Y")
    Chart(
        id="cost-of-living-inflation", topic=TOPIC,
        title="Inflation",
        subtitle=f"Change in consumer prices compared with the same month a year earlier, {pd.to_datetime(d.date.iloc[0]).strftime('%B %Y')} to {latest}.",
        sources=[Source.cso("CPM20", "Consumer Price Index")],
        notes=["The Consumer Price Index measures the change in the average price of the goods and services that households buy, "
               "weighted by how much households spend on each.",
               "A negative figure means prices were lower on average than a year earlier."],
        data=d, figure=fig,
    ).write()


def price_change_by_group():
    df = _cpi()
    idx = df[df["Statistic Label"] == INDEX].dropna(subset=["VALUE"])
    end = idx["date"].max()
    start = end - pd.DateOffset(years=5)
    a = idx[idx.date == start].set_index("Commodity Group")["VALUE"]
    b = idx[idx.date == end].set_index("Commodity Group")["VALUE"]
    d = ((b / a - 1) * 100).round(1).rename("percent_change").reset_index()
    d = d.rename(columns={"Commodity Group": "group"}).sort_values("percent_change").reset_index(drop=True)
    colours = [style.INK_2 if g == "All Items" else style.BLUE for g in d.group]
    labels = [SHORT.get(g, g) for g in d.group]
    fig = go.Figure(go.Bar(y=labels, x=d.percent_change, orientation="h", marker=dict(color=colours, cornerradius=4),
                           text=[f"{v:+.1f}%" for v in d.percent_change], textposition="outside",
                           textfont=dict(color=style.INK, size=12), cliponaxis=False,
                           hovertemplate="<b>%{y}</b>: %{x:+.1f}%<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=56, t=8, b=32), bargap=0.3,
                                        xaxis=style.value_axis(ticksuffix="%", nticks=4, tickangle=0, zeroline=True, zerolinecolor=style.INK_3),
                                        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=12))))
    span = f"{start.strftime('%B %Y')} to {end.strftime('%B %Y')}"
    Chart(
        id="cost-of-living-price-change-by-group", topic=TOPIC, height=520,
        title="Price changes by type of spending",
        subtitle=f"Change in consumer prices for each main group of goods and services, {span}.",
        sources=[Source.cso("CPM20", "Consumer Price Index")],
        notes=["Each group's change is calculated from its Consumer Price Index. All items is the change in the overall index, "
               "which weights each group by how much households spend on it.",
               "Housing and energy includes rents, mortgage interest, electricity, gas and other home heating fuels."],
        data=d.rename(columns={"group": "cso_group"}).assign(group=labels, period=span)[["group", "cso_group", "percent_change", "period"]], figure=fig,
    ).write()
