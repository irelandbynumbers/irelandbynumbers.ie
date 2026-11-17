"""Gender equality charts: the EU Gender Equality Index, the gender pay gap,
employment, unpaid care, top earners, and women in the Dáil and in business
leadership. Figures only, with no view on targets or policy."""
import pandas as pd
import plotly.graph_objects as go

from ibn import cso, eu, eurostat, figures, style
from ibn.chart import Chart, Source
from ibn.charts import hbars

from gender import violence

TOPIC = "gender"
EU_GEO = eurostat.EU27 + [eurostat.EU]
WOMEN, MEN = "Women", "Men"
CODES = {"Austria": "AT", "Belgium": "BE", "Bulgaria": "BG", "Croatia": "HR", "Cyprus": "CY", "Czechia": "CZ",
         "Denmark": "DK", "Estonia": "EE", "Finland": "FI", "France": "FR", "Germany": "DE", "Greece": "EL",
         "Hungary": "HU", "Ireland": "IE", "Italy": "IT", "Latvia": "LV", "Lithuania": "LT", "Luxembourg": "LU",
         "Malta": "MT", "Netherlands (the)": "NL", "Poland": "PL", "Portugal": "PT", "Romania": "RO",
         "Slovakia": "SK", "Slovenia": "SI", "Spain": "ES", "Sweden": "SE", "EU27 countries (from 2020)": eurostat.EU}
INDEX_SOURCE = "Gender Equality Index (European Institute for Gender Equality)"
INDEX_NOTE = ("The Gender Equality Index is published by the European Institute for Gender Equality (EIGE), an EU "
              "agency, and republished by the CSO. It scores each country from 1 to 100, where 100 would mean full "
              "equality between women and men, across six areas: work, money, knowledge, time, power and health.")


def build():
    equality_index_eu()
    equality_index_domains()
    pay_gap()
    pay_gap_eu()
    employment()
    carers()
    top_earners()
    dail()
    business_leaders()
    violence.build()


def _index():
    df = cso.fetch("WMI06")
    df = df.assign(geo=df.Country.map(CODES), geo_label=df.Country.replace({"Netherlands (the)": "Netherlands"}))
    return df.rename(columns={"Year": "time", "VALUE": "value"})


def equality_index_eu():
    df = _index()
    df = df[df["Statistic Label"] == "Gender Equality Index - Overall"]
    eu.rank_chart(
        "gender-equality-index-eu", TOPIC, "Gender Equality Index across the EU",
        "Gender Equality Index score, out of 100, EU countries, {year}.",
        Source.cso("WMI06", INDEX_SOURCE), df,
        lambda y, ie, ev, place: f"Ireland scored {ie:.1f} out of 100 on the Gender Equality Index for {y}, compared "
                                 f"with {ev:.1f} for the EU as a whole. Its score was {place}.",
        notes=[INDEX_NOTE, "This is the latest year of the index published in the CSO's table."],
        value_format=".1f")


