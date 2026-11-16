"""Population charts, from CSO population estimates and the census."""
import pandas as pd
import plotly.graph_objects as go

from ibn import cso, eu, eurostat, figures, style
from ibn.chart import Chart, Source
from ibn.facts import millions, pct_change

TOPIC = "population"

EU_GEO = eurostat.EU27 + [eurostat.EU]


def build():
    population_total()
    population_change()
    county_map()
    age_shares()
    births_deaths()
    fertility()
    marriages()
    marriage_ceremonies()
    eu_comparisons()


def population_total():
    df = cso.fetch("PEA01")
    d = df[(df["Age Group"] == "All ages") & (df["Sex"] == "Both sexes")]
    d = d[["Year", "VALUE"]].rename(columns={"VALUE": "population"})
    d["population"] = (d["population"] * 1000).round().astype(int)   # published in thousands
    first, last = d.iloc[0], d.iloc[-1]
    ten = d[d.Year == last.Year - 10].iloc[0]
    Chart(
        id="population-total", topic=TOPIC,
        key_fact=f"An estimated {millions(last.population)} people lived in the State in April {last.Year}, "
                 f"{pct_change(last.population, ten.population)} on {ten.Year}.",
        title="Population of Ireland",
        subtitle=f"Estimated number of people living in the State each April, {first.Year} to {last.Year}.",
        sources=[Source.cso("PEA01", "Population Estimates (Persons in April)")],
        notes=["The CSO counts the population in each census and estimates it for the years in between, "
               "using births, deaths and estimated migration. Estimates are revised after each new census.",
               "Figures are published rounded to the nearest hundred people."],
        data=d, figure=figures.lines(d, "Year", {"population": "Population"}, y_range=[0, d.population.max() * 1.08]),
    ).write()


def population_change():
    df = cso.fetch("PEA15")
    wide = df.pivot_table(index="Year", columns="Component", values="VALUE").reset_index()
    d = wide[["Year", "Annual births", "Annual deaths", "Net migration"]].copy()
    d.columns = ["Year", "births", "deaths", "net_migration"]
    d = d.dropna().reset_index(drop=True)   # births and deaths start later than migration
    for c in ["births", "deaths", "net_migration"]:
        d[c] = (d[c] * 1000).round().astype(int)
    fig = figures.lines(d, "Year", {"births": "Births", "deaths": "Deaths", "net_migration": "Net migration"},
                        colours=[style.BLUE, style.INK_3, style.ORANGE], label_last=False)
    fig.update_layout(showlegend=True, legend=style.legend_top(), margin=dict(t=40))
    fig.add_hline(y=0, line=dict(color=style.INK_3, width=1))
    y = d.iloc[-1]
    migration = (f"net migration added {y.net_migration:,} people" if y.net_migration >= 0
                 else f"net migration reduced the population by {-y.net_migration:,}")
    Chart(
        id="population-change", topic=TOPIC,
        key_fact=f"In the twelve months to April {y.Year} there were {y.births:,} births and {y.deaths:,} deaths, "
                 f"and {migration}.",
        title="Births, deaths and migration",
        subtitle=f"People born, people who died, and net migration (people arriving minus people leaving) "
                 f"in the twelve months to April, {d.Year.min()} to {d.Year.max()}.",
        sources=[Source.cso("PEA15", "Annual Population Change")],
        notes=["Each year runs from May to the following April. Migration is estimated, not counted, "
               "and the estimates are revised after each census.",
               "A negative net migration figure means more people emigrated than immigrated that year."],
        data=d, figure=fig,
    ).write()


def county_map():
    df = cso.fetch("F1001")
    d = df[(df["Sex"] == "Both sexes") & (df["County"].isin(figures.COUNTIES))]
    d = d[["CensusYear", "County", "VALUE"]].rename(columns={"CensusYear": "census_year", "County": "county", "VALUE": "population"})
    base = d[d.census_year == 1841].set_index("county")["population"]
    d["percent_of_1841"] = (d["population"] / d["county"].map(base) * 100).round(1)
    d = d.sort_values(["census_year", "county"]).reset_index(drop=True)
    latest = d.census_year.max()
    # Colour runs from far below 1841 (orange) through 100% (neutral) to above it (blue).
    fig = figures.county_map(d[["census_year", "county", "percent_of_1841", "population"]], "county", "percent_of_1841",
                             time="census_year", colorscale=style.DIVERGING, value_format=".0f", suffix="%",
                             legend_title="% of 1841 population", zmin=0, zmax=200,
                             hover_extra="Population %{customdata[3]:,}")
    fewer = int((d[d.census_year == latest].percent_of_1841 < 100).sum())
    Chart(
        id="population-county-map", topic=TOPIC, kind="map", height=640,
        key_fact=f"At the {latest} census, {fewer} of the 26 counties had fewer people than in 1841.",
        title="County populations since 1841",
        subtitle=f"Population of each county at each census from 1841 to {latest}, as a percentage of its 1841 population. "
                 "Use the slider to move through the census years.",
        sources=[Source.cso("F1001", "Population at Each Census")],
        notes=["100% means a county had the same population as in 1841, the last census before the Great Famine. "
               "Counties above 200% are shown in the darkest blue. In 2022 these were Dublin and Kildare."],
        data=d, figure=fig,
    ).write()


