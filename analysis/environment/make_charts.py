"""Environment and climate charts: greenhouse gas emissions."""
from ibn import cso, figures, style
from ibn.chart import Chart, Source

TOPIC = "environment"
EU = "EU 27 Countries (from 2020)"

SECTORS = {
    "Agriculture": "Agriculture",
    "Transport": "Transport",
    "Energy Industries": "Energy industries",
    "Industry, Commercial and Public Services": "Industry and services",
    "Residential": "Homes",
    "Waste and F-Gases": "Waste and F-gases",
}


def build():
    by_sector()
    per_person()


def by_sector():
    df = cso.fetch("EIIA08")
    d = df.pivot_table(index="Year", columns="Sector", values="VALUE").reset_index()
    cols = {k: v.lower().replace(" ", "_").replace("-", "_") for k, v in SECTORS.items()}
    d = d.rename(columns={**cols, "All EPA inventory groups": "total"})
    for c in [*cols.values(), "total"]:
        d[c] = (d[c] / 1000).round(2)   # thousand tonnes to million tonnes
    d = d[["Year", *cols.values(), "total"]]
    d["Year"] = d.Year.astype(int)
    fig = figures.lines(d, "Year", {cols[k]: v for k, v in SECTORS.items()}, value_format=".1f", label_last=False,
                        y_range=[0, d[list(cols.values())].max().max() * 1.1], y_title="Million tonnes CO₂ equivalent")
    fig.update_layout(showlegend=True, legend=style.legend_top(), margin=dict(t=64, l=64))
    a, b = d.iloc[0], d.iloc[-1]
    peak = d.loc[d.total.idxmax()]
    Chart(
        id="environment-emissions-by-sector", topic=TOPIC,
        title="Greenhouse gas emissions by sector",
        subtitle=f"Ireland's greenhouse gas emissions in millions of tonnes of carbon dioxide equivalent, by sector, "
                 f"{d.Year.min()} to {d.Year.max()}.",
        sources=[Source.cso("EIIA08", "Ireland greenhouse gas emissions (Territorial Principle)")],
        notes=["The figures come from the national inventory compiled by the Environmental Protection Agency (EPA), as published "
               "by the CSO. They count emissions produced in Ireland, and do not include emissions or removals from land use and forestry.",
               "Gases other than carbon dioxide, such as methane from cattle, are converted to the amount of carbon dioxide "
               "that would warm the climate by the same amount. The data file also includes the total for all sectors."],
        key_fact=f"Ireland's greenhouse gas emissions were {b.total:.1f} million tonnes in {b.Year:.0f}, down from a peak of "
                 f"{peak.total:.1f} million tonnes in {peak.Year:.0f}. Agriculture was the largest source, at "
                 f"{b.agriculture / b.total * 100:.0f}% of the total.",
        data=d, figure=fig,
    ).write()


def per_person():
    df = cso.fetch("MIP07")
    d = df[df.Countries.isin(["Ireland", EU]) & (df["Statistic Label"] == "Green House Gas Emission Per Capita")]
    d = d.pivot_table(index="Year", columns="Countries", values="VALUE").reset_index()
    d = d.rename(columns={"Ireland": "ireland", EU: "eu_27"})[["Year", "ireland", "eu_27"]]
    d["Year"] = d.Year.astype(int)
    fig = figures.lines(d, "Year", {"ireland": "Ireland", "eu_27": "EU average"}, value_format=".1f",
                        colours=[style.BLUE, style.INK_3], y_range=[0, d[["ireland", "eu_27"]].max().max() * 1.15])
    y = d.iloc[-1]
    Chart(
        id="environment-emissions-per-person", topic=TOPIC,
        title="Emissions per person in Ireland and the EU",
        subtitle=f"Greenhouse gas emissions per person in tonnes of carbon dioxide equivalent, Ireland and the 27 EU countries, "
                 f"{d.Year.min()} to {d.Year.max()}.",
        sources=[Source.cso("MIP07", "Greenhouse Gas Emissions")],
        notes=["The CSO publishes these figures from Eurostat as part of its Measuring Ireland's Progress series, so they "
               "can differ slightly from the EPA's national inventory.",
               "The EU figure covers the 27 countries that have been members since 2020."],
        key_fact=f"In {y.Year:.0f}, emissions were {y.ireland:.1f} tonnes per person in Ireland, compared with an EU average "
                 f"of {y.eu_27:.1f} tonnes.",
        data=d, figure=fig,
    ).write()
