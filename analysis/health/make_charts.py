"""Health charts: life expectancy, causes of death, access and the health service."""
import pandas as pd

from ibn import cso, eu, eurostat, figures, style
from ibn.chart import Chart, Source
from ibn.counties import SUMMED_NOTE, add_up, county

TOPIC = "health"
EU = "EU 27 Countries (from 2020)"

EU_GEO = eurostat.EU27 + [eurostat.EU]


def build():
    life_expectancy()
    death_rates()
    distance_maps()
    trolleys()
    emergency_department_times()
    outpatient_waits()
    spending()
    eu_comparisons()


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
                        value_format=",.1f", label_last=True)
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


SERVICES = {"General Practitioner (GP)": ("gp", "a GP"), "HSE Emergency Department": ("emergency_department", "a hospital emergency department")}


def distance_maps():
    df = cso.fetch("MDSI05", where={"Statistic Label": ["Median Distance of Persons in Residential Dwellings to Services"],
                                    "Type of Service": list(SERVICES)})
    year = int(df.Year.max())
    state = df[df.County == "Ireland"].set_index("Type of Service")["VALUE"]
    df["county"] = df.County.map(county)
    df = df.dropna(subset=["county"])
    for service, (slug, words) in SERVICES.items():
        d = df[df["Type of Service"] == service][["county", "VALUE"]].rename(columns={"VALUE": "median_distance_km"})
        d = d.sort_values("county").reset_index(drop=True)
        fig = figures.county_map(d, "county", "median_distance_km", value_format=".1f", suffix=" km",
                                 legend_title=f"Median distance to {words.split(' ', 1)[1]} (km)")
        hi, lo = d.loc[d.median_distance_km.idxmax()], d.loc[d.median_distance_km.idxmin()]
        Chart(
            id=f"health-distance-{slug.replace('_', '-')}-map", topic=TOPIC, kind="map", height=600,
            title=f"Distance to {words.split(' ', 1)[1]} by county",
            subtitle=f"Median distance by road from people's homes to the nearest {words.split(' ', 1)[1]}, in kilometres, {year}.",
            sources=[Source.cso("MDSI05", "Average distance to the nearest service for individuals and households by County")],
            notes=["The CSO measures the distance along the road network from each home to the nearest service, weighted by "
                   "the number of people living there. Half of people in each county live closer than the median distance "
                   "and half live further away.",
                   "Emergency departments are those in HSE hospitals. Injury units, which treat less serious injuries, are not included."
                   if slug == "emergency_department" else
                   "The distance is to the nearest GP practice, which may not be taking new patients."],
            key_fact=f"In {year}, half of people in {hi.county} lived more than {hi.median_distance_km:.1f} km by road from "
                     f"{words}, the furthest of any county, compared with {state[service]:.1f} km across the State.",
            data=d, figure=fig,
        ).write()


def _months(series, fmt="%Y %B"):
    return pd.to_datetime(series, format=fmt)


def trolleys():
    df = cso.fetch("KTA02")
    d = df[df["Statistic Label"].str.startswith("Admitted")].copy()
    d["day"] = _months(d.Day, "%Y %B %d")
    d["month"] = d.day.dt.to_period("M").dt.to_timestamp()
    m = d.groupby("month").VALUE.mean().round(0).astype(int).rename("average_daily_count").reset_index()
    fig = figures.lines(m, "month", {"average_daily_count": "Patients on trolleys"}, hover_x="%B %Y",
                        y_range=[0, m.average_daily_count.max() * 1.1])
    y = d.groupby(d.day.dt.year).VALUE.mean()
    last, peak = int(y.index.max()), int(y.idxmax())
    worst = d.loc[d.VALUE.idxmax()]
    Chart(
        id="health-trolleys", topic=TOPIC,
        title="Patients waiting on trolleys",
        subtitle=f"Average number of admitted patients waiting on trolleys in public hospital emergency departments at "
                 f"8am each day, by month, {m.month.min():%B %Y} to {m.month.max():%B %Y}.",
        sources=[Source.cso("KTA02", "Admitted Patients Waiting on Trolleys in Public Acute Hospital Emergency Departments at 8 am")],
        notes=["Counts patients who have been admitted to hospital but are still waiting in the emergency department "
               "for a bed, at 8am each day. The Department of Health publishes these figures, from HSE data, in its "
               "Health in Ireland key trends.",
               "The Irish Nurses and Midwives Organisation publishes its own daily count, which is usually higher "
               "because it also includes patients on trolleys elsewhere in the hospital."],
        key_fact=f"On an average morning in {last}, {y[last]:.0f} admitted patients were waiting on trolleys in emergency "
                 f"departments. The highest single count was {worst.VALUE:.0f}, on {worst.day:%-d %B %Y}.",
        data=m, figure=fig,
    ).write()


def emergency_department_times():
    df = cso.fetch("KTA03")
    d = df.pivot_table(index="Month", columns="Percentile", values="VALUE").reset_index()
    d["month"] = _months(d.Month)
    d = d.sort_values("month")
    d["median_hours"] = (d["50th percentile"] / 60).round(1)
    d["longest_5pc_hours"] = (d["95th percentile"] / 60).round(1)
    d = d[["month", "median_hours", "longest_5pc_hours"]].reset_index(drop=True)
    fig = figures.lines(d, "month", {"median_hours": "Half", "longest_5pc_hours": "95%"},
                        value_format=".1f", suffix=" hours", hover_x="%B %Y", y_range=[0, d.longest_5pc_hours.max() * 1.1])
    a = d[d.month.dt.year == d.month.dt.year.min()]
    b = d[d.month.dt.year == d.month.dt.year.max()]
    Chart(
        id="health-ed-times", topic=TOPIC,
        title="Time spent in emergency departments",
        subtitle=f"Hours within which half of patients, and 95% of patients, left a public hospital emergency "
                 f"department after arriving, by month, "
                 f"{d.month.min():%B %Y} to {d.month.max():%B %Y}.",
        sources=[Source.cso("KTA03", "Patient experience time in emergency departments")],
        notes=["Patient experience time runs from registration in the emergency department until the patient leaves it, "
               "either to go home or to a hospital bed.",
               "The lower line is the median: half of patients left within this time. The upper line is the 95th "
               "percentile: 95% of patients left within this time, and 5% stayed longer."],
        key_fact=f"In {b.month.dt.year.iloc[0]}, half of patients left the emergency department within "
                 f"{b.median_hours.mean():.1f} hours, but one in twenty spent more than {b.longest_5pc_hours.mean():.0f} hours there.",
        data=d, figure=fig,
    ).write()