def age_shares():
    df = cso.fetch("PEA01")
    d = df[df["Sex"] == "Both sexes"].pivot_table(index="Year", columns="Age Group", values="VALUE").reset_index()
    out = d[["Year"]].copy()
    out["under_15"] = (d["0 - 14 years"] / d["All ages"] * 100).round(1)
    out["aged_65_plus"] = (d["65 years and over"] / d["All ages"] * 100).round(1)
    fig = figures.lines(out, "Year", {"under_15": "Children under 15", "aged_65_plus": "People aged 65 and over"},
                        value_format=".1f", suffix="%", y_range=[0, 35], label_last=False)
    fig.update_layout(showlegend=True, legend=style.legend_top(), margin=dict(t=40))
    a, b = out.iloc[0], out.iloc[-1]
    Chart(
        id="population-ageing", topic=TOPIC,
        key_fact=f"People aged 65 and over made up {b.aged_65_plus:.1f}% of the population in {b.Year:.0f}, "
                 f"compared with {a.aged_65_plus:.1f}% in {a.Year:.0f}.",
        title="Children and older people as a share of the population",
        subtitle=f"Percentage of the population aged under 15 and aged 65 and over, {out.Year.min()} to {out.Year.max()}.",
        sources=[Source.cso("PEA01", "Population Estimates (Persons in April)")],
        notes=["Calculated from the CSO's estimates of the population by age in April of each year."],
        data=out, figure=fig,
    ).write()


REGISTERED = ("Births, deaths and marriages are counted in the year they are registered, which is usually soon after "
              "they happen. Figures for the latest year are provisional and can be revised.")


def births_deaths():
    df = cso.fetch("VSA03")
    d = df.pivot_table(index="Year", columns="Statistic Label", values="VALUE").reset_index()
    d = d.rename(columns={"Births Registered": "births", "Deaths Registered": "deaths"})[["Year", "births", "deaths"]]
    d = d.dropna().astype(int)
    d["natural_increase"] = d.births - d.deaths
    fig = figures.lines(d, "Year", {"births": "Births", "deaths": "Deaths"}, colours=[style.BLUE, style.INK_3],
                        y_range=[0, d.births.max() * 1.1])
    peak = d.loc[d.births.idxmax()]
    b = d.iloc[-1]
    Chart(
        id="population-births-deaths", topic=TOPIC,
        title="Births and deaths",
        subtitle=f"Number of births and deaths registered in Ireland each year, {d.Year.min()} to {b.Year}.",
        sources=[Source.cso("VSA03", "Total Births and Deaths Registered Numbers and Rates")],
        notes=[REGISTERED,
               "The gap between the two lines is the natural increase, the number of births minus the number of deaths. "
               "It is given in the data file. Population change also depends on migration."],
        key_fact=f"{b.births:,} births and {b.deaths:,} deaths were registered in {b.Year}. Births peaked at "
                 f"{peak.births:,} in {peak.Year}.",
        data=d, figure=fig,
    ).write()


def fertility():
    df = cso.fetch("VSA104")
    d = df[(df["NUTS 3 Region"] == "Ireland") & (df["Age Group"] == "All ages")
           & (df["Statistic Label"] == "Total period of fertility rate")].dropna(subset=["VALUE"])
    d = d[["Year", "VALUE"]].rename(columns={"VALUE": "fertility_rate"})
    d["Year"] = d.Year.astype(int)
    fig = figures.lines(d, "Year", {"fertility_rate": "Fertility rate"}, value_format=".2f", y_range=[0, 4.2])
    fig.add_hline(y=2.1, line=dict(color=style.INK_3, width=1, dash="dot"),
                  annotation=dict(text="Replacement level, 2.1", font=dict(color=style.INK_3, size=11)),
                  annotation_position="top right")
    a, b = d.iloc[0], d.iloc[-1]
    below = d[d.fertility_rate >= 2.1].Year.max()
    Chart(
        id="population-fertility", topic=TOPIC,
        title="Fertility rate",
        subtitle=f"Average number of children a woman would have over her lifetime at each year's birth rates, "
                 f"{a.Year:.0f} to {b.Year:.0f}.",
        sources=[Source.cso("VSA104", "Fertility Rates")],
        notes=["The total fertility rate adds up the birth rates of women at each age in a year. It is the number of "
               "children a woman would have on average if those rates stayed the same throughout her life.",
               "A rate of about 2.1 is known as replacement level, the rate at which a population would replace itself "
               "from one generation to the next without migration."],
        key_fact=f"Ireland's fertility rate was {b.fertility_rate:.2f} in {b.Year:.0f}, down from {a.fertility_rate:.2f} in "
                 f"{a.Year:.0f}. It was last at or above replacement level, 2.1, in {below:.0f}.",
        data=d, figure=fig,
    ).write()


