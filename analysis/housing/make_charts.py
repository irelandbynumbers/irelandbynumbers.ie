"""Housing charts: new homes, house prices and rents."""
import pandas as pd
import plotly.graph_objects as go

from ibn import cso, figures, homelessness, style
from ibn.chart import Chart, Source
from ibn.counties import SUMMED_NOTE, add_up, county

TOPIC = "housing"


def build():
    completions()
    house_prices()
    rents_map()
    prices_map()
    completions_map()
    renting_map()
    homelessness_trend()
    homelessness_regions()


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


def prices_map():
    df = cso.fetch("HPA03", where={"Dwelling Status": ["All Dwelling Statuses"], "Type of Buyer": ["All Buyer Types"],
                                   "Stamp Duty Event": ["Executions"], "Statistic Label": ["Volume of Sales", "Value of Sales"]})
    df = df[df["RPPI Region"] != "Dublin"]   # Dublin's total; its four council areas are added up instead
    d = df.pivot_table(index=["Year", "RPPI Region"], columns="Statistic Label", values="VALUE").reset_index()
    d = add_up(d, "RPPI Region", ["Volume of Sales", "Value of Sales"], by=["Year"])
    d["mean_price"] = (d["Value of Sales"] * 1e6 / d["Volume of Sales"]).round(-2).astype(int)
    d = d.rename(columns={"Year": "year", "Volume of Sales": "sales"})[["year", "county", "mean_price", "sales"]]
    d["sales"] = d.sales.astype(int)
    d = d.sort_values(["year", "county"]).reset_index(drop=True)
    fig = figures.county_map(d[["year", "county", "mean_price"]], "county", "mean_price", time="year",
                             legend_title="Average price paid (€)")
    fig.data[1].hovertemplate = "<b>%{location}</b><br>€%{z:,.0f}<extra></extra>"
    for fr in fig.frames:
        fr.data[1].hovertemplate = fig.data[1].hovertemplate
    y = d[d.year == d.year.max()].sort_values("mean_price")
    lo, hi = y.iloc[0], y.iloc[-1]
    Chart(
        id="housing-prices-map", topic=TOPIC, kind="map", height=640,
        title="Average house price by county",
        subtitle=f"Average price paid for homes bought at market value by households, {d.year.min()} to {d.year.max()}. "
                 "Use the slider to move through the years.",
        sources=[Source.cso("HPA03", "Market-based Household Purchases of Residential Dwellings")],
        notes=["Prices are from stamp duty returns filed with the Revenue Commissioners, for new and existing homes bought "
               "by households at market value. They are averages of the prices paid, so they reflect the mix of homes sold "
               "as well as price levels, and are not adjusted for inflation.",
               "The average is the total value of sales divided by the number of sales. It is used here rather than the median "
               "so that the CSO's figures for city and county areas can be combined. A few very expensive homes can pull "
               "the average up. " + SUMMED_NOTE.replace("council ", "")],
        key_fact=f"In {hi.year}, the average price paid for a home ranged from €{lo.mean_price:,} in {lo.county} "
                 f"to €{hi.mean_price:,} in {hi.county}.",
        data=d, figure=fig,
    ).write()


