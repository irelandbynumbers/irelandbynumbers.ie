"""Health charts: life expectancy and causes of death."""
from ibn import cso, figures, style
from ibn.chart import Chart, Source

TOPIC = "health"
EU = "EU 27 Countries (from 2020)"


def build():
    life_expectancy()
    death_rates()


def life_expectancy():
    df = cso.fetch("MIP12")
    d = df[df.Countries.isin(["Ireland", EU]) & (df.Sex == "Total Persons")]
    d = d.pivot_table(index="Year", columns="Countries", values="VALUE").reset_index()
    d = d.rename(columns={"Ireland": "ireland", EU: "eu_27"})[["Year", "ireland", "eu_27"]]
    d["Year"] = d.Year.astype(int)
    fig = figures.lines(d, "Year", {"ireland": "Ireland", "eu_27": "EU average"}, value_format=".1f",
                        colours=[style.BLUE, style.INK_3], y_range=[70, 90])
    fig.update_xaxes(dtick=1)
    y = d.iloc[-1]
    Chart(
        id="health-life-expectancy", topic=TOPIC,
        title="Life expectancy in Ireland and the EU",
        subtitle=f"Life expectancy at birth in years, Ireland and the 27 EU countries, {d.Year.min()} to {d.Year.max()}.",
        sources=[Source.cso("MIP12", "Life expectancy at birth (Years)")],
        notes=["Life expectancy at birth is how long a baby born that year would live on average if death rates at each age "
               "stayed as they were that year. It is a summary of death rates, not a forecast.",
               "The CSO publishes these figures from Eurostat as part of its Measuring Ireland's Progress series. "
               "The EU figure covers the 27 countries that have been members since 2020."],
        key_fact=f"Life expectancy at birth in Ireland was {y.ireland:.1f} years in {y.Year:.0f}, compared with an EU average "
                 f"of {y.eu_27:.1f} years.",
        data=d, figure=fig,
    ).write()


def death_rates():
    df = cso.fetch("VSD56")
    d = df[(df.Sex == "All sexes") & (df["Statistic Label"] == "Death rate per 100,000 persons")]
    d = d.pivot_table(index="Year", columns="Cause of Death", values="VALUE").reset_index()
    d = d.rename(columns={"Heart disease deaths": "heart_disease", "Cancer deaths": "cancer",
                          "Tuberculosis deaths": "tuberculosis", "All causes of death": "all_causes"})
    d = d[["Year", "heart_disease", "cancer", "tuberculosis", "all_causes"]]
    d["Year"] = d.Year.astype(int)
    fig = figures.lines(d, "Year", {"heart_disease": "Heart disease", "cancer": "Cancer", "tuberculosis": "Tuberculosis"},
                        value_format=",.0f", label_last=True)
    a, b = d.iloc[0], d.iloc[-1]
    # The first year from which cancer has had the higher death rate every year since.
    behind = d[d.cancer <= d.heart_disease].Year
    since = int(behind.max()) + 1 if len(behind) else int(d.Year.min())
    Chart(
        id="health-death-rates", topic=TOPIC,
        title="Deaths from heart disease, cancer and tuberculosis",
        subtitle=f"Deaths per 100,000 people each year from heart disease, cancer and tuberculosis, {d.Year.min()} to {d.Year.max()}.",
        sources=[Source.cso("VSD56", "Deaths Occurring")],
        notes=["These are crude death rates, the number of deaths divided by the population. They are not adjusted for age, "
               "so part of the change over time comes from the population getting older.",
               "Causes of death are as recorded on death certificates, and the way causes are classified has changed several "
               "times since 1922. The data file also includes the rate for all causes of death."],
        key_fact=(f"The death rate from tuberculosis fell from {a.tuberculosis:,.0f} per 100,000 people in {a.Year:.0f} to "
                  f"{b.tuberculosis:.1f} in {b.Year:.0f}." + (f" Cancer has caused more deaths than heart disease in every year since {since}."
                  if since <= d.Year.max() else "")),
        data=d, figure=fig,
    ).write()