def marriages():
    opposite = cso.fetch("VSA46")
    opposite = opposite[(opposite["Day of Occurence"] == "All days") & (opposite["Month of Occurrence"] == "All months")]
    same = cso.fetch("VSB12")
    same = same[(same["Day of Occurence"] == "All days") & (same["Month of Occurrence"] == "All months")]
    d = pd.concat([opposite.set_index("Year").VALUE.rename("opposite_sex"), same.set_index("Year").VALUE.rename("same_sex")],
                  axis=1).fillna(0).astype(int).reset_index()
    d["total"] = d.opposite_sex + d.same_sex
    fig = figures.lines(d, "Year", {"total": "Marriages"}, y_range=[0, d.total.max() * 1.1])
    low = d.loc[d.total.idxmin()]
    b = d.iloc[-1]
    Chart(
        id="population-marriages", topic=TOPIC,
        title="Marriages",
        subtitle=f"Number of marriages registered in Ireland each year, {d.Year.min()} to {b.Year}.",
        sources=[Source.cso("VSA46", "Opposite-Sex Marriages Registered"), Source.cso("VSB12", "Same-Sex Marriages Registered")],
        notes=[REGISTERED,
               "Same-sex marriage became legal in Ireland in November 2015. The data file gives opposite-sex and "
               "same-sex marriages separately."],
        key_fact=f"{b.total:,} marriages were registered in {b.Year}, including {b.same_sex:,} same-sex marriages. The "
                 f"lowest number was {low.total:,}, in {low.Year}.",
        data=d, figure=fig,
    ).write()


def marriage_ceremonies():
    df = cso.fetch("VSA44")
    d = df[df["Province County and City"] == "State"].pivot_table(index="Year", columns="Form of Ceremony", values="VALUE").fillna(0)
    total = d["All ceremonies"]
    out = pd.DataFrame({
        "Year": d.index.astype(int),
        "roman_catholic": (d["Roman Catholic"] / total * 100).round(1).values,
        "civil": (d["Civil marriages"] / total * 100).round(1).values,
        "other": ((total - d["Roman Catholic"] - d["Civil marriages"]) / total * 100).round(1).values,
    })
    fig = figures.lines(out, "Year", {"roman_catholic": "Catholic", "civil": "Civil", "other": "Other ceremonies"},
                        value_format=".0f", suffix="%", y_range=[0, 100], colours=[style.BLUE, style.ORANGE, style.AQUA])
    a, b = out.iloc[0], out.iloc[-1]
    Chart(
        id="population-marriage-ceremonies", topic=TOPIC,
        title="How couples marry",
        subtitle=f"Percentage of opposite-sex marriages by type of ceremony, {a.Year:.0f} to {b.Year:.0f}.",
        sources=[Source.cso("VSA44", "Opposite-Sex Marriages Registered")],
        notes=[REGISTERED,
               "Other ceremonies include those by other churches and religions, and by bodies such as the Humanist "
               "Association of Ireland and the Spiritualist Union of Ireland, which the CSO has counted separately "
               "since 2014. The CSO publishes this breakdown for opposite-sex marriages only."],
        key_fact=f"In {b.Year:.0f}, {b.roman_catholic:.0f}% of opposite-sex marriages were Catholic ceremonies, down from "
                 f"{a.roman_catholic:.0f}% in {a.Year:.0f}. {b.civil:.0f}% were civil ceremonies.",
        data=out, figure=fig,
    ).write()


def eu_comparisons():
    df = eurostat.fetch("demo_find", geo=EU_GEO, indic_de="TOTFERRT")
    eu.rank_chart(
        "population-fertility-eu", TOPIC, "Fertility rates across the EU",
        "Total fertility rate, average number of children per woman, EU countries, {year}.",
        Source.eurostat("demo_find", "Fertility indicators"), df,
        lambda y, ie, ev, place: f"Ireland's fertility rate was {ie:.2f} children per woman in {y}, {place}.",
        notes=["The total fertility rate is the average number of children a woman would have if she had children at "
               "the rates seen at each age in that year."],
        value_format=".2f")
