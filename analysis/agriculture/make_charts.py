"""Agriculture and food charts: farms and farmers, livestock and milk, what
farming produces and earns, fertiliser use, organic farming compared with the
EU, and food waste. Emissions from farming are in the environment topic and
food prices in the cost of living topic."""
import pandas as pd
import plotly.graph_objects as go

from ibn import cso, eu, eurostat, figures, style
from ibn.chart import Chart, Source
from ibn.charts import hbars

TOPIC = "agriculture"
EU_GEO = eurostat.EU27 + [eurostat.EU]
FSS = "Farm Structure Survey 2023"
COA = "Census of Agriculture 2020"


def build():
    farm_types()
    holder_age()
    dairy_map()
    organic_eu()
    livestock()
    cows()
    milk()
    fertiliser()
    output_mix()
    income()
    food_waste()


def farm_types():
    df = cso.fetch("IFS08")
    df = df[(df.Region == "Ireland") & (df.Year == df.Year.max())]
    year = int(df.Year.max())
    p = df.pivot_table(index="Farm Type", columns="Statistic Label", values="VALUE")
    names = {"Specialist beef production": "Beef", "Specialist dairying": "Dairy", "Specialist sheep": "Sheep",
             "Mixed grazing livestock": "Mixed grazing livestock", "Specialist tillage": "Tillage (crops)",
             "Mixed crops and livestock": "Mixed crops and livestock", "Mixed field crops": "Mixed field crops",
             "Other": "Other"}
    w = (p.loc[list(names)].rename(index=names).rename(columns={"Number of Farms": "farms",
                                                                "Percentage of Agricultural Holdings": "percent"})
         .rename_axis("farm_type").reset_index().sort_values("percent", ascending=False))
    w = w.astype({"farms": int})
    total = int(p.loc["All farms", "Number of Farms"])
    beef = w.set_index("farm_type").loc["Beef"]
    Chart(
        id="agriculture-farm-types", topic=TOPIC, height=360,
        title="Types of farm",
        subtitle=f"Share of farms in Ireland, by main type of farming, {year}.",
        sources=[Source.cso("IFS08", FSS)],
        notes=["Each farm is grouped by where most of its standard output comes from. A specialist beef farm, for "
               "example, earns most of its output from cattle reared for beef.",
               "The Farm Structure Survey counts farms with at least one hectare of farmed land, or with livestock or "
               "crops above set minimum levels. The data file has the number of farms of each type."],
        key_fact=f"There were {total:,} farms in Ireland in {year}. {beef.percent:.0f}% were specialist beef farms, "
                 f"the most common type.",
        data=w, figure=hbars(w, "farm_type", "percent", colour=style.AQUA),
    ).write()


def holder_age():
    df = cso.fetch("IFS14")
    year = int(df.Year.max())
    w = df[df.Year == year][["Age Group", "VALUE"]].rename(columns={"Age Group": "age_group", "VALUE": "percent"})
    w["age_group"] = w.age_group.str.replace(" - ", " to ").str.replace(" years and over", " and over").str.replace(" years", "")
    avg = cso.fetch("AVA43")
    avg = avg[(avg["Electoral Division"] == "State") & (avg["Statistic Label"] == "Average Age of Holder")]
    a = avg.set_index("Census Year").VALUE
    r = w.set_index("age_group").percent
    Chart(
        id="agriculture-holder-age", topic=TOPIC, height=300,
        title="Age of farmers",
        subtitle=f"Farm holders in Ireland by age group, {year}.",
        sources=[Source.cso("IFS14", FSS), Source.cso("AVA43", COA)],
        notes=["The holder is the person in whose name the farm is run. The average ages in the key fact come from the Census of Agriculture, held every ten years."],
        key_fact=f"In {year}, {r.iloc[-1]:.0f}% of farm holders were aged 65 or over and {r.iloc[0]:.0f}% were under 35. "
                 f"The average age of a farm holder was {a.loc[2020]:.0f} in 2020, up from {a.loc[2000]:.0f} in 2000.",
        data=w, figure=hbars(w.assign(age_group=w.age_group), "age_group", "percent", colour=style.AQUA),
    ).write()