def outpatient_waits():
    df = cso.fetch("HSPAN16")
    d = df[df["Waiting Times"] == "Waiting times less than 15 months"].copy()
    d["month"] = _months(d.Month)
    d = d.sort_values("month").rename(columns={"VALUE": "percent_under_15_months"})[["month", "percent_under_15_months"]]
    d = d.dropna().reset_index(drop=True)
    fig = figures.lines(d, "month", {"percent_under_15_months": "Waiting under 15 months"}, value_format=".0f", suffix="%",
                        hover_x="%B %Y", y_range=[0, 100])
    a, b = d.iloc[0], d.iloc[-1]
    Chart(
        id="health-outpatient-waits", topic=TOPIC,
        title="Outpatient waiting times",
        subtitle=f"Percentage of people on the hospital outpatient waiting list who had been waiting less than 15 months, "
                 f"{a.month:%B %Y} to {b.month:%B %Y}.",
        sources=[Source.cso("HSPAN16", "Outpatient waiting times")],
        notes=["An outpatient appointment is a first appointment with a hospital consultant, usually after a GP referral. "
               "The Sláintecare target is that no one waits more than 10 weeks.",
               "The CSO publishes these figures, from the National Treatment Purchase Fund, as part of the Department of "
               "Health's health system performance assessment. The series ends in September 2024. The National Treatment "
               "Purchase Fund publishes more recent monthly waiting list figures on its own website."],
        key_fact=f"In {b.month:%B %Y}, {b.percent_under_15_months:.0f}% of people on the outpatient waiting list had been "
                 f"waiting less than 15 months, up from {a.percent_under_15_months:.0f}% in {a.month:%B %Y}.",
        data=d, figure=fig,
    ).write()


def spending():
    df = cso.fetch("SHA07")
    df["Statistic Label"] = df["Statistic Label"].str.strip()
    d = df.pivot_table(index="Year", columns="Statistic Label", values="VALUE").reset_index()
    d = d.rename(columns={"Current Public Expenditure": "public", "Current Private Expenditure": "private",
                          "Current Expenditure": "total", "Current Expenditure GNI*": "percent_of_gni_star"})
    for c in ["public", "private", "total"]:
        d[c] = (d[c] / 1000).round(2)
    d["Year"] = d.Year.astype(int)
    d["percent_of_gni_star"] = d.percent_of_gni_star.round(1)
    d = d[["Year", "public", "private", "total", "percent_of_gni_star"]]
    fig = figures.lines(d, "Year", {"public": "Public", "private": "Private"}, value_format=".1f", prefix="€", suffix="bn",
                        y_range=[0, d.public.max() * 1.1])
    a, b = d.iloc[0], d.iloc[-1]
    Chart(
        id="health-spending", topic=TOPIC,
        title="Spending on health care",
        subtitle=f"Current spending on health care in Ireland, by the State and by households and insurers, € billion, "
                 f"{a.Year:.0f} to {b.Year:.0f}.",
        sources=[Source.cso("SHA07", "Revised Health Care Expenditure")],
        notes=["Current spending covers the day-to-day cost of health care, such as staff, medicines and treatment. It "
               "does not include capital spending on buildings and equipment.",
               "Public spending is by the State, mainly through the HSE. Private spending is by households, health "
               "insurers and others, including out-of-pocket payments such as GP fees.",
               "Figures are in current prices, not adjusted for inflation. The data file also gives total spending as a "
               "percentage of GNI*, a measure of the size of the Irish economy."],
        key_fact=f"Current spending on health care was €{b.total:.1f} billion in {b.Year:.0f}, of which €{b.public:.1f} billion "
                 f"({b.public / b.total * 100:.0f}%) was public. That was {b.percent_of_gni_star:.1f}% of GNI*.",
        data=d, figure=fig,
    ).write()


def eu_comparisons():
    df = eurostat.fetch("hlth_sha11_hf", geo=EU_GEO, icha11_hf="TOT_HF", unit="PPS_HAB")
    eu.rank_chart(
        "health-spending-eu", TOPIC, "Health spending across the EU",
        "Current spending on health care per person, public and private, adjusted for price levels, EU countries, {year}.",
        Source.eurostat("hlth_sha11_hf", "Health care expenditure by financing scheme"), df,
        lambda y, ie, ev, place: f"In {y}, health spending per person in Ireland, adjusted for price levels, was "
                                 f"{ie / ev * 100 - 100:.0f}% above the EU average, {place}." if ev else
                                 f"In {y}, health spending per person in Ireland, adjusted for price levels, was {place}.",
        notes=["Figures are in purchasing power standards (PPS), an artificial currency that adjusts for differences in "
               "price levels between countries, so the amounts are not euro. Covers spending by the State, health "
               "insurance and people themselves, but not investment in buildings and equipment."],
        value_format=",.0f")
