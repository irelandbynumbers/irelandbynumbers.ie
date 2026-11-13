"""Economy and work charts: unemployment and national income."""
import pandas as pd

from ibn import cso, figures, style
from ibn.chart import Chart, Source

TOPIC = "economy"


def build():
    unemployment()
    gdp_gni()
    earnings()


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
    Chart(
        id="economy-gdp-gni", topic=TOPIC,
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
    Chart(
        id="economy-earnings", topic=TOPIC,
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