def dairy_map():
    df = cso.fetch("AVA34")
    df = df[(df["Farm Type"] == "Specialist dairying")]
    df = df.assign(county=df.County.str.replace("Co. ", "", regex=False))
    p = df.pivot_table(index="county", columns="Statistic Label", values="VALUE")
    d = p.rename(columns={"Percentage of Agricultural Holdings": "percent_dairy", "Number of Farms": "dairy_farms"})
    d = d.reindex(figures.COUNTIES).rename_axis("county").reset_index()[["county", "percent_dairy", "dairy_farms"]]
    d = d.astype({"dairy_farms": int})
    fig = figures.county_map(d, "county", "percent_dairy", value_format=".0f", suffix="%",
                             legend_title="Share of farms that are dairy farms",
                             hover_extra="%{customdata[2]:,} dairy farms")
    d = d.sort_values("percent_dairy", ascending=False).reset_index(drop=True)
    top, second, low = d.iloc[0], d.iloc[1], d.iloc[-1]
    Chart(
        id="agriculture-dairy-map", topic=TOPIC, kind="map", height=560,
        title="Dairy farms by county",
        subtitle="Specialist dairy farms as a share of all farms in each county, 2020.",
        sources=[Source.cso("AVA34", COA)],
        notes=["A specialist dairy farm earns most of its output from milk. The Census of Agriculture is held every "
               "ten years, and 2020 is the latest. The data file has the number of dairy farms in each county."],
        key_fact=f"In 2020, {top.percent_dairy:.0f}% of farms in {top.county} were dairy farms, the highest share of any "
                 f"county, followed by {second.county} at {second.percent_dairy:.0f}%. {low.county} had the lowest share, "
                 f"at {low.percent_dairy:.0f}%.",
        data=d, figure=fig,
    ).write()


def organic_eu():
    df = eurostat.fetch("sdg_02_40", geo=EU_GEO)
    eu.rank_chart(
        "agriculture-organic-eu", TOPIC, "Organic farming across the EU",
        "Share of farmed land used for organic farming, EU countries, {year}.",
        Source.eurostat("sdg_02_40", "Area under organic farming"), df,
        lambda y, ie, ev, place: f"In {y}, {ie:.1f}% of farmed land in Ireland was organic or being converted to "
                                 f"organic. Ireland's share was {place}.",
        notes=["Includes land that is fully organic and land in the process of converting, which usually takes two "
               "to three years. Measured as a share of utilised agricultural area, the land used for crops, grassland "
               "and permanent crops such as orchards.",
               "Eurostat has not published an EU-wide figure for years after 2020."],
        suffix="%")


def livestock():
    df = cso.fetch("EIIA18")
    df = df[df["Statistic Label"] == "Farm Animals December"]
    names = {"Total cattle": "Cattle", "Total sheep": "Sheep", "Total pigs": "Pigs"}
    w = df.pivot_table(index="Year", columns="Type of Farm Animal", values="VALUE").rename(columns=names)
    w = (w[list(names.values())] / 1000).round(2).reset_index().rename(columns={"Year": "year"})
    w["year"] = w.year.astype(int)
    a, b = w.iloc[0], w.iloc[-1]
    peak = w.loc[w.Sheep.idxmax()]
    fig = figures.lines(w, "year", {c: c for c in names.values()}, colours=[style.INK, style.AQUA, style.ORANGE],
                        value_format=".1f", suffix="m", y_range=[0, None])
    Chart(
        id="agriculture-livestock", topic=TOPIC,
        title="Cattle, sheep and pigs",
        subtitle=f"Number of cattle, sheep and pigs on farms in Ireland in December, in millions, {a.year:.0f} to {b.year:.0f}.",
        sources=[Source.cso("EIIA18", "Ireland cattle, sheep and pigs December")],
        notes=["Counted in December each year. Numbers in June are higher, because of lambs and calves born in spring."],
        key_fact=f"There were {b.Cattle:.1f} million cattle on Irish farms in December {b.year:.0f}, compared with "
                 f"{a.Cattle:.1f} million in {a.year:.0f}. Sheep numbers peaked at {peak.Sheep:.1f} million in {peak.year:.0f}.",
        data=w, figure=fig,
    ).write()