def completions_map():
    df = cso.fetch("NDQ05")
    df["year"] = df.Quarter.str[:4].astype(int)
    full = df.groupby("year").Quarter.nunique()
    df = df[df.year.isin(full[full == 4].index)]   # whole years only
    d = add_up(df, "Local Authority", ["VALUE"], by=["year"]).rename(columns={"VALUE": "completions"})
    # Homes per 1,000 people, using the population at the latest census before or in that year.
    pop = cso.fetch("F1001")
    pop = pop[(pop.Sex == "Both sexes") & pop.County.isin(figures.COUNTIES) & (pop.CensusYear >= 2011)]
    pop = pop.rename(columns={"County": "county", "CensusYear": "census_year", "VALUE": "population"})
    d["census_year"] = d.year.map(lambda y: max(c for c in pop.census_year.unique() if c <= y))
    d = d.merge(pop[["county", "census_year", "population"]], on=["county", "census_year"])
    d["completions"] = d.completions.astype(int)
    d["per_1000_people"] = (d.completions / d.population * 1000).round(1)
    d = d.sort_values(["year", "county"]).reset_index(drop=True)[["year", "county", "completions", "per_1000_people", "population", "census_year"]]
    fig = figures.county_map(d[["year", "county", "per_1000_people", "completions"]], "county", "per_1000_people", time="year",
                             value_format=".1f", legend_title="New homes per 1,000 people",
                             hover_extra="%{customdata[3]:,} new homes")
    y = d[d.year == d.year.max()].sort_values("per_1000_people")
    lo, hi = y.iloc[0], y.iloc[-1]
    Chart(
        id="housing-completions-map", topic=TOPIC, kind="map", height=640,
        title="New homes by county",
        subtitle=f"New homes completed each year for every 1,000 people living in the county, {d.year.min()} to {d.year.max()}. "
                 "Use the slider to move through the years.",
        sources=[Source.cso("NDQ05", "New Dwelling Completions"), Source.cso("F1001", "Population at Each Census")],
        notes=["Completions are counted when a new home is first connected to the electricity network, and are added up "
               "from the CSO's quarterly figures for each local authority.",
               "Each year is divided by the county's population at the latest census before or in that year "
               "(2011, 2016 or 2022), so the rate is approximate. " + SUMMED_NOTE],
        key_fact=f"In {hi.year}, {hi.county} had the most new homes for its population, {hi.per_1000_people:.1f} for every "
                 f"1,000 people, and {lo.county} the fewest, at {lo.per_1000_people:.1f}.",
        data=d, figure=fig,
    ).write()


def renting_map():
    df = cso.fetch("SAP2022T6T3CTY", where={"Statistic Label": ["Permanent private households"]})
    area = "Administrative Counties"
    d = df.pivot_table(index=area, columns="Type of Occupancy", values="VALUE", aggfunc="sum").reset_index()
    d["owned"] = d["Owned with mortgage or loan"] + d["Owned outright"]
    d["rented"] = (d["Rented from private landlord"] + d["Rented from Local Authority"]
                   + d["Rented from voluntary/co-operative housing body"])
    d = d.rename(columns={"Rented from private landlord": "private_rented"})
    d["households"] = d["Total"] - d["Not stated"]
    d = add_up(d, area, ["owned", "rented", "private_rented", "households"])
    d["percent_owned"] = (d.owned / d.households * 100).round(1)
    d["percent_rented"] = (d.rented / d.households * 100).round(1)
    d["percent_private_rented"] = (d.private_rented / d.households * 100).round(1)
    fig = figures.county_map(d, "county", "percent_rented", value_format=".0f", suffix="%",
                             legend_title="% of households renting their home")
    hi, lo = d.loc[d.percent_rented.idxmax()], d.loc[d.percent_rented.idxmin()]
    Chart(
        id="housing-renting-map", topic=TOPIC, kind="map", height=600,
        title="Renting by county",
        subtitle="Percentage of households renting their home, from a private landlord, a local authority or a housing body, Census 2022.",
        sources=[Source.cso("SAP2022T6T3CTY", "Census 2022 Small Area Population Statistics, permanent private households")],
        notes=["Households living in a permanent dwelling are counted by how they occupy it. Households that did not "
               "answer are left out of the total. The data file also gives the share owning their home and the share "
               "renting from a private landlord.", SUMMED_NOTE],
        key_fact=f"At the 2022 census, {hi.percent_rented:.0f}% of households in {hi.county} rented their home, the highest "
                 f"share of any county, compared with {lo.percent_rented:.0f}% in {lo.county}.",
        data=d[["county", "households", "owned", "rented", "private_rented", "percent_owned", "percent_rented", "percent_private_rented"]],
        figure=fig,
    ).write()


