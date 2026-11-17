"""Poverty and inequality charts: poverty and deprivation rates, who is most
affected, child poverty, and income inequality, with EU comparisons."""
import plotly.graph_objects as go

from ibn import cso, eu, eurostat, figures, style
from ibn.chart import Chart, Source
from ibn import charts

TOPIC = "poverty"
EU_GEO = eurostat.EU27 + [eurostat.EU]
YEAR_NOTE = "From the CSO's Survey on Income and Living Conditions (SILC). These CSO tables start in 2020."
MEASURES = {"At Risk of Poverty Rate": "At risk of poverty", "Enforced Deprivation Rate": "Deprivation",
            "Consistent Poverty Rate": "Consistent poverty"}
MEASURES_NOTE = ("At risk of poverty means a household income, adjusted for household size, below 60% of the national "
                 "median. Deprivation means being unable to afford two or more of eleven basic items, such as a warm "
                 "waterproof coat or keeping the home adequately warm. Consistent poverty means both at the same time.")
LOW_INCOME = "Children below 60% median equivalised net administrative income"
LOW_INCOME_NOTE = ("A child is counted as living in a low-income household if the household's income, adjusted for its "
                   "size, is below 60% of the national median. Income is measured from administrative records, such "
                   "as tax and social welfare data, rather than from a survey.")
LOW_INCOME_SOURCE = "Children aged under 18 living in low-income households"


def build():
    rates()
    social_transfers()
    by_age()
    by_household()
    by_work()
    child_rates()
    child_low_income_map()
    child_low_income_by_family()
    child_low_income_by_work()
    child_poverty_eu()
    inequality()
    inequality_eu()


def _measures(df, group_col=None, year=None):
    d = df[df["Statistic Label"].isin(MEASURES)].copy()
    d["measure"] = d["Statistic Label"].map(MEASURES)
    if year:
        d = d[d.Year == year]
    return d


def grouped(d, label, cols, value_format=".1f", suffix="%"):
    fig = go.Figure()
    for col, colour in zip(cols, [style.BLUE, style.ORANGE, style.AQUA]):
        fig.add_trace(go.Bar(y=d[label], x=d[col], name=col, orientation="h", marker=dict(color=colour, cornerradius=3),
                             text=[f"{format(v, value_format)}{suffix}" for v in d[col]], textposition="outside",
                             cliponaxis=False, textfont=dict(color=style.INK_2, size=11),
                             hovertemplate=f"<b>%{{y}}</b>, {col}: %{{x:{value_format}}}{suffix}<extra></extra>"))
    fig.update_layout(style.base_layout(
        barmode="group", bargap=0.25, bargroupgap=0.05, showlegend=True,
        legend=dict(style.legend_top(), traceorder="normal"), margin=dict(l=8, r=48, t=40, b=32),
        xaxis=style.value_axis(ticksuffix=suffix),
        yaxis=style.axis(automargin=True, autorange="reversed", tickfont=dict(color=style.INK_2, size=12))))
    return fig


def rates():
    df = cso.fetch("SIA77")
    names = {"At Risk of Poverty Rate: 60% Median Income Threshold": "At risk of poverty",
             "Enforced Deprivation Rate": "Deprivation",
             "Consistent Poverty Rate (60% Median Income Threshold)": "Consistent poverty"}
    d = df[df["Statistic Label"].isin(names)].assign(measure=lambda x: x["Statistic Label"].map(names))
    w = d.pivot_table(index="Year", columns="measure", values="VALUE").reset_index().rename(columns={"Year": "year"})
    w["year"] = w.year.astype(int)
    w = w[["year", "At risk of poverty", "Deprivation", "Consistent poverty"]]
    b = w.iloc[-1]
    fig = figures.lines(w, "year", {c: c for c in w.columns[1:]}, value_format=".1f", suffix="%",
                        y_range=[0, w.iloc[:, 1:].max().max() * 1.2])
    fig.update_layout(margin=dict(r=170))
    Chart(
        id="poverty-rates", topic=TOPIC,
        title="Poverty and deprivation",
        subtitle=f"Share of people at risk of poverty, experiencing deprivation, and in consistent poverty, "
                 f"{w.year.iloc[0]} to {b.year:.0f}.",
        sources=[Source.cso("SIA77", "Key national indicators of poverty, deprivation and social exclusion")],
        notes=[MEASURES_NOTE, YEAR_NOTE],
        key_fact=f"In {b.year:.0f}, {b['At risk of poverty']:.1f}% of people in Ireland were at risk of poverty, "
                 f"{b['Deprivation']:.1f}% experienced deprivation and {b['Consistent poverty']:.1f}% were in consistent "
                 f"poverty.",
        data=w, figure=fig,
    ).write()


