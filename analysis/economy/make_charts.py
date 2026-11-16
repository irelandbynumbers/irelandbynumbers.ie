"""Economy and work charts: unemployment and national income."""
import pandas as pd

from ibn import cso, figures, style
from ibn.chart import Chart, Source
from ibn.counties import SUMMED_NOTE, add_up, county
from ibn.facts import higher_lower

TOPIC = "economy"


def build():
    unemployment()
    gdp_gni()
    earnings()
    income_map()
    work_from_home_map()
    car_to_work_map()


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
