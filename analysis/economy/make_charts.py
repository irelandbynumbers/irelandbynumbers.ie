"""Economy and work charts: unemployment and national income."""
import pandas as pd
import plotly.graph_objects as go

from ibn import cso, eu, eurostat, figures, ni, style
from ibn.chart import Chart, Source
from ibn.counties import SUMMED_NOTE, add_up, county
from ibn.facts import higher_lower

TOPIC = "economy"

EU_GEO = eurostat.EU27 + [eurostat.EU]


def build():
    unemployment()
    gdp_gni()
    earnings()
    income_map()
    work_from_home_map()
    car_to_work_map()
    eu_comparisons()
    ni_comparisons()


def unemployment():
    df = cso.fetch("MUM01")
    d = df[(df["Statistic Label"] == "Seasonally Adjusted Monthly Unemployment Rate") & (df["Sex"] == "Both sexes")]
    d = d.pivot_table(index="Month", columns="Age Group", values="VALUE", sort=False).reset_index()
    d.insert(0, "date", pd.to_datetime(d["Month"], format="%Y %B"))
    d = d.drop(columns="Month").sort_values("date").reset_index(drop=True)
    d = d.rename(columns={"15 - 74 years": "aged_15_74", "15 - 24 years": "aged_15_24", "25 - 74 years": "aged_25_74"})
    d = d[["date", "aged_15_74", "aged_15_24"]]
    d["date"] = d["date"].dt.strftime("%Y-%m")
    fig = figures.lines(d, "date", {"aged_15_74": "All aged 15 to 74", "aged_15_24": "Aged 15 to 24"},
                        value_format=".1f", suffix="%", hover_x="%B %Y", y_range=[0, d.aged_15_24.max() * 1.05])
    first = pd.to_datetime(d.date.iloc[0]).strftime("%B %Y")
    latest = pd.to_datetime(d.date.iloc[-1]).strftime("%B %Y")
    Chart(
        id="economy-unemployment", topic=TOPIC,
        key_fact=f"The unemployment rate was {d.aged_15_74.iloc[-1]:.1f}% in {latest}, seasonally adjusted.",
        title="Unemployment rate",
        subtitle=f"Percentage of people in the labour force who are unemployed, seasonally adjusted, {first} to {latest}.",
        sources=[Source.cso("MUM01", "Seasonally Adjusted Monthly Unemployment")],
        notes=["A person is unemployed if they are without work, available to start within two weeks, and have looked for work "
               "in the past four weeks. The rate is the number unemployed as a share of everyone working or looking for work.",
               "Monthly figures are estimates based on the Labour Force Survey and are revised as new survey results come in."],
        data=d, figure=fig,
    ).write()


def gdp_gni():
    df = cso.fetch("NA001")
    keep = {"1. Gross domestic product at current market prices - ESA code (B.1*g)": "gdp",
            "10. Modified gross national income at current market prices": "gni_star"}
    d = df[df["Item"].isin(keep)].pivot_table(index="Year", columns="Item", values="VALUE").reset_index()
    d = d.rename(columns=keep)
    d["gdp"] = (d["gdp"] / 1000).round(1)          # € million to € billion
    d["gni_star"] = (d["gni_star"] / 1000).round(1)
    d = d[["Year", "gdp", "gni_star"]]
    fig = figures.lines(d, "Year", {"gdp": "GDP", "gni_star": "GNI*"}, value_format=",.0f", prefix="€", suffix="bn",
                        y_range=[0, d.gdp.max() * 1.08])
    y = d.iloc[-1]
    Chart(
        id="economy-gdp-gni", topic=TOPIC,
        key_fact=f"In {y.Year:.0f}, GNI* was €{y.gni_star:,.0f} billion, {y.gni_star / y.gdp * 100:.0f}% of GDP.",
        title="GDP and modified gross national income",
        subtitle=f"Gross domestic product (GDP) and modified gross national income (GNI*) in billions of euro at current prices, "
                 f"{d.Year.min()} to {d.Year.max()}.",
        sources=[Source.cso("NA001", "Modified Gross National Income at Current Market Prices")],
        notes=["GDP measures the value of everything produced in Ireland. Because a number of large multinational companies "
               "record intellectual property, aircraft leasing and profits here, GDP overstates the income available to people living in Ireland.",
               "GNI* removes the profits of companies that moved their headquarters to Ireland, and the depreciation of "
               "intellectual property and leased aircraft owned by foreign companies here. The CSO introduced it in 2017 as a better measure of the domestic economy.",
               "Figures are at current prices, so they are not adjusted for inflation."],
        data=d, figure=fig,
    ).write()