def social_transfers():
    df = cso.fetch("SIA77")
    year = int(df.Year.max())
    r = df[df.Year == year].set_index("Statistic Label").VALUE
    before = r["At Risk of Poverty Rate: Excluding All Social Transfers (60% Median Income Threshold)"]
    after = r["At Risk of Poverty Rate: 60% Median Income Threshold"]
    import pandas as pd
    d = pd.DataFrame({"income": ["Before social welfare payments", "After social welfare payments"],
                      "percent_at_risk_of_poverty": [before, after]})
    Chart(
        id="poverty-social-transfers", topic=TOPIC, height=240,
        title="Poverty before and after social welfare",
        subtitle=f"Share of people at risk of poverty, counting income before and after social welfare payments, {year}.",
        sources=[Source.cso("SIA77", "Key national indicators of poverty, deprivation and social exclusion")],
        notes=["Social welfare payments here are all social transfers, as the CSO defines them.", YEAR_NOTE],
        key_fact=f"In {year}, {before:.1f}% of people would have been at risk of poverty without social welfare "
                 f"payments, compared with {after:.1f}% after them.",
        data=d, figure=charts.hbars(d, "income", "percent_at_risk_of_poverty", ".1f"),
    ).write()


def _by(code, col, labels, year=None):
    df = cso.fetch(code)
    year = year or int(df.Year.max())
    d = _measures(df, year=year)
    w = d.pivot_table(index=col, columns="measure", values="VALUE").reindex(list(labels)).rename(index=labels)
    return year, w.rename_axis("group").reset_index()[["group", "At risk of poverty", "Deprivation", "Consistent poverty"]]


def by_age():
    labels = {"0 - 17 years": "Under 18", "18 - 34 years": "18 to 34", "35 - 49 years": "35 to 49",
              "50 - 64 years": "50 to 64", "65 years and over": "65 and over"}
    year, d = _by("SIA61", "Age Group", labels)
    r = d.set_index("group")
    Chart(
        id="poverty-by-age", topic=TOPIC, height=460,
        title="Poverty and deprivation by age",
        subtitle=f"Share of people at risk of poverty, experiencing deprivation, and in consistent poverty, by age, {year}.",
        sources=[Source.cso("SIA61", "Income, poverty and deprivation rates, by age group")],
        notes=[MEASURES_NOTE, YEAR_NOTE],
        key_fact=f"In {year}, {r.loc['65 and over', 'At risk of poverty']:.1f}% of people aged 65 and over were at risk "
                 f"of poverty, and {r.loc['Under 18', 'At risk of poverty']:.1f}% of children.",
        data=d, figure=grouped(d, "group", ["At risk of poverty", "Deprivation", "Consistent poverty"]),
    ).write()


def by_household():
    labels = {"1 adult, with children under 18 years": "One adult with children",
              "1 adult aged 65 years and over": "One adult, 65 or over",
              "1 adult aged less than 65 years": "One adult, under 65",
              "Other households with children under 18 years": "Other households with children",
              "2 adults, with 1-3 children under 18 years": "Two adults with 1 to 3 children",
              "2 adults, at least 1 aged 65 years and over": "Two adults, one or both 65 or over",
              "2 adults, both aged less than 65 years": "Two adults, both under 65",
              "3 or more adults": "Three or more adults"}
    year, d = _by("SIA64", "Household Composition", labels)
    r = d.set_index("group")
    Chart(
        id="poverty-by-household", topic=TOPIC, height=640,
        title="Poverty and deprivation by type of household",
        subtitle=f"Share of people at risk of poverty, experiencing deprivation, and in consistent poverty, by type of "
                 f"household, {year}.",
        sources=[Source.cso("SIA64", "Income, poverty and deprivation rates, by household composition")],
        notes=[MEASURES_NOTE, YEAR_NOTE],
        key_fact=f"In {year}, {r.loc['One adult with children', 'Deprivation']:.1f}% of people in one-parent households "
                 f"experienced deprivation, compared with {r.loc['Two adults with 1 to 3 children', 'Deprivation']:.1f}% "
                 f"in households of two adults with one to three children.",
        data=d, figure=grouped(d, "group", ["At risk of poverty", "Deprivation", "Consistent poverty"]),
    ).write()


def by_work():
    labels = {"Unemployed": "Unemployed", "Unable to work due to long-standing health problems": "Unable to work due to illness",
              "Fulfilling domestic tasks": "Looking after the home", "Student, pupil": "Student",
              "Retired": "Retired", "Employed": "In work"}
    year, d = _by("SIA62", "Principal Economic Status", labels)
    r = d.set_index("group")
    Chart(
        id="poverty-by-work", topic=TOPIC, height=560,
        title="Poverty and deprivation by work status",
        subtitle=f"Share of people aged 16 and over at risk of poverty, experiencing deprivation, and in consistent "
                 f"poverty, by main economic status, {year}.",
        sources=[Source.cso("SIA62", "Income, poverty and deprivation rates, by principal economic status")],
        notes=[MEASURES_NOTE, "Each person is counted under the activity they say is their main one.", YEAR_NOTE],
        key_fact=f"In {year}, {r.loc['Unemployed', 'At risk of poverty']:.1f}% of unemployed people were at risk of "
                 f"poverty, compared with {r.loc['In work', 'At risk of poverty']:.1f}% of people in work.",
        data=d, figure=grouped(d, "group", ["At risk of poverty", "Deprivation", "Consistent poverty"]),
    ).write()


