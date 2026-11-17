"""Elections and trust charts: turnout at Dáil and European Parliament
elections, turnout compared with other EU countries, trust in public
institutions, and views on how elections are run. Figures only, with no
view on any party or result."""
import pandas as pd
import plotly.graph_objects as go

from ibn import cso, eu, eurostat, figures, idea, style
from ibn.chart import Chart, Source
from ibn.charts import hbars, oecd_trust

TOPIC = "elections"
TURNOUT_NOTE = ("Turnout is the number of votes cast, including spoilt votes, as a share of the people on the "
                "electoral register.")
TRUST_NOTE = ("From the CSO's survey for the OECD Survey on Drivers of Trust in Public Institutions. People rated "
              "their trust from 0 (not at all) to 10 (completely), and a score of 6 to 10 counts as trust.")


def build():
    turnout()
    turnout_eu()
    trust_institutions()
    trust_government_oecd()
    satisfaction()
    views_on_voting()


def _ireland():
    d = idea.fetch()
    return d[(d.iso2 == "IE") & d.turnout.notna()]


def turnout():
    d = _ireland()
    names = {"Parliamentary": "Dáil", "EU Parliament": "European Parliament"}
    d = d[d.election_type.isin(names)].assign(election=lambda x: x.election_type.map(names))
    w = d.pivot_table(index="year", columns="election", values="turnout").reset_index()
    w["year"] = w.year.astype(int)
    fig = figures.lines(w, "year", {"Dáil": "Dáil", "European Parliament": "European Parliament"},
                        colours=[style.BLUE, style.GOLD], value_format=".0f", suffix="%", y_range=[0, 100])
    for tr in fig.data:
        tr.update(mode="lines+markers", marker=dict(size=6), connectgaps=True)
    fig.update_layout(margin=dict(r=170))
    dail = d[d.election_type == "Parliamentary"].sort_values("year")
    first, last = dail.iloc[0], dail.iloc[-1]
    peak = dail.loc[dail.turnout.idxmax()]
    euro = d[d.election_type == "EU Parliament"].sort_values("year").iloc[-1]
    Chart(
        id="elections-turnout", topic=TOPIC,
        title="Turnout at elections",
        subtitle=f"Turnout at Dáil and European Parliament elections in Ireland, {int(first.year)} to {int(last.year)}.",
        sources=[idea.source()],
        notes=[TURNOUT_NOTE, "Each point is an election. The database has the November 1982 Dáil election but not the "
               "February 1982 one. Presidential elections and referendums are not shown."],
        key_fact=f"Turnout at the {int(last.year)} general election was {last.turnout:.1f}%, compared with "
                 f"{peak.turnout:.1f}% in {int(peak.year)}, the highest since {int(first.year)}. Turnout at the "
                 f"{int(euro.year)} European Parliament election was {euro.turnout:.1f}%.",
        data=w, figure=fig,
    ).write()


def turnout_eu():
    d = idea.fetch()
    p = d[(d.election_type == "Parliamentary") & d.turnout.notna()].assign(geo=lambda x: x.iso2.replace({"GR": "EL"}))
    p = p[p.geo.isin(eurostat.EU27)].sort_values("date").groupby("geo").tail(1)
    p = p.assign(country=[eurostat.country(g) or c for g, c in zip(p.geo, p.country)])
    p = p.sort_values("turnout", ascending=False).reset_index(drop=True)
    b = p.rename(columns={"turnout": "value"})[["country", "geo", "value"]]
    place, _, total = eu.rank(b)
    compulsory = ", ".join(sorted(p[p.compulsory_voting == "Yes"].country))
    ie = p.set_index("geo").loc["IE"]
    Chart(
        id="elections-turnout-eu", topic=TOPIC, height=620,
        title="Turnout at national elections across the EU",
        subtitle="Turnout at the most recent national parliamentary election in each EU country.",
        sources=[idea.source()],
        notes=[TURNOUT_NOTE, "The elections were held in different years, from "
               f"{int(p.year.min())} to {int(p.year.max())}. The data file has the date of each election.",
               f"Voting is compulsory in {compulsory}, according to the database. Electoral registers are kept in "
               "different ways in different countries, which affects turnout figures."],
        key_fact=f"Turnout at Ireland's {int(ie.year)} general election was {ie.turnout:.1f}%. Comparing each "
                 f"country's most recent national election, Ireland's turnout was {place}.",
        data=p[["country", "date", "turnout", "compulsory_voting"]], figure=eu.bars(b, ".0f", "%"),
    ).write()


TRUST_NAMES = {"The electoral system": "The electoral system", "The police (the Gardaí)": "The Gardaí",
               "The armed forces/military": "The Defence Forces", "The courts and legal system": "The courts",
               "The civil service": "The civil service", "International organisations": "International organisations",
               "The news media": "The news media",
               "The parliament/congress (the Oireachtas)": "The Oireachtas",
               "Their local government (local authority)": "Local councils",
               "National government (the Taoiseach and government ministers)": "The government",
               "Political parties": "Political parties"}