def earnings():
    """Average weekly earnings, in cash terms and adjusted for consumer prices."""
    weekly = "Average Weekly Earnings"
    df = cso.fetch("EHQ03", where={"Statistic Label": [weekly], "Economic Sector NACE Rev 2": ["All NACE economic sectors"],
                                   "Type of Employee": ["All employees"]})
    d = df[["Quarter", "VALUE"]].rename(columns={"Quarter": "quarter", "VALUE": "weekly_earnings"}).dropna()
    # Adjust for inflation with the CPI averaged over each quarter, in prices of the latest quarter.
    cpi = cso.fetch("CPM20", where={"Statistic Label": ["Consumer Price Index (Base Month December 2023 = 100)",
                                                        "Percentage change over 12 months for Consumer Price Index"]})
    cpi = cpi[(cpi["Commodity Group"] == "All Items") &
              (cpi["Statistic Label"] == "Consumer Price Index (Base Month December 2023 = 100)")].copy()
    cpi["quarter"] = pd.to_datetime(cpi["Month"], format="%Y %B").dt.to_period("Q").astype(str)
    q = cpi.groupby("quarter")["VALUE"].agg(["mean", "count"])
    q = q[q["count"] == 3]["mean"]
    d = d[d.quarter.isin(q.index)].copy()
    latest = d.quarter.iloc[-1]
    d["weekly_earnings"] = d["weekly_earnings"].round(2)
    d[f"in_{latest}_prices"] = (d["weekly_earnings"] * q[latest] / d.quarter.map(q)).round(2)
    d["date"] = pd.PeriodIndex(d.quarter, freq="Q").to_timestamp().strftime("%Y-%m")
    d = d[["quarter", "date", "weekly_earnings", f"in_{latest}_prices"]].reset_index(drop=True)
    fig = figures.lines(d, "date", {"weekly_earnings": "In cash terms", f"in_{latest}_prices": f"Adjusted for prices"},
                        value_format=",.0f", prefix="€", y_range=[0, d.weekly_earnings.max() * 1.1], label_last=False)
    fig.update_layout(showlegend=True, legend=style.legend_top(), margin=dict(t=40))
    for tr in fig.data:
        tr.customdata = d.quarter
    label = latest.replace("Q", " Q")
    now, year_ago = d.iloc[-1], d.iloc[-5]
    real = f"in_{latest}_prices"
    Chart(
        id="economy-earnings", topic=TOPIC,
        key_fact=f"Average weekly earnings were €{now.weekly_earnings:,.0f} in {label}, "
                 f"{higher_lower((now.weekly_earnings / year_ago.weekly_earnings - 1) * 100)} than a year earlier, "
                 f"or {higher_lower((now[real] / year_ago[real] - 1) * 100)} after adjusting for prices.",
        title="Average weekly earnings",
        subtitle=f"Average weekly earnings of employees, in cash terms and adjusted for consumer prices "
                 f"(in {label} prices), {d.quarter.iloc[0].replace('Q', ' Q')} to {label}.",
        sources=[Source.cso("EHQ03", "Average Earnings, Hours Worked, Employment and Labour Costs"),
                 Source.cso("CPM20", "Consumer Price Index")],
        notes=["Earnings are gross, before tax, and include irregular payments such as bonuses. They cover all employees, "
               "full-time and part-time, so changes in the mix of jobs and hours also move the average.",
               f"The price-adjusted line uses the Consumer Price Index averaged over each quarter, so every figure is shown in {label} prices.",
               "Figures are not seasonally adjusted, so some of the movement from quarter to quarter is seasonal."],
        data=d, figure=fig,
    ).write()


