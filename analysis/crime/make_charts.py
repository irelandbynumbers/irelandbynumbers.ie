"""Crime charts, from CSO recorded crime statistics (Garda PULSE data)."""
import pandas as pd
import plotly.graph_objects as go

from ibn import cso, figures, style
from ibn.chart import Chart, Source

TOPIC = "crime"

RESERVATION = ("The CSO publishes recorded crime figures as statistics under reservation. This means the "
               "quality of the underlying Garda data does not yet meet the standards the CSO requires of official "
               "statistics, and the figures should be read with that in mind.")

THEFT = {
    "Theft from shop (0822)": "Theft from shops",
    "Other thefts, handling stolen property (084)": "Other thefts",
    "Burglary (not aggravated) (0712)": "Burglary",
    "Theft/taking of vehicle and related offences (081)": "Theft or taking of vehicles",
    "Theft from person (0821)": "Theft from the person",
}


def build():
    thefts_by_type()
    by_offence()
    trends()
    division_maps()


def thefts_by_type():
    df = cso.fetch("CJA01")
    d = df[df["Type of Offence"].isin(THEFT)].pivot_table(index="Year", columns="Type of Offence", values="VALUE").reset_index()
    cols = {k: v.lower().replace(" ", "_") for k, v in THEFT.items()}
    d = d.rename(columns=cols)[["Year", *cols.values()]]
    for c in cols.values():
        d[c] = d[c].astype(int)
    series = {cols[k]: v for k, v in THEFT.items()}
    fig = figures.lines(d, "Year", series, label_last=False, y_range=[0, d[list(cols.values())].max().max() * 1.08])
    fig.update_layout(showlegend=True, legend=style.legend_top(), margin=dict(t=64))
    a, b = d.iloc[0], d.iloc[-1]
    Chart(
        id="crime-thefts", topic=TOPIC,
        key_fact=f"{b.theft_from_shops:,} thefts from shops were recorded in {b.Year}, compared with "
                 f"{a.theft_from_shops:,} in {a.Year}.",
        title="Recorded thefts and burglaries",
        subtitle=f"Number of theft and burglary incidents recorded by An Garda Síochána each year, by type, {d.Year.min()} to {d.Year.max()}.",
        sources=[Source.cso("CJA01", "Recorded crime incidents")],
        notes=[RESERVATION,
               "Recorded crime counts incidents reported to or discovered by the Gardaí. Changes can reflect how often "
               "crimes are reported and recorded, as well as how often they happen.",
               "Other thefts covers thefts that fall outside the other categories shown, along with handling stolen property. "
               "This table does not show theft from vehicles separately. Burglary excludes aggravated burglary, which numbers a few hundred a year."],
        data=d, figure=fig,
    ).write()


# Offence groups, as the CSO names them, and plain names for the charts.
GROUPS = {
    "Homicide & related offences (01)": "Homicide",
    "Sexual offences (02)": "Sexual offences",
    "Attempts/threats to murder, assaults, harassments and related offences (03)": "Assaults, threats and harassment",
    "Dangerous or negligent acts (04)": "Dangerous or negligent acts",
    "Kidnapping and related offences (05)": "Kidnapping",
    "Robbery, extortion and hijacking offences (06)": "Robbery",
    "Burglary and related offences (07)": "Burglary",
    "Theft and related offences (08)": "Theft",
    "Controlled drug offences (10)": "Drug offences",
    "Weapons and explosives offences (11)": "Weapons offences",
    "Damage to property and to the environment  offences (12)": "Damage to property",
    "Public order and other social code offences (13)": "Public order offences",
    "Road and traffic offences (14)": "Road and traffic offences",
    "Offences against government, justice procedures and organisation of crime (15)": "Offences against justice and government",
    "Offences not elsewhere classified (16)": "Other offences",
}
FRAUD_NOTE = ("Fraud is not shown. The CSO stopped including it in this table after 2022 and now publishes fraud "
              "reported directly by the public in separate tables.")


