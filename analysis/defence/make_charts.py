"""Defence and security charts: government spending on defence compared with
the EU, trust in the Defence Forces, and cyber security incidents at
businesses. Figures only, with no view on defence or neutrality policy."""
import plotly.graph_objects as go

from ibn import eu, eurostat, figures, style
from ibn.chart import Chart, Source
from ibn.charts import oecd_trust

TOPIC = "defence"
EU_GEO = eurostat.EU27 + [eurostat.EU]
COFOG = ("gov_10a_exp", "General government expenditure by function (COFOG)")
COFOG_NOTE = ("Defence is spending by central and local government on military defence, civil defence, foreign "
              "military aid and defence research, as classified under the international Classification of the "
              "Functions of Government (COFOG). It includes pay, equipment and buildings.")
CYBER = ("isoc_cisce_ic", "Security related incidents and consequences (enterprises)")


def build():
    spending_per_person_eu()
    spending_share()
    spending_trend()
    trust_armed_forces()
    cyber_incidents_eu()
    cyber_incident_types()


def _cofog():
    return eurostat.fetch(COFOG[0], name="gov_defence", geo=EU_GEO, cofog99="GF02", sector="S13", na_item="TE",
                          unit=["PC_GDP", "MIO_EUR", "PC_TOT"])


def spending_per_person_eu():
    df = _cofog()
    eur = df[df.unit == "MIO_EUR"][["geo", "geo_label", "time", "value"]]
    pop = eurostat.fetch("demo_pjan", name="population_total", geo=EU_GEO, age="TOTAL", sex="T")[["geo", "time", "value"]]
    d = eur.merge(pop.rename(columns={"value": "people"}), on=["geo", "time"])
    d["value"] = (d.value * 1e6 / d.people).round(0)
    gdp = df[(df.unit == "PC_GDP") & (df.geo.isin(["IE", eurostat.EU]))].pivot_table(index="time", columns="geo", values="value")
    eu.rank_chart(
        "defence-spending-eu", TOPIC, "Defence spending across the EU",
        "Government spending on defence per person, in euro, EU countries, {year}.",
        Source.eurostat(*COFOG, name="gov_defence"), d,
        lambda y, ie, ev, place: f"Government spending on defence in Ireland was €{ie:,.0f} per person in {y}, "
                                 f"compared with €{ev:,.0f} across the EU. Ireland's spending was {place}. It came to "
                                 f"{gdp.loc[y, 'IE']:.1f}% of GDP, compared with {gdp.loc[y, eurostat.EU]:.1f}% across the EU.",
        notes=[COFOG_NOTE, "Spending per person is total spending divided by the population on 1 January of the "
               "same year, from Eurostat (demo_pjan). Figures are in euro at current prices and are not "
               "adjusted for differences in prices between countries."],
        value_format=",.0f", prefix="€", higher_is="highest")


def spending_share():
    df = _cofog()
    eu.lines_chart(
        "defence-spending-share", TOPIC, "Defence as a share of government spending",
        "Defence as a share of total government spending, Ireland and the EU, {first} to {last}.",
        Source.eurostat(*COFOG, name="gov_defence"), df[df.unit == "PC_TOT"],
        lambda w: (lambda a, b: f"Defence made up {b.ireland:.1f}% of government spending in Ireland in {b.year:.0f}, "
                                f"compared with {b.eu_average:.1f}% across the EU. In {a.year:.0f} it was "
                                f"{a.ireland:.1f}% in Ireland.")(w.iloc[0], w.dropna().iloc[-1]),
        notes=[COFOG_NOTE, "Eurostat rounds these shares to one decimal place."],
        suffix="%", y_range=[0, None])


def spending_trend():
    df = _cofog()
    w = df[(df.unit == "MIO_EUR") & (df.geo == "IE")][["time", "value"]].rename(columns={"time": "year", "value": "euro_million"})
    w["year"] = w.year.astype(int)
    w = w.dropna().sort_values("year")
    a, b = w.iloc[0], w.iloc[-1]
    peak = w.loc[w.euro_million.idxmax()]
    fig = go.Figure(go.Bar(x=w.year, y=w.euro_million, marker=dict(color=style.BLUE, cornerradius=2),
                           hovertemplate="<b>%{x}</b>: €%{y:,.0f} million<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=64, r=16, t=8, b=32), bargap=0.2,
                                        xaxis=style.axis(), yaxis=style.value_axis(tickprefix="€", ticksuffix="m")))
    Chart(
        id="defence-spending-trend", topic=TOPIC,
        title="Defence spending in Ireland",
        subtitle=f"Government spending on defence in Ireland, in millions of euro at current prices, {a.year:.0f} to {b.year:.0f}.",
        sources=[Source.eurostat(*COFOG, name="gov_defence")],
        notes=[COFOG_NOTE, "Figures are at current prices and are not adjusted for inflation."],
        key_fact=f"The Irish government spent €{b.euro_million:,.0f} million on defence in {b.year:.0f}, compared with "
                 f"€{a.euro_million:,.0f} million in {a.year:.0f}. The highest in the period was €{peak.euro_million:,.0f} "
                 f"million in {peak.year:.0f}.",
        data=w, figure=fig,
    ).write()