def child_rates():
    df = cso.fetch("SIA61")
    d = _measures(df)
    d = d[d["Age Group"] == "0 - 17 years"]
    w = d.pivot_table(index="Year", columns="measure", values="VALUE").reset_index().rename(columns={"Year": "year"})
    w["year"] = w.year.astype(int)
    w = w[["year", "At risk of poverty", "Deprivation", "Consistent poverty"]]
    b = w.iloc[-1]
    fig = figures.lines(w, "year", {c: c for c in w.columns[1:]}, value_format=".1f", suffix="%",
                        y_range=[0, w.iloc[:, 1:].max().max() * 1.2])
    fig.update_layout(margin=dict(r=170))
    Chart(
        id="poverty-child-rates", topic=TOPIC,
        title="Child poverty and deprivation",
        subtitle=f"Share of children aged under 18 at risk of poverty, experiencing deprivation, and in consistent "
                 f"poverty, {w.year.iloc[0]} to {b.year:.0f}.",
        sources=[Source.cso("SIA61", "Income, poverty and deprivation rates, by age group")],
        notes=[MEASURES_NOTE, YEAR_NOTE],
        key_fact=f"In {b.year:.0f}, {b['At risk of poverty']:.1f}% of children were at risk of poverty, "
                 f"{b['Deprivation']:.1f}% experienced deprivation and {b['Consistent poverty']:.1f}% were in consistent "
                 f"poverty.",
        data=w, figure=fig,
    ).write()

def child_low_income_map():
    df = cso.fetch("CCLIH03")
    df = df[df["Statistic Label"] == LOW_INCOME]
    state = float(df[df.County == "Ireland"].VALUE.iloc[0])
    d = df[df.County != "Ireland"].assign(county=lambda x: x.County.str.replace("Co. ", "", regex=False))
    d = d[["county", "VALUE"]].rename(columns={"VALUE": "percent"})
    fig = figures.county_map(d, "county", "percent", value_format=".1f", suffix="%",
                             legend_title="Children in low-income households")
    d = d.sort_values("percent", ascending=False).reset_index(drop=True)
    hi, lo = d.iloc[0], d.iloc[-1]
    Chart(
        id="poverty-child-low-income-map", topic=TOPIC, kind="map", height=560,
        title="Children in low-income households by county",
        subtitle="Share of children aged under 18 living in a household with income below 60% of the national median, "
                 "by county, 2022.",
        sources=[Source.cso("CCLIH03", LOW_INCOME_SOURCE)],
        notes=[LOW_INCOME_NOTE],
        key_fact=f"In 2022, {state:.1f}% of children in Ireland lived in low-income households. The share ranged from "
                 f"{hi.percent:.1f}% in {hi.county} to {lo.percent:.1f}% in {lo.county}.",
        data=d, figure=fig,
    ).write()

def child_low_income_by_family():
    df = cso.fetch("CCLIH09")
    df = df[(df["Number of Children"] == "All households with children") & (df["Statistic Label"] == LOW_INCOME)]
    labels = {"Married couple with children": "Married couple", "Cohabiting couple with children": "Cohabiting couple",
              "One parent mother with children": "One parent, mother", "One parent father with children": "One parent, father",
              "All family units": "All families"}
    d = df.assign(family=df["Type of Family Unit"].map(labels))[["family", "VALUE"]].rename(columns={"VALUE": "percent"})
    r = d.set_index("family").percent
    Chart(
        id="poverty-child-low-income-by-family", topic=TOPIC, height=320,
        title="Children in low-income households by type of family",
        subtitle="Share of children aged under 18 living in a low-income household, by type of family, 2022.",
        sources=[Source.cso("CCLIH09", LOW_INCOME_SOURCE)],
        notes=[LOW_INCOME_NOTE],
        key_fact=f"In 2022, {r['One parent, mother']:.0f}% of children living with a lone mother and "
                 f"{r['One parent, father']:.0f}% of those living with a lone father were in low-income households, "
                 f"compared with {r['Married couple']:.0f}% of children of married couples.",
        data=d, figure=charts.hbars(d, "family", "percent"),
    ).write()