def by_offence():
    df = cso.fetch("CJA01")
    year = int(df.Year.max())
    d = df[(df.Year == year) & df["Type of Offence"].isin(GROUPS)].dropna(subset=["VALUE"]).copy()
    d["offence"] = d["Type of Offence"].map(GROUPS)
    d["incidents"] = d.VALUE.astype(int)
    d = d.sort_values("incidents").reset_index(drop=True)[["offence", "incidents"]]
    fig = go.Figure(go.Bar(y=d.offence, x=d.incidents, orientation="h", marker=dict(color=style.BLUE, cornerradius=4),
                           text=[f"{v:,}" for v in d.incidents], textposition="outside", cliponaxis=False,
                           textfont=dict(color=style.INK, size=12),
                           hovertemplate="<b>%{y}</b>: %{x:,} incidents<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=64, t=8, b=32), bargap=0.3,
                                        xaxis=style.value_axis(tickformat="~s"),
                                        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=12))))
    top = d.iloc[-1]
    total = d.incidents.sum()
    Chart(
        id="crime-by-offence", topic=TOPIC, height=560,
        title="Recorded crime by type of offence",
        subtitle=f"Number of crime incidents recorded by An Garda Síochána in {year}, by type of offence.",
        sources=[Source.cso("CJA01", "Recorded crime incidents")],
        notes=[RESERVATION,
               "Each incident is counted once, under its most serious offence. Road and traffic offences cover offences "
               "recorded as crime incidents, such as vehicle tax and roadworthiness offences, not fixed-charge "
               "penalties such as speeding fines.", FRAUD_NOTE],
        key_fact=f"Theft was the most common type of recorded crime in {year}, with {top.incidents:,} incidents, "
                 f"about {top.incidents / total * 100:.0f}% of the offences shown." if top.offence == "Theft" else
                 f"{top.offence} was the most common type of recorded crime in {year}, with {top.incidents:,} incidents.",
        data=d.iloc[::-1].reset_index(drop=True), figure=fig,
    ).write()


TREND = ["Theft", "Assaults, threats and harassment", "Public order offences", "Damage to property", "Burglary"]


def trends():
    df = cso.fetch("CJA01")
    d = df[df["Type of Offence"].isin(GROUPS)].copy()
    d["offence"] = d["Type of Offence"].map(GROUPS)
    d = d[d.offence.isin(TREND)].pivot_table(index="Year", columns="offence", values="VALUE").reset_index()
    cols = {o: o.split(",")[0].lower().replace(" ", "_") for o in TREND}
    d = d.rename(columns=cols)[["Year", *cols.values()]].astype(int)
    fig = figures.lines(d, "Year", {v: k for k, v in cols.items()}, label_last=False,
                        y_range=[0, d[list(cols.values())].max().max() * 1.08])
    fig.update_layout(showlegend=True, legend=style.legend_top(), margin=dict(t=64))
    a, b = d.iloc[0], d.iloc[-1]
    peak = d.loc[d.burglary.idxmax()]
    Chart(
        id="crime-trends", topic=TOPIC,
        title="Recorded crime over time",
        subtitle=f"Number of crime incidents recorded by An Garda Síochána each year, for the five largest types of "
                 f"crime against people and property, {a.Year} to {b.Year}.",
        sources=[Source.cso("CJA01", "Recorded crime incidents")],
        notes=[RESERVATION,
               "Recorded crime counts incidents reported to or discovered by the Gardaí. Changes can reflect how often "
               "crimes are reported and recorded, as well as how often they happen.",
               "Assaults covers assaults, threats to murder, harassment and related offences."],
        key_fact=f"{b.burglary:,} burglaries were recorded in {b.Year}, down from a peak of {peak.burglary:,} in {peak.Year}.",
        data=d, figure=fig,
    ).write()


# Garda divisions (before the new operating model) and the counties each mainly covers.
DIVISIONS = {
    "Cavan/Monaghan": ["Cavan", "Monaghan"], "Clare": ["Clare"], "Cork City": ["Cork"], "Cork North": ["Cork"],
    "Cork West": ["Cork"], "Donegal": ["Donegal"], "Galway": ["Galway"], "Kerry": ["Kerry"], "Kildare": ["Kildare"],
    "Kilkenny/Carlow": ["Kilkenny", "Carlow"], "Laois/Offaly": ["Laois", "Offaly"], "Limerick": ["Limerick"],
    "Louth": ["Louth"], "Mayo": ["Mayo"], "Meath": ["Meath"], "Roscommon/Longford": ["Roscommon", "Longford"],
    "Sligo/Leitrim": ["Sligo", "Leitrim"], "Tipperary": ["Tipperary"], "Waterford": ["Waterford"],
    "Westmeath": ["Westmeath"], "Wexford": ["Wexford"], "Wicklow": ["Wicklow"],
}
MAPS = {
    "burglary": ("Burglary and related offences (07)", "burglaries"),
    "assaults": ("Attempts/threats to murder, assaults, harassments and related offences (03)", "assaults, threats and harassment offences"),
}


