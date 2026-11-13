"""Population charts, from CSO population estimates and the census."""
import plotly.graph_objects as go

from ibn import cso, figures, style
from ibn.chart import Chart, Source

TOPIC = "population"


def build():
    population_total()
    population_change()
    county_map()
    age_shares()


def population_total():
    df = cso.fetch("PEA01")
    d = df[(df["Age Group"] == "All ages") & (df["Sex"] == "Both sexes")]
    d = d[["Year", "VALUE"]].rename(columns={"VALUE": "population"})
    d["population"] = (d["population"] * 1000).round().astype(int)   # published in thousands
    first, last = d.iloc[0], d.iloc[-1]
    Chart(
        id="population-total", topic=TOPIC,
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
    Chart(
        id="population-change", topic=TOPIC,
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
    Chart(
        id="population-county-map", topic=TOPIC, kind="map", height=640,
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
    Chart(
        id="population-ageing", topic=TOPIC,
        title="Children and older people as a share of the population",
        subtitle=f"Percentage of the population aged under 15 and aged 65 and over, {out.Year.min()} to {out.Year.max()}.",
        sources=[Source.cso("PEA01", "Population Estimates (Persons in April)")],
        notes=["Calculated from the CSO's estimates of the population by age in April of each year."],
        data=out, figure=fig,
    ).write()
