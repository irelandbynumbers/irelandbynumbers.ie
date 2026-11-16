"""Cost of living charts, from the CSO Consumer Price Index."""
import pandas as pd
import plotly.graph_objects as go

from ibn import cso, eu, eurostat, figures, style
from ibn.chart import Chart, Source
from ibn.facts import higher_lower, lower_first

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

EU_GEO = eurostat.EU27 + [eurostat.EU]


def build():
    inflation()
    price_change_by_group()
    energy_prices()
    food_prices()
    average_prices()
    eu_comparisons()


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
    rate = d.inflation.iloc[-1]
    Chart(
        id="cost-of-living-inflation", topic=TOPIC,
        key_fact=f"Consumer prices were {higher_lower(rate)} in {latest} than a year earlier.",
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
    groups = d[d.group != "All Items"]
    top, overall = groups.iloc[-1], d[d.group == "All Items"].percent_change.iloc[0]
    Chart(
        id="cost-of-living-price-change-by-group", topic=TOPIC, height=520,
        key_fact=f"Over the five years to {end.strftime('%B %Y')}, prices rose most for "
                 f"{lower_first(SHORT.get(top.group, top.group))} ({top.percent_change:+.1f}%), "
                 f"compared with {overall:+.1f}% for all items.",
        title="Price changes by type of spending",
        subtitle=f"Change in consumer prices for each main group of goods and services, {span}.",
        sources=[Source.cso("CPM20", "Consumer Price Index")],
        notes=["Each group's change is calculated from its Consumer Price Index. All items is the change in the overall index, "
               "which weights each group by how much households spend on it.",
               "Housing and energy includes rents, mortgage interest, electricity, gas and other home heating fuels."],
        data=d.rename(columns={"group": "cso_group"}).assign(group=labels, period=span)[["group", "cso_group", "percent_change", "period"]], figure=fig,
    ).write()


ENERGY = {"Electricity": "electricity", "Natural gas through networks": "gas",
          "Liquid fuels (Home Heating Oil)": "home_heating_oil", "Petrol": "petrol", "All Items": "all_items"}
FOOD = {"Food": "food", "All Items": "all_items"}
BASE_YEAR = 2015


def _sub_indices(names):
    """Detailed CPI sub-indices, rebased so the average of BASE_YEAR is 100."""
    df = cso.fetch("CPM24", where={"Statistic Label": ["Consumer Price Index"],
                                   "Detailed Sub Indices": list(ENERGY) + list(FOOD)})
    df = df.rename(columns={"STATISTIC Label": "Statistic Label"})
    df = df[df["Detailed Sub Indices"].isin(names)].dropna(subset=["VALUE"])
    df["date"] = pd.to_datetime(df.Month, format="%Y %B")
    d = df.pivot_table(index="date", columns="Detailed Sub Indices", values="VALUE")
    d = (d / d[d.index.year == BASE_YEAR].mean() * 100).round(1)
    d = d[d.index.year >= BASE_YEAR].rename(columns=names).reset_index()
    d["date"] = d.date.dt.strftime("%Y-%m")
    return d[["date", *names.values()]]


INDEX_NOTE = (f"Each line is a Consumer Price Index, set to 100 for the average of {BASE_YEAR}, so a value of 150 means "
              f"prices were 50% higher than in {BASE_YEAR}. The indices measure the price of the same quantity over time, "
              "so they show price changes, not changes in how much households use.")


def energy_prices():
    d = _sub_indices(ENERGY)
    labels = {"electricity": "Electricity", "gas": "Gas", "home_heating_oil": "Home heating oil", "petrol": "Petrol",
              "all_items": "All items"}
    fig = figures.lines(d, "date", labels, value_format=".0f", hover_x="%B %Y", label_last=False,
                        colours=[style.BLUE, style.ORANGE, style.AQUA, style.PURPLE, style.INK_3])
    fig.update_layout(showlegend=True, legend=style.legend_top(), margin=dict(t=64))
    fig.add_hline(y=100, line=dict(color=style.INK_3, width=1, dash="dot"))
    b = d.iloc[-1]
    peak = d.loc[d.electricity.idxmax()]
    when = lambda x: pd.to_datetime(x).strftime("%B %Y")
    Chart(
        id="cost-of-living-energy-prices", topic=TOPIC,
        title="Energy prices",
        subtitle=f"Consumer prices for electricity, gas, home heating oil and petrol, compared with all items, "
                 f"{BASE_YEAR} average = 100, January {BASE_YEAR} to {when(b.date)}.",
        sources=[Source.cso("CPM24", "Consumer Price Index, detailed sub indices")],
        notes=[INDEX_NOTE,
               "Gas is natural gas supplied through the network. Electricity and gas prices include the effect of "
               "government energy credits in the months they were paid, which lowered bills."],
        key_fact=f"In {when(b.date)}, electricity prices were {b.electricity - 100:.0f}% higher than in {BASE_YEAR}, and "
                 f"gas prices {b.gas - 100:.0f}% higher, compared with {b.all_items - 100:.0f}% for all items.",
        data=d, figure=fig,
    ).write()


def food_prices():
    d = _sub_indices(FOOD)
    fig = figures.lines(d, "date", {"food": "Food", "all_items": "All items"}, value_format=".0f", hover_x="%B %Y",
                        colours=[style.BLUE, style.INK_3])
    fig.add_hline(y=100, line=dict(color=style.INK_3, width=1, dash="dot"))
    when = lambda x: pd.to_datetime(x).strftime("%B %Y")
    b = d.iloc[-1]
    jan21 = d[d.date == "2021-01"].iloc[0]
    Chart(
        id="cost-of-living-food-prices", topic=TOPIC,
        title="Food prices",
        subtitle=f"Consumer prices for food, compared with all items, {BASE_YEAR} average = 100, January {BASE_YEAR} to {when(b.date)}.",
        sources=[Source.cso("CPM24", "Consumer Price Index, detailed sub indices")],
        notes=[INDEX_NOTE, "Food covers food bought to eat at home. It does not include drinks, or meals in restaurants and cafés."],
        key_fact=f"Food prices were {b.food - 100:.0f}% higher in {when(b.date)} than in {BASE_YEAR}, compared with "
                 f"{b.all_items - 100:.0f}% for all items. Food prices rose {(b.food / jan21.food - 1) * 100:.0f}% between "
                 f"January 2021 and {when(b.date)}, after falling slightly in the years before.",
        data=d, figure=fig,
    ).write()


ITEMS = {
    "Bread, white sliced pan, large (800g)": "White sliced pan (800g)",
    "Full fat milk per 2 litre": "Full fat milk (2 litres)",
    "Butter per lb": "Butter (1lb)",
    "Large eggs per half dozen": "Large eggs (6)",
    "Irish cheddar per kg": "Irish cheddar (1kg)",
    "Uncooked chicken medium size 1.6kg": "Whole chicken (1.6kg)",
    "Potatoes 2.5 kg": "Potatoes (2.5kg)",
    "Bananas per kg": "Bananas (1kg)",
    "Tea bags per 80": "Tea bags (80)",
    "Petrol - unleaded per litre": "Petrol (1 litre)",
    "Diesel per litre": "Diesel (1 litre)",
    "Stout - draught bar (1 pint)": "Pint of stout in a bar",
}


def average_prices():
    df = cso.fetch("CPM12")
    df = df.rename(columns={"STATISTIC Label": "Statistic Label"})
    df["date"] = pd.to_datetime(df.Month, format="%Y %B")
    end = df.date.max()
    start = end - pd.DateOffset(years=5)
    p = df[df["Consumer Item"].isin(ITEMS) & df.date.isin([start, end])]
    d = p.pivot_table(index="Consumer Item", columns="date", values="VALUE").reset_index()
    d.columns = ["cso_item", "then", "now"]
    d["item"] = d.cso_item.map(ITEMS)
    d["percent_change"] = ((d.now / d.then - 1) * 100).round(1)
    d[["then", "now"]] = d[["then", "now"]].round(2)
    d = d.set_index("cso_item").loc[list(ITEMS)].reset_index()
    a, b = start.strftime("%B %Y"), end.strftime("%B %Y")
    d = d.sort_values("percent_change").reset_index(drop=True)
    fig = go.Figure(go.Bar(y=d.item, x=d.percent_change, orientation="h", marker=dict(color=style.BLUE, cornerradius=4),
                           text=[f"+{c:.0f}%  (€{t:.2f} to €{n:.2f})" if c >= 0 else f"{c:.0f}%  (€{t:.2f} to €{n:.2f})"
                                 for c, t, n in zip(d.percent_change, d.then, d.now)],
                           textposition="outside", cliponaxis=False, textfont=dict(color=style.INK, size=11),
                           customdata=d[["then", "now"]].values,
                           hovertemplate="<b>%{y}</b>: %{x:+.0f}%<br>€%{customdata[0]:.2f} to €%{customdata[1]:.2f}<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=150, t=8, b=32), bargap=0.3,
                                        xaxis=style.value_axis(ticksuffix="%", zeroline=True, zerolinecolor=style.INK_3),
                                        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=12))))
    food = d[~d.item.str.startswith(("Petrol", "Diesel", "Pint"))]
    top = food.loc[food.percent_change.idxmax()]
    Chart(
        id="cost-of-living-average-prices", topic=TOPIC, height=520,
        title="What everyday items cost",
        subtitle=f"Change in the national average price of selected items, {a} to {b}, with the price at each date.",
        sources=[Source.cso("CPM12", "National Average Price")],
        notes=["The CSO collects these prices each month from shops, pubs and filling stations around the country, as part "
               "of the Consumer Price Index. They are averages, so prices in any one shop can be higher or lower.",
               "The data file gives each item's average price at both dates."],
        key_fact=f"{top['item'].split(' (')[0]} cost €{top.now:.2f} on average in {b}, up from €{top.then:.2f} in {a}, "
                 f"a rise of {top.percent_change:.0f}%.",
        data=d.iloc[::-1][["item", "cso_item", "then", "now", "percent_change"]].rename(columns={"then": f"price_{start:%Y_%m}", "now": f"price_{end:%Y_%m}"}),
        figure=fig,
    ).write()