HOMELESS_SOURCE = Source("Department of Housing, Local Government and Heritage", "Monthly homelessness reports",
                         homelessness.PAGE, licence="CC BY-SA 4.0",
                         licence_url="https://creativecommons.org/licenses/by-sa/4.0/")
HOMELESS_NOTES = [
    "Counts people staying in emergency accommodation funded and overseen by local authorities, during one week "
    "near the end of each month. It does not include people sleeping rough, people staying with friends or family, "
    "people in domestic violence refuges, or people seeking international protection in State-provided accommodation.",
    "Dependants are people who depend on an adult in a family staying in emergency accommodation. Almost all are children.",
    "The Department of Housing publishes these figures under a CC BY-SA 4.0 licence, so this chart and its data may "
    "be reused under the same licence.",
]


def homelessness_trend():
    df = homelessness.fetch()
    d = df.groupby("month")[["Total Adults", "Number of Dependants in Families"]].sum().reset_index()
    d.columns = ["month", "adults", "dependants"]
    d["total"] = d.adults + d.dependants
    d[["adults", "dependants", "total"]] = d[["adults", "dependants", "total"]].astype(int)
    fig = figures.lines(d, "month", {"total": "All people", "adults": "Adults", "dependants": "Dependants"},
                        colours=[style.BLUE, style.INK_3, style.ORANGE], hover_x="%B %Y",
                        y_range=[0, d.total.max() * 1.1])
    when = lambda m: pd.to_datetime(m).strftime("%B %Y")
    a, b = d.iloc[0], d.iloc[-1]
    Chart(
        id="housing-homelessness", topic=TOPIC,
        title="People in emergency accommodation",
        subtitle=f"Number of people in emergency accommodation for homeless people, by month, {when(a.month)} to {when(b.month)}.",
        sources=[HOMELESS_SOURCE],
        notes=HOMELESS_NOTES,
        key_fact=f"{b.total:,} people were in emergency accommodation in {when(b.month)}, including {b.dependants:,} "
                 f"dependants, almost all of them children. That was up from {a.total:,} in {when(a.month)}.",
        data=d, figure=fig,
    ).write()


def homelessness_regions():
    df = homelessness.fetch()
    last = df.month.max()
    d = df[df.month == last][["Region", "Total Adults", "Number of Dependants in Families"]].copy()
    d.columns = ["region", "adults", "dependants"]
    d["total"] = d.adults + d.dependants
    d[["adults", "dependants", "total"]] = d[["adults", "dependants", "total"]].astype(int)
    d["percent"] = (d.total / d.total.sum() * 100).round(1)
    d = d.sort_values("total").reset_index(drop=True)
    fig = go.Figure(go.Bar(y=d.region, x=d.total, orientation="h", marker=dict(color=style.BLUE, cornerradius=4),
                           text=[f"{v:,}" for v in d.total], textposition="outside", cliponaxis=False,
                           textfont=dict(color=style.INK, size=12),
                           hovertemplate="<b>%{y}</b>: %{x:,} people<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=64, t=8, b=32), bargap=0.3,
                                        xaxis=style.value_axis(tickformat="~s"),
                                        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=12))))
    when = pd.to_datetime(last).strftime("%B %Y")
    dub = d[d.region == "Dublin"].iloc[0]
    Chart(
        id="housing-homelessness-regions", topic=TOPIC, height=440,
        title="Emergency accommodation by region",
        subtitle=f"Number of people in emergency accommodation for homeless people, by region, {when}.",
        sources=[HOMELESS_SOURCE],
        notes=HOMELESS_NOTES[:2] + [
            "The regions are those used for regional homelessness action plans, each covering several local "
            "authorities. The Department of Housing's reports list the local authorities in each region.",
            HOMELESS_NOTES[2]],
        key_fact=f"In {when}, {dub.percent:.0f}% of people in emergency accommodation were in Dublin, {dub.total:,} people.",
        data=d.iloc[::-1].reset_index(drop=True)[["region", "adults", "dependants", "total", "percent"]], figure=fig,
    ).write()