def cows():
    df = cso.fetch("AAA06")
    names = {"Dairy cows": "Dairy cows", "Other cows": "Beef (suckler) cows"}
    w = df[df["Type of Animal"].isin(names)].pivot_table(index="Year", columns="Type of Animal", values="VALUE")
    w = (w.rename(columns=names)[list(names.values())] / 1000).round(2).reset_index().rename(columns={"Year": "year"})
    w["year"] = w.year.astype(int)
    a, b = w.iloc[0], w.iloc[-1]
    fig = figures.lines(w, "year", {c: c for c in names.values()}, colours=[style.BLUE, style.ORANGE],
                        value_format=".2f", suffix="m", y_range=[0, None])
    fig.update_layout(margin=dict(r=170))
    Chart(
        id="agriculture-cows", topic=TOPIC,
        title="Dairy and beef cows",
        subtitle=f"Number of dairy cows and other cows in Ireland in December, in millions, {a.year:.0f} to {b.year:.0f}.",
        sources=[Source.cso("AAA06", "Farm Animals in December")],
        notes=["Other cows are cows kept to rear calves for beef, often called suckler cows.",
               "EU milk quotas, which capped how much milk each country could produce, ended in April 2015."],
        key_fact=f"There were {b['Dairy cows']:.2f} million dairy cows in Ireland in December {b.year:.0f}, up from "
                 f"{a['Dairy cows']:.2f} million in {a.year:.0f}. Beef cows fell from {a['Beef (suckler) cows']:.2f} million "
                 f"to {b['Beef (suckler) cows']:.2f} million.",
        data=w, figure=fig,
    ).write()


def milk():
    df = cso.fetch("AKA01")
    df = df[(df["Statistic Label"] == "Intake of Cows Milk by Milk Processors and Co-Ops") &
            (df["Domestic or Import Source"] == "Domestic")]
    w = df[["Year", "VALUE"]].rename(columns={"Year": "year", "VALUE": "million_litres"})
    w["billion_litres"] = (w.million_litres / 1000).round(2)
    w["year"] = w.year.astype(int)
    a, b = w.iloc[0], w.iloc[-1]
    q = w.set_index("year").billion_litres
    fig = go.Figure(go.Bar(x=w.year, y=w.billion_litres, marker=dict(color=style.BLUE, cornerradius=2),
                           hovertemplate="<b>%{x}</b>: %{y:.2f} billion litres<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=56, r=16, t=8, b=32), bargap=0.2,
                                        xaxis=style.axis(), yaxis=style.value_axis(ticksuffix="bn")))
    Chart(
        id="agriculture-milk", topic=TOPIC,
        title="Milk from Irish farms",
        subtitle=f"Cows' milk taken in by dairies from farms in Ireland, in billions of litres, {a.year:.0f} to {b.year:.0f}.",
        sources=[Source.cso("AKA01", "Intake of Cows Milk by Milk Processors and Co-Ops")],
        notes=["Milk delivered by Irish farms to dairies and co-ops. Milk imported for processing is not included.",
               "EU milk quotas, which capped how much milk each country could produce, ended in April 2015."],
        key_fact=f"Irish dairies took in {b.billion_litres:.1f} billion litres of milk from Irish farms in {b.year:.0f}, "
                 f"compared with {q.loc[2014]:.1f} billion litres in 2014, the last full year of EU milk quotas.",
        data=w[["year", "million_litres"]], figure=fig,
    ).write()