def eu_comparisons():
    df = eurostat.fetch("prc_hicp_aind", geo=EU_GEO, unit="RCH_A_AVG", coicop="CP00")
    eu.lines_chart(
        "cost-of-living-inflation-eu", TOPIC, "Inflation in Ireland and the EU",
        "Annual change in consumer prices, measured the same way in every EU country, {first} to {last}.",
        Source.eurostat("prc_hicp_aind", "HICP, annual data"), df,
        lambda w: f"Consumer prices in Ireland rose by {w.ireland.iloc[-1]:.1f}% in {w.year.iloc[-1]}, compared with "
                  f"{w.eu_average.iloc[-1]:.1f}% across the EU.",
        notes=["Uses the Harmonised Index of Consumer Prices (HICP), which every EU country calculates in the same way. "
               "It differs from the CSO's Consumer Price Index mainly by leaving out mortgage interest."],
        suffix="%")
    df = eurostat.fetch("prc_ppp_ind", name="prc_ppp_ind_aic", geo=EU_GEO,
                        na_item=["VI_PPS_EU27_2020_HAB", "PLI_EU27_2020"], ppp_cat=["A01", "GDP"])
    pli = df[(df.na_item == "PLI_EU27_2020") & (df.ppp_cat == "A01")]
    eu.rank_chart(
        "cost-of-living-price-levels-eu", TOPIC, "Price levels across the EU",
        "Price level of the goods and services households use, EU average = 100, {year}.",
        Source.eurostat("prc_ppp_ind", "Purchasing power adjusted GDP per capita and related indicators", "prc_ppp_ind_aic"),
        pli, lambda y, ie, ev, place: f"In {y}, prices in Ireland were {ie - 100:.0f}% above the EU average, {place}.",
        notes=["Compares the price of the same basket of goods and services in each country, covering what households "
               "buy and the services, such as health and education, provided to them by the State."],
        value_format=".0f")