def equality_index_domains():
    df = _index()
    year = int(df.time.max())
    d = df[(df.time == year) & df.geo.isin(["IE", eurostat.EU])]
    d = d[d["Statistic Label"] != "Gender Equality Index - Overall"]
    d = d.assign(area=d["Statistic Label"].str.replace("Gender Equality Index - ", "", regex=False))
    w = d.pivot_table(index="area", columns="geo", values="value").rename(columns={"IE": "Ireland", eurostat.EU: "EU"})
    w = w.sort_values("Ireland", ascending=False).reset_index()
    fig = go.Figure()
    for col, colour in [("Ireland", style.ORANGE), ("EU", style.INK_3)]:
        fig.add_trace(go.Bar(y=w.area, x=w[col], name=col, orientation="h", marker=dict(color=colour, cornerradius=3),
                             text=[f"{v:.1f}" for v in w[col]], textposition="outside", cliponaxis=False,
                             textfont=dict(color=style.INK_2, size=11),
                             hovertemplate=f"<b>%{{y}}</b>, {col}: %{{x:.1f}}<extra></extra>"))
    fig.update_layout(style.base_layout(
        barmode="group", bargap=0.25, bargroupgap=0.05, showlegend=True,
        legend=dict(style.legend_top(), traceorder="normal"), margin=dict(l=8, r=48, t=40, b=32),
        xaxis=style.value_axis(range=[0, 105]),
        yaxis=style.axis(automargin=True, autorange="reversed", tickfont=dict(color=style.INK_2, size=12))))
    hi, lo = w.iloc[0], w.iloc[-1]
    Chart(
        id="gender-equality-index-areas", topic=TOPIC, height=440,
        title="Gender Equality Index by area",
        subtitle=f"Gender Equality Index score for each area, out of 100, Ireland and the EU, {year}.",
        sources=[Source.cso("WMI06", INDEX_SOURCE)],
        notes=[INDEX_NOTE, "Power covers political, economic and social decision-making. Time covers time spent on care, "
               "housework and social activities."],
        key_fact=f"In the {year} Gender Equality Index, Ireland scored highest on {hi.area.lower()}, at {hi.Ireland:.1f}, "
                 f"and lowest on {lo.area.lower()}, at {lo.Ireland:.1f}.",
        data=w, figure=fig,
    ).write()


PAY_NOTE = ("The gender pay gap is the difference between the average hourly earnings of men and women, as a "
            "percentage of men's. It compares all employees, not women and men in the same jobs, so it reflects "
            "differences in jobs, sectors and hours as well as any differences in pay for the same work.")


def _pay_gap():
    return eurostat.fetch("earn_gr_gpgr2", geo=EU_GEO, nace_r2="B-S_X_O", unit="PC")


def pay_gap():
    eu.lines_chart(
        "gender-pay-gap", TOPIC, "The gender pay gap in Ireland and the EU",
        "Difference between men's and women's average gross hourly earnings, as a percentage of men's, {first} to {last}.",
        Source.eurostat("earn_gr_gpgr2", "Gender pay gap in unadjusted form"), _pay_gap(),
        lambda w: (lambda b: f"In {b.year:.0f}, women in Ireland earned on average {b.ireland:.1f}% less per hour than "
                             f"men, compared with {b.eu_average:.1f}% across the EU.")(w.dropna().iloc[-1]),
        notes=[PAY_NOTE, "Covers businesses with 10 or more employees, excluding public administration and defence."],
        suffix="%", y_range=[0, 20])


def pay_gap_eu():
    eu.rank_chart(
        "gender-pay-gap-eu", TOPIC, "The gender pay gap across the EU",
        "Difference between men's and women's average gross hourly earnings, as a percentage of men's, EU countries, {year}.",
        Source.eurostat("earn_gr_gpgr2", "Gender pay gap in unadjusted form"), _pay_gap(),
        lambda y, ie, ev, place: f"Ireland's gender pay gap was {ie:.1f}% in {y}, compared with {ev:.1f}% across the "
                                 f"EU. It was {place}.",
        notes=[PAY_NOTE, "A negative figure means women earned more per hour than men on average."],
        suffix="%")


def employment():
    df = eurostat.fetch("lfsi_emp_a", geo=EU_GEO, indic_em="EMP_LFS", age="Y20-64", sex=["F", "M"], unit="PC_POP")
    d = df[df.geo == "IE"].pivot_table(index="time", columns="sex", values="value").reset_index()
    d = d.rename(columns={"time": "year", "F": "women", "M": "men"})
    d["year"] = d.year.astype(int)
    d = d[["year", "women", "men"]]
    a, b = d.iloc[0], d.iloc[-1]
    fig = figures.lines(d, "year", {"women": WOMEN, "men": MEN}, colours=[style.PURPLE, style.BLUE], value_format=".1f",
                        suffix="%", y_range=[0, 100])
    Chart(
        id="gender-employment", topic=TOPIC,
        title="Employment rates of women and men",
        subtitle=f"Share of people aged 20 to 64 in work, women and men, Ireland, {a.year:.0f} to {b.year:.0f}.",
        sources=[Source.eurostat("lfsi_emp_a", "Employment and activity by sex and age, annual data")],
        notes=["From the Labour Force Survey, which the CSO carries out and Eurostat publishes for every EU country."],
        key_fact=f"In {b.year:.0f}, {b.women:.1f}% of women aged 20 to 64 in Ireland were in work, compared with "
                 f"{b.men:.1f}% of men. In {a.year:.0f} the figures were {a.women:.1f}% and {a.men:.1f}%.",
        data=d, figure=fig,
    ).write()