def trust_institutions():
    df = cso.fetch("TRA102")
    year = int(df.Year.max())
    df = df[(df.Gender == "Both male and female") & (df["Statistic Label"] == "Trust (6-10)") & (df.Year == year)]
    w = (df.set_index("Trust in people and institutions").VALUE.reindex(list(TRUST_NAMES)).rename(index=TRUST_NAMES)
         .rename_axis("institution").reset_index(name="percent_trust").sort_values("percent_trust", ascending=False))
    r = w.set_index("institution").percent_trust
    Chart(
        id="elections-trust-institutions", topic=TOPIC, height=440,
        title="Trust in public institutions",
        subtitle=f"Share of people in Ireland who trust each institution, {year}.",
        sources=[Source.cso("TRA102", "Trust Survey, trust in people and institutions")],
        notes=[TRUST_NOTE],
        key_fact=f"In {year}, {r['The electoral system']:.0f}% of people in Ireland said they trust the electoral "
                 f"system, compared with {r['The government']:.0f}% for the government and "
                 f"{r['Political parties']:.0f}% for political parties.",
        data=w, figure=hbars(w, "institution", "percent_trust", colour=style.BLUE),
    ).write()


def trust_government_oecd():
    year, d = oecd_trust("National Government (OECD)")
    c = d[d.geo != eurostat.EU].reset_index(drop=True)
    place, n = int(c.index[c.country == "Ireland"][0]) + 1, len(c)
    r = d.set_index("country").value
    Chart(
        id="elections-trust-government-oecd", topic=TOPIC, height=720,
        title="Trust in national government across countries",
        subtitle=f"Share of people who trust their national government, OECD Trust Survey countries, {year}.",
        sources=[Source.cso("TRA312", "OECD Trust Survey, trust in institutions across countries")],
        notes=[TRUST_NOTE, "The OECD average is shown in dark grey."],
        key_fact=f"In {year}, {r['Ireland']:.0f}% of people in Ireland said they trust the national government, "
                 f"compared with an OECD average of {r['OECD average']:.0f}%. Ireland ranked {eu.ordinal(place)} of "
                 f"the {n} countries with figures.",
        data=d.drop(columns="geo"), figure=eu.bars(d, ".0f", "%"),
    ).write()


def satisfaction():
    age = cso.fetch("TRA269")
    vote = cso.fetch("TRA273")
    sat = "Satisfied (6-10)"
    rows = [(f"Aged {a.replace(' - ', ' to ').replace(' years and over', ' and over').replace(' years', '')}", v)
            for a, v in age[age["Statistic Label"] == sat][["Age", "VALUE"]].values]
    labels = {"Voted for a party in Government": "Voted for a party in government",
              "Voted for a party not in Government": "Voted for another party"}
    rows += [(labels[g], v) for g, v in vote[vote["Statistic Label"] == sat][["Voting status in last general election", "VALUE"]].values]
    w = pd.DataFrame(rows, columns=["group", "percent_satisfied"])
    year = int(age.Year.max())
    r = w.set_index("group").percent_satisfied
    Chart(
        id="elections-satisfaction", topic=TOPIC, height=320,
        title="Satisfaction with how elections are run",
        subtitle=f"Share of people satisfied with how elections are managed in Ireland, by age and by how they voted "
                 f"at the last general election, {year}.",
        sources=[Source.cso("TRA269", "Satisfaction with how elections are managed, by age"),
                 Source.cso("TRA273", "Satisfaction with how elections are managed, by voting status")],
        notes=["People rated their satisfaction from 0 to 10, and a score of 6 to 10 counts as satisfied. "
               "The CSO does not publish a figure for everyone together.",
               "The last two rows group people by whether they voted for a party in government at the last "
               "general election. People who did not vote are not included in those rows."],
        key_fact=f"In {year}, {r.iloc[0]:.0f}% of people aged 18 to 29 were satisfied with how elections are managed "
                 f"in Ireland, compared with {r.iloc[1]:.0f}% of those aged 30 to 49.",
        data=w, figure=hbars(w, "group", "percent_satisfied", colour=style.BLUE),
    ).write()


def views_on_voting():
    duty = cso.fetch("TRA274")
    duty = duty[(duty.Gender == "Both male and female") & (duty["Voting perception"] == "Perception voting is a duty")]
    ec = cso.fetch("TRA306")
    ec = ec[(ec.Gender == "Both male and female") & (ec["Statistic Label"] == "Trust (6-10)")]
    sysm = cso.fetch("TRA102")
    sysm = sysm[(sysm.Gender == "Both male and female") & (sysm["Statistic Label"] == "Trust (6-10)") &
                (sysm["Trust in people and institutions"] == "The electoral system") & (sysm.Year == 2025)]
    w = pd.DataFrame([("See voting as a duty rather than a choice", duty.VALUE.iloc[0]),
                      ("Trust the Electoral Commission", ec.VALUE.iloc[0]),
                      ("Trust the electoral system", sysm.VALUE.iloc[0])], columns=["view", "percent"])
    r = w.set_index("view").percent
    Chart(
        id="elections-views-on-voting", topic=TOPIC, height=240,
        title="Views on voting and elections",
        subtitle="Share of people in Ireland who hold each view, 2025.",
        sources=[Source.cso("TRA274", "Perception of voting as a duty or choice"),
                 Source.cso("TRA306", "Trust in the Electoral Commission (An Coimisiún Toghcháin)"),
                 Source.cso("TRA102", "Trust Survey, trust in people and institutions")],
        notes=[TRUST_NOTE, "The Electoral Commission, An Coimisiún Toghcháin, was set up in 2023. Its work includes "
               "reviewing constituency boundaries and explaining referendum proposals to voters."],
        key_fact=f"In 2025, {r.iloc[0]:.0f}% of people in Ireland saw voting as a duty rather than a choice, and "
                 f"{r.iloc[1]:.0f}% said they trust the Electoral Commission.",
        data=w, figure=hbars(w, "view", "percent", colour=style.BLUE),
    ).write()