def child_low_income_by_work():
    df = cso.fetch("CCLIH11")
    df = df[(df["Number of children"] == "All households with children") & (df["Type of Family Unit"] == "All family units")
            & (df["Statistic Label"] == LOW_INCOME)]
    col = "Number of working parents in household"
    order = ["No parent at work", "One parent at work", "Two parents at work"]
    d = df.set_index(col).VALUE.loc[order].rename("percent").rename_axis("parents_at_work").reset_index()
    r = d.set_index("parents_at_work").percent
    Chart(
        id="poverty-child-low-income-by-work", topic=TOPIC, height=280,
        title="Children in low-income households by parents' work",
        subtitle="Share of children aged under 18 living in a low-income household, by how many parents are at work, 2022.",
        sources=[Source.cso("CCLIH11", LOW_INCOME_SOURCE)],
        notes=[LOW_INCOME_NOTE, "Children living with one parent can only be in the first two groups."],
        key_fact=f"In 2022, {r['No parent at work']:.0f}% of children in households where no parent was at work lived on "
                 f"a low income, compared with {r['Two parents at work']:.0f}% where two parents were at work.",
        data=d, figure=charts.hbars(d, "parents_at_work", "percent"),
    ).write()

def child_poverty_eu():
    df = eurostat.fetch("ilc_peps01n", name="ilc_peps01n_children", geo=EU_GEO, age="Y_LT18", sex="T", unit="PC")
    eu.rank_chart(
        "poverty-child-eu", TOPIC, "Children at risk of poverty or social exclusion across the EU",
        "Share of children aged under 18 at risk of poverty or social exclusion, EU countries, {year}.",
        Source.eurostat("ilc_peps01n", "Persons at risk of poverty or social exclusion", name="ilc_peps01n_children"), df,
        lambda y, ie, ev, place: f"In {y}, {ie:.1f}% of children in Ireland were at risk of poverty or social exclusion, "
                                 f"compared with {ev:.1f}% across the EU. Ireland's rate was {place}.",
        notes=["Children are counted if their household income is below 60% of the national median, if the household "
               "cannot afford a number of basic items or activities, or if the adults in it work very little. This is a "
               "survey measure, so it differs from the CSO's count of children in low-income households."],
        suffix="%", higher_is="highest")



def inequality():
    df = cso.fetch("SIA75")
    names = {"Gini Coefficient (Ratio) - Equivalised Market Income": "Before tax and social welfare",
             "Gini Coefficient (Ratio) - Equivalised Disposable Income": "After tax and social welfare"}
    d = df[df["Statistic Label"].isin(names)].assign(measure=lambda x: x["Statistic Label"].map(names))
    w = d.pivot_table(index="Year", columns="measure", values="VALUE").reset_index().rename(columns={"Year": "year"})
    w["year"] = w.year.astype(int)
    cols = list(names.values())
    w = w[["year"] + cols]
    scale = 100 if w[cols].max().max() <= 1 else 1
    w[cols] = (w[cols] * scale).round(1)
    b = w.iloc[-1]
    fig = figures.lines(w, "year", {c: c for c in cols}, colours=[style.CONTEXT, style.BLUE], value_format=".1f",
                        y_range=[0, w[cols].max().max() * 1.2])
    fig.update_layout(margin=dict(r=210))
    Chart(
        id="poverty-inequality", topic=TOPIC,
        title="Income inequality before and after tax and social welfare",
        subtitle=f"Gini coefficient of household income, adjusted for household size, {w.year.iloc[0]} to {b.year:.0f}.",
        sources=[Source.cso("SIA75", "Income inequality rates")],
        notes=["The Gini coefficient measures how evenly income is shared. It would be 0 if every household had the "
               "same income and 100 if one household had all of it.",
               "Income before tax and social welfare is market income, from work, investments and private pensions. "
               "Income after is disposable income.", YEAR_NOTE],
        key_fact=f"In {b.year:.0f}, the Gini coefficient for household income was {b[cols[0]]:.1f} before tax and "
                 f"social welfare and {b[cols[1]]:.1f} after them.",
        data=w, figure=fig,
    ).write()


def inequality_eu():
    df = eurostat.fetch("ilc_di12", geo=EU_GEO, age="TOTAL")
    eu.rank_chart(
        "poverty-inequality-eu", TOPIC, "Income inequality across the EU",
        "Gini coefficient of disposable household income, EU countries, {year}.",
        Source.eurostat("ilc_di12", "Gini coefficient of equivalised disposable income"), df,
        lambda y, ie, ev, place: f"In {y}, Ireland's Gini coefficient for disposable income was {ie:.1f}, compared "
                                 f"with {ev:.1f} for the EU as a whole. It was {place}.",
        notes=["The Gini coefficient measures how evenly income is shared after tax and social welfare. It would be 0 "
               "if every household had the same income and 100 if one household had all of it. Eurostat's figure for "
               "Ireland can differ slightly from the CSO's."],
        value_format=".1f")