def carers():
    df = cso.fetch("F4015", where={"County and City": ["State"], "Age Group": ["All ages"], "CensusYear": [2022]})
    df = df[(df["Statistic Label"] == "Carers") & df.Sex.isin(["Male", "Female"])]
    col = "Regular Unpaid Help"
    order = ["1-14 hours unpaid help per week", "15-28 hours unpaid help per week", "29-42 hours unpaid help per week",
             "43 or more hours unpaid help per week", "All carers"]
    labels = {order[0]: "1 to 14 hours a week", order[1]: "15 to 28 hours a week", order[2]: "29 to 42 hours a week",
              order[3]: "43 hours a week or more", order[4]: "All carers"}
    w = df.pivot_table(index=col, columns="Sex", values="VALUE").reindex(order).rename(index=labels)
    w = w.rename(columns={"Female": "women", "Male": "men"}).rename_axis("hours").reset_index()
    w["percent_women"] = (w.women / (w.women + w.men) * 100).round(1)
    w = w.astype({"women": int, "men": int})
    r = w.set_index("hours")
    Chart(
        id="gender-carers", topic=TOPIC, height=320,
        title="Women's share of unpaid carers",
        subtitle="Women as a share of people who give regular unpaid help to someone with a long-lasting health "
                 "condition, illness or disability, by hours a week, 2022.",
        sources=[Source.cso("F4015", "Census of Population 2022, carers")],
        notes=["From the 2022 census, which asked whether each person regularly provides unpaid personal help to a "
               "friend or family member with a long-term illness, health problem or disability. It does not cover "
               "looking after children who do not need such help. The data file has the numbers of women and men."],
        key_fact=f"In 2022, {r.loc['All carers', 'percent_women']:.0f}% of unpaid carers were women, and "
                 f"{r.loc['43 hours a week or more', 'percent_women']:.0f}% of those giving 43 hours or more a week.",
        data=w, figure=hbars(w, "hours", "percent_women", colour=style.PURPLE),
    ).write()


def top_earners():
    df = cso.fetch("DEA02")
    df = df[(df["NACE Rev 2 Economic Sector"] == "All NACE economic sectors") & (df.Sex == "Female")]
    names = {"All Employments": "All jobs", "Employments in Top 25% of Earnings": "Top 25% of earnings",
             "Employments in Top 10% of Earnings": "Top 10% of earnings", "Employments in Top 1% of Earnings": "Top 1% of earnings"}
    w = df.pivot_table(index="Year", columns="Statistic Label", values="VALUE").rename(columns=names).reset_index()
    w = w.rename(columns={"Year": "year"})[["year"] + list(names.values())]
    w["year"] = w.year.astype(int)
    a, b = w.iloc[0], w.iloc[-1]
    fig = figures.lines(w, "year", {c: c for c in names.values()}, value_format=".0f", suffix="%", y_range=[0, 60])
    fig.update_layout(margin=dict(r=170))
    Chart(
        id="gender-top-earners", topic=TOPIC,
        title="Women's share of the best-paid jobs",
        subtitle=f"Women's share of all jobs and of the best-paid jobs, by annual earnings, {a.year:.0f} to {b.year:.0f}.",
        sources=[Source.cso("DEA02", "Gender representation in employments, by earnings")],
        notes=["Counts employments from administrative records, so a person with more than one job can be counted "
               "more than once. Earnings are for the whole year, so they reflect hours worked as well as rates of pay."],
        key_fact=f"In {b.year:.0f}, women held {b['All jobs']:.0f}% of all jobs but {b['Top 1% of earnings']:.0f}% of "
                 f"the jobs in the top 1% of earnings, up from {a['Top 1% of earnings']:.0f}% in {a.year:.0f}.",
        data=w, figure=fig,
    ).write()