def _area(division):
    name = division.removesuffix(" Division")
    if name.startswith("D.M.R."):
        return "Dublin Metropolitan Region"
    if name.startswith("Cork"):
        return "Cork (three divisions)"
    return name


def division_maps():
    df = cso.fetch("CJA07", where={"Type of Offence": [o for o, _ in MAPS.values()]})
    year = int(df.Year.max())
    df = df[df.Year == year].copy()
    df["division"] = df["Garda Station"].str.split(", ").str[-1]
    df["area"] = df.division.map(_area)
    pop = cso.fetch("F1001")
    pop = pop[(pop.Sex == "Both sexes") & pop.County.isin(figures.COUNTIES) & (pop.CensusYear == 2022)]
    pop = dict(zip(pop.County, pop.VALUE))
    areas = {"Dublin Metropolitan Region": ["Dublin"], "Cork (three divisions)": ["Cork"]}
    areas.update({k: v for k, v in DIVISIONS.items() if not k.startswith("Cork")})
    for key, (offence, words) in MAPS.items():
        a = df[df["Type of Offence"] == offence].groupby("area").VALUE.sum().astype(int).rename("incidents").reset_index()
        a["population"] = a.area.map(lambda x: sum(pop[c] for c in areas[x])).astype(int)
        a["per_1000_people"] = (a.incidents / a.population * 1000).round(1)
        d = a.merge(pd.DataFrame([(k, c) for k, cs in areas.items() for c in cs], columns=["area", "county"]), on="area")
        assert sorted(d.county) == sorted(figures.COUNTIES), "every county should be in one Garda area"
        fig = figures.county_map(d[["county", "area", "per_1000_people"]], "county", "per_1000_people",
                                 value_format=".1f", legend_title=f"{words.capitalize()} per 1,000 people",
                                 hover_extra="Garda division: %{customdata[1]}")
        a = a.sort_values("per_1000_people", ascending=False).reset_index(drop=True)
        hi, second, lo = a.iloc[0], a.iloc[1], a.iloc[-1]
        name = lambda x: ("the Dublin Metropolitan Region" if x.startswith("Dublin") else
                          "the three Cork divisions" if x.startswith("Cork") else f"the {x} division")
        top = (f"{name(hi.area)} and {name(second.area)} had the joint highest rate of recorded {words}, {hi.per_1000_people:.1f} per 1,000 people"
               if second.per_1000_people == hi.per_1000_people else
               f"{name(hi.area)} had the highest rate of recorded {words}, {hi.per_1000_people:.1f} per 1,000 people")
        Chart(
            id=f"crime-{key}-map", topic=TOPIC, kind="map", height=600,
            title=f"{words.capitalize()} by Garda division",
            subtitle=f"Recorded {words} per 1,000 people in each Garda division, {year}.",
            sources=[Source.cso("CJA07", "Recorded crime incidents by Garda station"),
                     Source.cso("F1001", "Census of Population, population by county")],
            notes=[RESERVATION,
                   "Incidents recorded at each Garda station are added up to its division. Each division is shown as the "
                   "counties it mainly covers, as Garda divisions are drawn largely along county lines. The six Dublin "
                   "divisions are shown together as the Dublin Metropolitan Region, and the three Cork divisions together.",
                   "Rates use each area's population at the 2022 census. Divisions are those in place before An Garda "
                   "Síochána began merging them under its new operating model."],
            key_fact=f"In {year}, {top}, compared with {lo.per_1000_people:.1f} in {name(lo.area)}.",
            data=d[["area", "county", "incidents", "population", "per_1000_people"]], figure=fig,
        ).write()