def income_map():
    df = cso.fetch("RAA02", where={"Statistic Label": ["Disposable Income per Person"]})
    d = df.copy()
    d["county"] = d["County"].map(county)
    d = d.dropna(subset=["county"])
    d = d[["Year", "county", "VALUE"]].rename(columns={"Year": "year", "VALUE": "disposable_income_per_person"})
    d["disposable_income_per_person"] = d.disposable_income_per_person.round().astype(int)
    d = d.sort_values(["year", "county"]).reset_index(drop=True)
    state = df[df.County == "Ireland"].set_index("Year")["VALUE"]
    fig = figures.county_map(d, "county", "disposable_income_per_person", time="year",
                             legend_title="Disposable income per person (€)")
    fig.data[1].hovertemplate = "<b>%{location}</b><br>€%{z:,.0f} a year<extra></extra>"
    for fr in fig.frames:
        fr.data[1].hovertemplate = fig.data[1].hovertemplate
    y = d[d.year == d.year.max()].sort_values("disposable_income_per_person")
    lo, hi = y.iloc[0], y.iloc[-1]
    Chart(
        id="economy-income-map", topic=TOPIC, kind="map", height=640,
        title="Disposable income per person by county",
        subtitle=f"Average household disposable income per person in each county, in euro at current prices, "
                 f"{d.year.min()} to {d.year.max()}. Use the slider to move through the years.",
        sources=[Source.cso("RAA02", "Estimates of Household Income")],
        notes=["Disposable income is household income from work, self-employment, rent, interest, dividends and social welfare, "
               "after income tax and social contributions, divided by the number of people living in the county. "
               "It is counted where people live, not where they work.",
               "Figures are not adjusted for inflation or for differences in the cost of living between counties."],
        key_fact=f"In {hi.year}, disposable income per person ranged from €{lo.disposable_income_per_person:,} in {lo.county} "
                 f"to €{hi.disposable_income_per_person:,} in {hi.county}, compared with €{state[hi.year]:,.0f} for the State.",
        data=d, figure=fig,
    ).write()


def work_from_home_map():
    df = cso.fetch("SAP2022T11T4CTY")
    area = next(c for c in df.columns if c.startswith("Administrative Counties"))
    d = df.pivot_table(index=area, columns="Working From Home", values="VALUE", aggfunc="sum").reset_index()
    d = d.rename(columns={"Persons who work from home": "work_from_home", "Persons who never work from home": "never"})
    d = add_up(d, area, ["work_from_home", "never"])
    d["people_at_work_answering"] = d.work_from_home + d.never
    d["percent_work_from_home"] = (d.work_from_home / d.people_at_work_answering * 100).round(1)
    fig = figures.county_map(d, "county", "percent_work_from_home", value_format=".1f", suffix="%",
                             legend_title="% of people at work who work from home at least some of the time")
    hi, lo = d.loc[d.percent_work_from_home.idxmax()], d.loc[d.percent_work_from_home.idxmin()]
    Chart(
        id="economy-work-from-home-map", topic=TOPIC, kind="map", height=600,
        title="Working from home by county",
        subtitle="Percentage of people at work who said they worked from home for at least part of the week, Census 2022.",
        sources=[Source.cso("SAP2022T11T4CTY", "Census 2022 Small Area Population Statistics, working from home")],
        notes=["The census asked people at work whether they worked from home, and if so on how many days a week. "
               "This map counts everyone who worked from home on at least one day. People who did not answer are "
               "left out of the total.", SUMMED_NOTE],
        key_fact=f"At the 2022 census, {hi.percent_work_from_home:.0f}% of people at work in {hi.county} worked from home "
                 f"for at least part of the week, the highest share of any county, compared with {lo.percent_work_from_home:.0f}% in {lo.county}.",
        data=d[["county", "work_from_home", "people_at_work_answering", "percent_work_from_home"]], figure=fig,
    ).write()