def dail():
    df = cso.fetch("G0502")
    d = df[(df.Sex == "Female") & (df.UNIT == "%")].copy()
    num = df[(df.Sex == "Female") & (df.UNIT == "Number")].set_index("Year").VALUE
    d["dail"] = d.Year.str.extract(r"^(\S+ Dáil)")[0] + " (" + d.Year.str.extract(r"(\d{4})$")[0] + ")"
    d["women_elected"] = d.Year.map(num).astype(int)
    d = d[["dail", "women_elected", "VALUE"]].rename(columns={"VALUE": "percent_women"})
    first, b = d.iloc[0], d.iloc[-1]
    fig = go.Figure(go.Bar(x=d.dail, y=d.percent_women, marker=dict(color=style.PURPLE, cornerradius=3),
                           text=[f"{v:.0f}%" for v in d.percent_women], textposition="outside", cliponaxis=False,
                           textfont=dict(color=style.INK, size=12), customdata=d.women_elected,
                           hovertemplate="<b>%{x}</b>: %{y:.0f}% (%{customdata} women)<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=8, t=8, b=80), bargap=0.3,
                                        xaxis=style.axis(type="category", tickangle=-35),
                                        yaxis=style.value_axis(ticksuffix="%", range=[0, 50])))
    Chart(
        id="gender-dail", topic=TOPIC, height=380,
        title="Women elected to the Dáil",
        subtitle="Women as a share of TDs elected at general elections, selected Dála, 1918 to 2024.",
        sources=[Source.cso("G0502", "Women and men elected to Dáil Éireann")],
        notes=["Counts TDs elected at each general election, not changes between elections."],
        key_fact=f"{b.women_elected} women were elected to the Dáil in {b.dail.split('(')[1].rstrip(')')}, "
                 f"{b.percent_women:.0f}% of all TDs. {first.women_elected} woman was elected to the first Dáil in 1918.",
        data=d, figure=fig,
    ).write()


def business_leaders():
    df = cso.fetch("GBA01")
    d = df[df.Sex == "Female"].pivot_table(index="Year", columns="Senior Roles in Business", values="VALUE")
    names = {"Senior Executives": "Senior executives", "Chief Financial Officers (CFOs)": "Chief financial officers",
             "Boards of Directors": "Board members", "Chief Executive Officers (CEOs)": "Chief executives",
             "Chairpersons": "Chairpersons"}
    d = d.rename(columns=names)[list(names.values())].reset_index().rename(columns={"Year": "year"})
    d["year"] = d.year.astype(int)
    a, b = d.iloc[0], d.iloc[-1]
    fig = figures.lines(d, "year", {c: c for c in names.values()}, value_format=".0f", suffix="%", y_range=[0, 50])
    fig.update_layout(margin=dict(r=190))
    Chart(
        id="gender-business-leaders", topic=TOPIC,
        title="Women in senior roles in large companies",
        subtitle=f"Women's share of senior roles in large enterprises, {a.year:.0f} to {b.year:.0f}.",
        sources=[Source.cso("GBA01", "Gender balance in business")],
        notes=["From the CSO's Gender Balance in Business survey of large enterprises, carried out every two years."],
        key_fact=f"In {b.year:.0f}, women held {b['Board members']:.0f}% of board seats and {b['Chief executives']:.0f}% "
                 f"of chief executive roles in large companies, up from {a['Board members']:.0f}% and "
                 f"{a['Chief executives']:.0f}% in {a.year:.0f}.",
        data=d, figure=fig,
    ).write()