def fertiliser():
    df = cso.fetch("PFSA01")
    names = {"Nitrogen (N) content of fertiliser sales": "Nitrogen",
             "Phosphorus (P) content of fertiliser sales": "Phosphorus",
             "Potassium (K) content of fertiliser sales": "Potassium"}
    w = df[df["Statistic Label"].isin(names)].pivot_table(index="Year", columns="Statistic Label", values="VALUE")
    w = (w.rename(columns=names)[list(names.values())] / 1000).round(1).reset_index().rename(columns={"Year": "year"})
    w["year"] = w.year.astype(int)
    a, b = w.iloc[0], w.iloc[-1]
    fig = figures.lines(w, "year", {c: c for c in names.values()}, colours=[style.BLUE, style.GOLD, style.PURPLE],
                        value_format=".0f", suffix="k", y_range=[0, None])
    Chart(
        id="agriculture-fertiliser", topic=TOPIC,
        title="Fertiliser sales",
        subtitle=f"Nitrogen, phosphorus and potassium in fertiliser sold in Ireland, in thousands of tonnes, "
                 f"{a.year:.0f} to {b.year:.0f}.",
        sources=[Source.cso("PFSA01", "Nutrient Content of Fertiliser Sales")],
        notes=["Measures the nutrients contained in the chemical fertiliser sold, not the total weight of fertiliser. "
               "Animal manure and slurry are not included."],
        key_fact=f"Fertiliser sold in Ireland in {b.year:.0f} contained {b.Nitrogen:.0f} thousand tonnes of nitrogen, "
                 f"compared with {a.Nitrogen:.0f} thousand tonnes in {a.year:.0f}.",
        data=w, figure=fig,
    ).write()


OUTPUT = {"Livestock - Cattle": "Cattle", "All Livestock Products - Milk": "Milk", "Livestock - Pig": "Pigs",
          "Livestock - Sheep": "Sheep", "Livestock - Poultry": "Poultry", "Livestock - Horses": "Horses",
          "All Livestock Products Other Products (excluding Milk)": "Eggs, wool and other animal products",
          "All Crops": "Crops"}


def _aea01():
    return cso.fetch("AEA01").pivot_table(index="Year", columns="Statistic Label", values="VALUE")


def output_mix():
    p = _aea01()
    year = int(p.index.max())
    r = p.loc[year]
    total = r["Goods Output at Producer Prices"]
    w = pd.DataFrame({"product": list(OUTPUT.values()), "euro_million": [r[k] for k in OUTPUT]})
    w["percent"] = (w.euro_million / total * 100).round(1)
    w = w.sort_values("percent", ascending=False)
    s = w.set_index("product").percent
    Chart(
        id="agriculture-output", topic=TOPIC, height=340,
        title="What Irish farms produce",
        subtitle=f"Value of goods produced by farms in Ireland, by product, as a share of the total, {year}.",
        sources=[Source.cso("AEA01", "Value at Current Prices for Output, Input and Income in Agriculture")],
        notes=["Valued at the prices farmers receive, before subsidies. Crops include cereals, potatoes, vegetables, "
               "fruit, mushrooms and the value of grass and other fodder grown. The data file has values in euro."],
        key_fact=f"Milk made up {s['Milk']:.0f}% of the value of goods produced by Irish farms in {year}, and cattle "
                 f"{s['Cattle']:.0f}%. Farms produced goods worth €{total / 1000:.1f} billion in total.",
        data=w, figure=hbars(w, "product", "percent", colour=style.AQUA),
    ).write()