def car_to_work_map():
    df = cso.fetch("SAP2022T11T1CTY", where={"Statistic Label": ["Usually resident by means of travel to work"]})
    area = next(c for c in df.columns if c.startswith("Administrative Counties"))
    d = df.pivot_table(index=area, columns="Means of Travel", values="VALUE", aggfunc="sum").reset_index()
    d["car"] = d["Car Driver"] + d["Car passenger"]
    d["travelling"] = d["Total"] - d["Work mainly at or from home"] - d["Not stated"]
    d = add_up(d, area, ["car", "travelling"])
    d["percent_by_car"] = (d.car / d.travelling * 100).round(1)
    fig = figures.county_map(d, "county", "percent_by_car", value_format=".0f", suffix="%",
                             legend_title="% of people travelling to work who go by car")
    hi, lo = d.loc[d.percent_by_car.idxmax()], d.loc[d.percent_by_car.idxmin()]
    Chart(
        id="economy-car-to-work-map", topic=TOPIC, kind="map", height=600,
        title="Driving to work by county",
        subtitle="Percentage of people travelling to work who went by car, as a driver or passenger, Census 2022.",
        sources=[Source.cso("SAP2022T11T1CTY", "Census 2022 Small Area Population Statistics, means of travel to work")],
        notes=["The census asks how each person usually travels the longest part of their journey to work. People who work "
               "mainly at or from home, and people who did not answer, are left out of the total.", SUMMED_NOTE],
        key_fact=f"At the 2022 census, {hi.percent_by_car:.0f}% of people travelling to work in {hi.county} went by car, "
                 f"the highest share of any county. The lowest was {lo.county}, at {lo.percent_by_car:.0f}%.",
        data=d[["county", "car", "travelling", "percent_by_car"]], figure=fig,
    ).write()


def eu_comparisons():
    df = eurostat.fetch("une_rt_a", geo=EU_GEO, age="Y15-74", sex="T", unit="PC_ACT")
    eu.lines_chart(
        "economy-unemployment-eu", TOPIC, "Unemployment in Ireland and the EU",
        "Unemployment rate, people aged 15 to 74, % of the labour force, {first} to {last}.",
        Source.eurostat("une_rt_a", "Unemployment by sex and age, annual data"), df,
        lambda w: f"Ireland's unemployment rate was {w.ireland.iloc[-1]:.1f}% in {w.year.iloc[-1]}, compared with "
                  f"{w.eu_average.iloc[-1]:.1f}% across the EU. Its highest since {w.year.iloc[0]} was {w.ireland.max():.1f}%, "
                  f"in {w.loc[w.ireland.idxmax(), 'year']}.",
        notes=["Measured the same way in every country, from each country's Labour Force Survey. Figures for Ireland "
               "can differ slightly from the CSO's own monthly estimates."],
        suffix="%", y_range=[0, None])
    df = eurostat.fetch("prc_ppp_ind", name="prc_ppp_ind_aic", geo=EU_GEO,
                        na_item=["VI_PPS_EU27_2020_HAB", "PLI_EU27_2020"], ppp_cat=["A01", "GDP"])
    aic = df[(df.na_item == "VI_PPS_EU27_2020_HAB") & (df.ppp_cat == "A01")]
    eu.rank_chart(
        "economy-consumption-per-head-eu", TOPIC, "Living standards across the EU",
        "Actual individual consumption per person, adjusted for price levels, EU average = 100, {year}.",
        Source.eurostat("prc_ppp_ind", "Purchasing power adjusted GDP per capita and related indicators", "prc_ppp_ind_aic"),
        aic, lambda y, ie, ev, place: f"In {y}, consumption per person in Ireland, adjusted for prices, was {ie:.0f}% of "
                                      f"the EU average, {place}.",
        notes=["Actual individual consumption is the value of the goods and services people use, whether they pay for "
               "them themselves or the State provides them, such as health care and education. Eurostat suggests it as a "
               "better guide to material living standards than GDP per person, which for Ireland is inflated by the "
               "profits of multinational companies.",
               "Figures are adjusted for differences in price levels between countries, using purchasing power standards."],
        value_format=".0f")
    df = eurostat.fetch("ilc_peps01n", geo=EU_GEO, age="TOTAL", sex="T", unit="PC")
    eu.rank_chart(
        "economy-poverty-eu", TOPIC, "Risk of poverty or social exclusion across the EU",
        "Share of people at risk of poverty or social exclusion, EU countries, {year}.",
        Source.eurostat("ilc_peps01n", "Persons at risk of poverty or social exclusion"), df,
        lambda y, ie, ev, place: f"In {y}, {ie:.1f}% of people in Ireland were at risk of poverty or social exclusion, "
                                 f"compared with {ev:.1f}% across the EU. Ireland's rate was {place}.",
        notes=["People are counted if their household income is below 60% of the national median, if they cannot "
               "afford a number of basic items or activities, or if they live in a household where adults work very "
               "little. Each country's poverty line is relative to its own median income."],
        suffix="%")