def trust_armed_forces():
    year, d = oecd_trust("Armed Forces (OECD)")
    r = d.set_index("country").value
    c = d[d.geo != eurostat.EU].reset_index(drop=True)
    place, n = int(c.index[c.country == "Ireland"][0]) + 1, len(c)
    Chart(
        id="defence-trust-armed-forces", topic=TOPIC, height=720,
        title="Trust in the armed forces",
        subtitle=f"Share of people who trust their country's armed forces, OECD Trust Survey countries, {year}.",
        sources=[Source.cso("TRA312", "OECD Trust Survey, trust in institutions across countries")],
        notes=["From the OECD Survey on Drivers of Trust in Public Institutions, republished by the CSO. People "
               "rated their trust from 0 (not at all) to 10 (completely), and a score of 6 to 10 counts as trust.",
               "In Ireland the armed forces are the Defence Forces. The OECD average is shown in dark grey."],
        key_fact=f"In {year}, {r['Ireland']:.0f}% of people in Ireland said they trust the armed forces, compared with "
                 f"an OECD average of {r['OECD average']:.0f}%. Ireland ranked "
                 f"{eu.ordinal(place)} of the {n} countries with figures.",
        data=d.drop(columns="geo"), figure=eu.bars(d, ".0f", "%"),
    ).write()


def _cyber():
    return eurostat.fetch(CYBER[0], name="cyber_enterprises", geo=EU_GEO, size_emp="GE10", unit="PC_ENT")


def cyber_incidents_eu():
    df = _cyber()
    eu.rank_chart(
        "defence-cyber-incidents-eu", TOPIC, "Cyber security incidents at businesses",
        "Share of businesses that had an ICT security incident, EU countries, {year}.",
        Source.eurostat(*CYBER, name="cyber_enterprises"), df[df.indic_is == "E_SEC2IANY"],
        lambda y, ie, ev, place: f"In {y}, {ie:.0f}% of businesses in Ireland had an ICT security incident, compared "
                                 f"with {ev:.0f}% across the EU. Ireland's share was {place}.",
        notes=["Covers businesses with ten or more people employed, outside farming, mining and finance. An incident "
               "is anything that made ICT services unavailable, or destroyed, corrupted or disclosed data, during the "
               "previous year. It includes hardware or software failures as well as attacks."],
        value_format=".0f", suffix="%")


CYBER_TYPES = {"E_SEC2IUSVF": "Services down, from a hardware or software failure",
               "E_SEC2IUSVA": "Services down, from an outside attack",
               "E_SEC2IDCDF": "Data lost or corrupted, from a failure",
               "E_SEC2IDCDA": "Data lost or corrupted, from malware or intrusion",
               "E_SEC2ICNFA": "Confidential data disclosed, from intrusion or phishing",
               "E_SEC2ICNFF": "Confidential data disclosed, by staff by mistake"}


def cyber_incident_types():
    df = _cyber()
    df = df[df.indic_is.isin(CYBER_TYPES) & df.geo.isin(["IE", eurostat.EU])]
    year = int(df[df.geo == "IE"].dropna(subset=["value"]).time.max())
    w = (df[df.time == year].pivot_table(index="indic_is", columns="geo", values="value")
         .reindex(list(CYBER_TYPES)).rename(index=CYBER_TYPES).rename(columns={"IE": "ireland", eurostat.EU: "eu_average"})
         .rename_axis("incident").reset_index())
    fig = go.Figure()
    for col, name, colour in [("ireland", "Ireland", style.ORANGE), ("eu_average", "EU average", style.CONTEXT)]:
        fig.add_bar(y=w.incident, x=w[col], name=name, orientation="h", marker=dict(color=colour, cornerradius=3),
                    text=[f"{v:.1f}%" for v in w[col]], textposition="outside", cliponaxis=False,
                    textfont=dict(color=style.INK, size=12),
                    hovertemplate=f"<b>%{{y}}</b><br>{name}: %{{x:.1f}}%<extra></extra>")
    fig.update_layout(style.base_layout(margin=dict(l=8, r=48, t=40, b=32), bargap=0.3, bargroupgap=0.08,
                                        barmode="group", showlegend=True, legend=style.legend_top(),
                                        xaxis=style.value_axis(ticksuffix="%"),
                                        yaxis=style.axis(automargin=True, autorange="reversed",
                                                         tickfont=dict(color=style.INK_2, size=12))))
    r = w.set_index("incident")
    att = r.loc["Services down, from an outside attack"]
    Chart(
        id="defence-cyber-incident-types", topic=TOPIC, height=460,
        title="Types of cyber security incident",
        subtitle=f"Share of businesses that had each type of ICT security incident, Ireland and the EU, {year}.",
        sources=[Source.eurostat(*CYBER, name="cyber_enterprises")],
        notes=["Covers businesses with ten or more people employed, outside farming, mining and finance, during the "
               "previous year. A business can have more than one type of incident.",
               "Outside attacks include ransomware and denial of service attacks."],
        key_fact=f"In {year}, {att.ireland:.1f}% of businesses in Ireland had ICT services go down because of an outside "
                 f"attack such as ransomware, compared with {att.eu_average:.1f}% across the EU. Hardware or software "
                 f"failures were far more common.",
        data=w, figure=fig,
    ).write()