def income():
    p = _aea01()
    w = (p[["Entrepreneurial Income"]] / 1000).round(2).reset_index().rename(columns={"Year": "year",
                                                                                     "Entrepreneurial Income": "income"})
    w["year"] = w.year.astype(int)
    a, b = w.iloc[0], w.iloc[-1]
    low = w.loc[w.income.idxmin()]
    fig = figures.lines(w, "year", {"income": "Farm income"}, colours=[style.AQUA], value_format=".1f", prefix="€",
                        suffix="bn", y_range=[0, None])
    Chart(
        id="agriculture-income", topic=TOPIC,
        title="Farm income",
        subtitle=f"Total income from farming in Ireland, in billions of euro at current prices, {a.year:.0f} to {b.year:.0f}.",
        sources=[Source.cso("AEA01", "Value at Current Prices for Output, Input and Income in Agriculture")],
        notes=["Entrepreneurial income: the value of what farms produce, plus subsidies, minus the cost of feed, "
               "fertiliser, energy and other inputs, depreciation, wages, rent and interest. It is the income left "
               "for farmers and their families, for all farms together.",
               "Figures are at current prices and are not adjusted for inflation. Recent years may be revised."],
        key_fact=f"Farm income in Ireland was €{b.income:.1f} billion in {b.year:.0f}, compared with €{a.income:.1f} billion "
                 f"in {a.year:.0f}. The lowest in the period was €{low.income:.1f} billion in {low.year:.0f}.",
        data=w, figure=fig,
    ).write()


WASTE = {"Primary production of food - agriculture, fishing and aquaculture (A1, A3)": "Farming and fishing",
         "Manufacture of food products and beverages (C10, C11)": "Food and drink manufacturing",
         "Retail and other distribution of food (G46, G47)": "Shops and distribution",
         "Restaurants and food services (I55, I56, N to S)": "Restaurants and food services",
         "Households (EP_HH)": "Households"}


def food_waste():
    df = cso.fetch("BIIESA08")
    year = int(df.Year.max())
    df = df[df.Year == year]
    p = df.pivot_table(index="NACE Rev 2 Sectors & Households", columns="Country", values="VALUE")
    p = p.rename(columns={"EU27 countries (from 2020)": "eu_average", "Ireland": "ireland"})
    total = p.loc["NACE activities plus households (TOTAL_HH)"]
    w = p.loc[list(WASTE)].rename(index=WASTE).rename_axis("stage").reset_index()[["stage", "ireland", "eu_average"]]
    hh = w.set_index("stage").loc["Households"]
    fig = go.Figure()
    for col, name, colour in [("ireland", "Ireland", style.AQUA), ("eu_average", "EU average", style.CONTEXT)]:
        fig.add_bar(y=w.stage, x=w[col], name=name, orientation="h", marker=dict(color=colour, cornerradius=3),
                    text=[f"{v:.0f}" for v in w[col]], textposition="outside", cliponaxis=False,
                    textfont=dict(color=style.INK, size=12),
                    hovertemplate=f"<b>%{{y}}</b><br>{name}: %{{x:.0f}} kg<extra></extra>")
    fig.update_layout(style.base_layout(margin=dict(l=8, r=40, t=40, b=32), bargap=0.3, bargroupgap=0.08,
                                        barmode="group", showlegend=True, legend=style.legend_top(),
                                        xaxis=style.value_axis(ticksuffix=" kg"),
                                        yaxis=style.axis(automargin=True, autorange="reversed",
                                                         tickfont=dict(color=style.INK_2, size=12))))
    Chart(
        id="agriculture-food-waste", topic=TOPIC, height=400,
        title="Food waste",
        subtitle=f"Food wasted per person in Ireland and the EU, in kilograms, by where it was wasted, {year}.",
        sources=[Source.cso("BIIESA08", "Food Waste per Capita")],
        notes=["Includes inedible parts such as bones and peelings, as well as food that could have been eaten.",
               "The figures are reported to Eurostat under EU rules on measuring food waste. The data file has the "
               f"total for all stages, which was {total.ireland:.0f} kg per person in Ireland and "
               f"{total.eu_average:.0f} kg across the EU."],
        key_fact=f"Ireland wasted {total.ireland:.0f} kg of food per person in {year}, compared with "
                 f"{total.eu_average:.0f} kg across the EU. Households wasted {hh.ireland:.0f} kg per person.",
        data=w, figure=fig,
    ).write()