def ni_comparisons():
    df = cso.fetch("INIJEPA01")
    area = "County and Local Government District (LGD)"
    d = df[(df["Statistic Label"] == "Gross Disposable Household Income per Person") & df[area].isin([ni.IE, ni.NI])]
    d = d.pivot_table(index="Year", columns=area, values="VALUE").rename(columns={ni.IE: "ireland", ni.NI: "northern_ireland"})
    d = d.reset_index().round(0)
    d["Year"] = d.Year.astype(int)
    a, b = d.iloc[0], d.iloc[-1]
    gap = (b.ireland / b.northern_ireland - 1) * 100
    Chart(
        id="economy-ni-income", topic=TOPIC,
        title="Household income in Ireland and Northern Ireland",
        subtitle=f"Gross disposable household income per person, adjusted for price levels, {a.Year:.0f} to {b.Year:.0f}.",
        sources=[Source.cso("INIJEPA01", "Gross disposable household income in purchasing power standards, Ireland and "
                                          "Northern Ireland")],
        notes=[ni.STATE_NOTE, "Disposable income is what households have to spend or save after taxes, including "
               "social welfare payments. It is shown in purchasing power standards (PPS), which adjust for the "
               "different price levels in the two jurisdictions, so the amounts are not euro or sterling.",
               "From a joint CSO and NISRA publication that measures the two in the same way."],
        key_fact=f"In {b.Year:.0f}, disposable household income per person, adjusted for prices, was {gap:.0f}% higher in "
                 f"Ireland than in Northern Ireland.",
        data=d, figure=ni.lines(d, "Year", value_format=",.0f", y_range=[0, d.ireland.max() * 1.1]),
    ).write()

    to_ni = cso.fetch("CPNI40")
    to_ie = cso.fetch("CPNI46")
    rows = []
    for name, t in [("Living in Ireland, working in Northern Ireland", to_ni), ("Living in Northern Ireland, working in Ireland", to_ie)]:
        t = t[t.Sex == "Both sexes"]
        for _, r in t.iterrows():
            rows.append(dict(direction=name, age_group=r["Age Group"], people=int(r.VALUE)))
    d = pd.DataFrame(rows)
    tot = d.groupby("direction", sort=False).people.sum().reset_index()
    fig = go.Figure(go.Bar(y=tot.direction, x=tot.people, orientation="h", marker=dict(color=[ni.COLOURS[ni.IE], ni.COLOURS[ni.NI]],
                    cornerradius=4), text=[f"{v:,}" for v in tot.people], textposition="outside", cliponaxis=False,
                    textfont=dict(color=style.INK, size=13), hovertemplate="<b>%{y}</b>: %{x:,}<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=72, t=8, b=32), bargap=0.4, xaxis=style.value_axis(),
                                        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=12))))
    t = tot.set_index("direction").people
    Chart(
        id="economy-ni-cross-border-commuters", topic=TOPIC, height=260,
        title="Cross-border commuters",
        subtitle="People aged 16 and over who live on one side of the border and work on the other, census 2022 in "
                 "Ireland and 2021 in Northern Ireland.",
        sources=[Source.cso("CPNI40", "Commuters from Ireland to Northern Ireland"),
                 Source.cso("CPNI46", "Commuters from Northern Ireland to Ireland")],
        notes=[ni.CENSUS_NOTE, "Commuters living in Ireland are counted in Ireland's census, and commuters living in "
               "Northern Ireland in Northern Ireland's. The data file breaks each down by age."],
        key_fact=f"{t.iloc[1]:,} people living in Northern Ireland worked in Ireland, and {t.iloc[0]:,} living in Ireland "
                 f"worked in Northern Ireland, at the most recent censuses.",
        data=d, figure=fig,
    ).write()
