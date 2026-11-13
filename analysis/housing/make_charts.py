"""Housing charts: new homes, house prices and rents."""
import pandas as pd
import plotly.graph_objects as go

from ibn import cso, figures, style
from ibn.chart import Chart, Source

TOPIC = "housing"


def build():
    completions()
    house_prices()
    rents_map()


def completions():
    df = cso.fetch("NDA01")
    d = df[df["Eircode Output"] == "All"][["Year", "VALUE"]].rename(columns={"VALUE": "completions"})
    d = d.sort_values("Year").reset_index(drop=True)
    fig = go.Figure(go.Bar(x=d.Year, y=d.completions, marker=dict(color=style.BLUE, cornerradius=4),
                           hovertemplate="<b>%{x}</b>: %{y:,} new homes<extra></extra>"))
    last = d.iloc[-1]
    fig.add_annotation(x=last.Year, y=last.completions, yshift=10, showarrow=False, yanchor="bottom",
                       text=f"<b>{last.completions:,.0f}</b>", font=dict(color=style.INK, size=13))
    fig.update_layout(style.base_layout(bargap=0.25, xaxis=style.axis(dtick=1, showline=True),
                                        yaxis=style.value_axis(tickformat="~s")))
    prev = d.iloc[-2]
    Chart(
        id="housing-completions", topic=TOPIC,
        key_fact=f"{last.completions:,.0f} new homes were completed in {last.Year}, compared with "
                 f"{prev.completions:,.0f} in {prev.Year}.",
        title="New homes completed each year",
        subtitle=f"Number of new dwellings completed in Ireland, {d.Year.min()} to {d.Year.max()}.",
        sources=[Source.cso("NDA01", "New Dwelling Completions")],
        notes=["A new dwelling is counted as completed when it is first connected to the electricity network. "
               "The count includes houses and apartments, built privately or by local authorities and approved housing bodies.",
               "Some connections can be for homes that were vacant for a long time rather than newly built, "
               "and the CSO adjusts for these."],
        data=d, figure=fig,
    ).write()


def house_prices():
    keep = {"National - all residential properties": "Ireland",
            "Dublin - all residential properties": "Dublin",
            "National excluding Dublin - all residential properties": "Outside Dublin"}
    df = cso.fetch("HPM09", where={"Type of Residential Property": list(keep)})
    d = df[(df["Statistic Label"] == "Residential Property Price Index") & df["Type of Residential Property"].isin(keep)]
    d = d.pivot_table(index="Month", columns="Type of Residential Property", values="VALUE", sort=False).reset_index()
    d = d.rename(columns={k: v.lower().replace(" ", "_") for k, v in keep.items()})
    d.insert(0, "date", pd.to_datetime(d["Month"], format="%Y %B"))
    d = d.drop(columns="Month").sort_values("date").reset_index(drop=True)
    d["date"] = d["date"].dt.strftime("%Y-%m")
    fig = figures.lines(d, "date", {"ireland": "Ireland", "dublin": "Dublin", "outside_dublin": "Outside Dublin"},
                        value_format=".1f", hover_x="%B %Y", label_last=False)
    fig.update_layout(showlegend=True, legend=style.legend_top(), margin=dict(t=40))
    fig.update_yaxes(tickformat=".0f")
    fig.add_hline(y=100, line=dict(color=style.CONTEXT, width=1, dash="dot"))
    latest = pd.to_datetime(d.date.iloc[-1]).strftime("%B %Y")
    gap = d.ireland.iloc[-1] - 100
    Chart(
        id="housing-prices", topic=TOPIC,
        key_fact=f"In {latest}, house prices nationally were {abs(gap):.0f}% {'above' if gap >= 0 else 'below'} their 2015 average, "
                 "before adjusting for inflation.",
        title="House prices",
        subtitle=f"Residential Property Price Index, January 2005 to {latest}. 100 is the average price level in 2015.",
        sources=[Source.cso("HPM09", "Residential Property Price Index")],
        notes=["The index tracks the prices paid for homes bought at market value, as filed with the Revenue Commissioners. "
               "It compares like with like, adjusting for the type, size and location of the homes sold each month.",
               "An index of 150 means prices are 50% higher than their 2015 average. The index is not adjusted for inflation."],
        data=d, figure=fig,
    ).write()


def rents_map():
    df = cso.fetch("RIA02", where={"Number of Bedrooms": ["All bedrooms"], "Property Type": ["All property types"],
                                   "Location": figures.COUNTIES})
    d = df[["Year", "Location", "VALUE"]].rename(columns={"Year": "year", "Location": "county", "VALUE": "average_monthly_rent"})
    d = d.dropna().sort_values(["year", "county"]).reset_index(drop=True)
    d["average_monthly_rent"] = d["average_monthly_rent"].round().astype(int)
    fig = figures.county_map(d, "county", "average_monthly_rent", time="year", value_format=",.0f",
                             legend_title="Average monthly rent (€)")
    fig.data[1].hovertemplate = "<b>%{location}</b><br>€%{z:,.0f} a month<extra></extra>"
    for fr in fig.frames:
        fr.data[1].hovertemplate = fig.data[1].hovertemplate
    y = d[d.year == d.year.max()].sort_values("average_monthly_rent")
    lo, hi = y.iloc[0], y.iloc[-1]
    Chart(
        id="housing-rents-map", topic=TOPIC, kind="map", height=640,
        key_fact=f"In {hi.year}, the average monthly rent on a new tenancy ranged from €{lo.average_monthly_rent:,} in "
                 f"{lo.county} to €{hi.average_monthly_rent:,} in {hi.county}.",
        title="Average rent by county",
        subtitle=f"Average monthly rent on new private tenancies registered with the Residential Tenancies Board, "
                 f"{d.year.min()} to {d.year.max()}. Use the slider to move through the years.",
        sources=[Source.cso("RIA02", "RTB Average Monthly Rent Report")],
        notes=["Rents are those agreed on new tenancies registered with the RTB in each year, for all property types "
               "and sizes. They are not adjusted for inflation, or for differences in the mix of homes let in each county.",
               "Rents on existing tenancies, and social housing rents, are not included."],
        data=d, figure=fig,
    ).write()
