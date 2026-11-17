"""Childcare and family leave charts: the gap between paid leave and a
guaranteed childcare place, childcare use and fees compared with the EU,
the types of childcare families use, family leave entitlements in Ireland
and Northern Ireland, and fathers' use of paternity benefit. Figures only,
with no view on policy."""
import os

import pandas as pd
import plotly.graph_objects as go

from ibn import cso, eu, eurostat, eurydice, figures, style
from ibn.chart import Chart, Source
from ibn.charts import hbars

TOPIC = "childcare"
EU_GEO = eurostat.EU27 + [eurostat.EU]
EU_NAMES = {"Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia", "Denmark", "Estonia", "Finland",
            "France", "Germany", "Greece", "Hungary", "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta",
            "Netherlands", "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden"}
BELGIUM = "Belgium (Flemish Community)"


def build():
    gap_eu()
    well_paid_leave_eu()
    under3_eu()
    under3_trend()
    affordable_access()
    types()
    fees_eu()
    fees_trend()
    fees_county()
    fees_deprivation()
    leave_ireland_ni()
    paternity_uptake()


def _eu_rows(d):
    """EU countries only, with Belgium shown once (its three communities have
    the same figures in these tables unless noted)."""
    d = d[d.country.isin(EU_NAMES) | d.country.str.startswith("Belgium (")].copy()
    d = d[~d.country.str.startswith("Belgium (") | (d.country == BELGIUM)]
    d["country"] = d.country.replace({BELGIUM: "Belgium"})
    return d.reset_index(drop=True)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _gap_table():
    d = _eu_rows(eurydice.table("B3", ["well_paid_leave", "legal_entitlement", "compulsory_ecec", "compulsory_primary"]))
    for c in ["well_paid_leave", "legal_entitlement", "compulsory_ecec", "compulsory_primary"]:
        d[c] = d[c].map(_num)
    d["well_paid_leave"] = d.well_paid_leave.fillna(0)
    d["guaranteed_place_from"] = d[["legal_entitlement", "compulsory_ecec", "compulsory_primary"]].min(axis=1)
    d["gap_years"] = (d.guaranteed_place_from - d.well_paid_leave).clip(lower=0).round(2)
    d["well_paid_leave_months"] = (d.well_paid_leave * 12).round(0)
    return d


def gap_eu():
    d = _gap_table().sort_values(["gap_years", "country"], ascending=[True, True]).reset_index(drop=True)
    shown = d.iloc[::-1]
    fig = go.Figure()
    fig.add_bar(y=shown.country, x=shown.well_paid_leave, name="Well-paid leave", orientation="h",
                marker=dict(color=style.AQUA), hovertemplate="<b>%{y}</b><br>Well-paid leave: %{x:.1f} years<extra></extra>")
    fig.add_bar(y=shown.country, x=shown.gap_years, name="Gap before a guaranteed place", orientation="h",
                marker=dict(color=[style.ORANGE if c == "Ireland" else style.CONTEXT for c in shown.country]),
                hovertemplate="<b>%{y}</b><br>Gap: %{x:.1f} years<extra></extra>")
    fig.update_layout(style.base_layout(margin=dict(l=8, r=24, t=40, b=40), barmode="stack", bargap=0.25,
                                        showlegend=True, legend=dict(style.legend_top(), traceorder="normal"),
                                        xaxis=style.value_axis(ticksuffix=" yrs", range=[0, 7], dtick=1),
                                        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=11))))
    ie = d.set_index("country").loc["Ireland"]
    none = int((d.gap_years == 0).sum())
    Chart(
        id="childcare-gap-eu", topic=TOPIC, height=680,
        title="The gap between paid leave and a childcare place",
        subtitle="Years of well-paid leave after a birth, and the further gap before a child is guaranteed a "
                 "place in early childhood education and care or school, EU countries, 2024/2025.",
        sources=[eurydice.source("Figure B3")],
        notes=["Well-paid leave is maternity, paternity and parental leave paid at 66% or more of earnings, added "
               "together for both parents. Leave paid at a flat rate, as all family leave in Ireland is, is not counted.",
               "The guaranteed place is the earliest age from which every child has a legal right to a place in early "
               "childhood education and care, or must attend it, or must start primary school. Ireland has no legal "
               "entitlement to a place before school, so its gap runs to the start of compulsory school at age 6. "
               "The free preschool hours of the Early Childhood Care and Education (ECCE) scheme are not a guaranteed place.",
               "Belgium's figures are for the Flemish Community. The data file has every figure."],
        key_fact=f"In Ireland there is no well-paid family leave and no guaranteed childcare place before school, so the "
                 f"gap runs to age {ie.guaranteed_place_from:.0f}, the longest of the {len(d)} EU countries. In {none} "
                 f"countries there is no gap at all.",
        data=d[["country", "well_paid_leave_months", "guaranteed_place_from", "gap_years"]], figure=fig,
    ).write()


def well_paid_leave_eu():
    d = _gap_table()
    b = d.assign(geo=d.country.map({"Ireland": "IE"}).fillna(""), value=d.well_paid_leave_months)
    b = b.sort_values(["value", "country"], ascending=[False, True]).reset_index(drop=True)
    zero = sorted(b[b.value == 0].country)
    Chart(
        id="childcare-well-paid-leave-eu", topic=TOPIC, height=640,
        title="Well-paid family leave across the EU",
        subtitle="Months of family leave paid at 66% or more of earnings, for both parents together, EU countries, 2024.",
        sources=[eurydice.source("Figure B3")],
        notes=["Counts post-natal maternity, paternity and parental leave paid at 66% or more of previous earnings. "
               "Eurydice took most of these figures from the International Network on Leave Policies and Research, "
               "for April 2024.",
               "In Ireland, maternity, paternity and parent's benefit are paid at a flat weekly rate rather than as a share "
               "of earnings, so none of it counts as well-paid leave here. Employers may top up pay."],
        key_fact=("Ireland is the only EU country with no family leave paid at 66% or more of earnings."
                  if zero == ["Ireland"] else
                  f"Ireland is one of {len(zero)} EU countries with no family leave paid at 66% or more of earnings, "
                  f"along with {', '.join(c for c in zero if c != 'Ireland')}."),
        data=b[["country", "value"]].rename(columns={"value": "well_paid_leave_months"}),
        figure=eu.bars(b[["country", "geo", "value"]], ".0f", " months"),
    ).write()


def _formal():
    return eurostat.fetch("ilc_caindformal", name="childcare_formal", geo=EU_GEO, unit="PC")


def _under3(df):
    d = df[(df.age == "Y_LT3") & (df.duration == "H0")].copy()
    d["value"] = (100 - d.value).round(1)
    return d


def under3_eu():
    eu.rank_chart(
        "childcare-under3-eu", TOPIC, "Children under 3 in formal childcare",
        "Share of children under 3 in formal childcare for at least one hour a week, EU countries, {year}.",
        Source.eurostat("ilc_caindformal", "Children in formal childcare or education", name="childcare_formal"),
        _under3(_formal()),
        lambda y, ie, ev, place: f"In {y}, {ie:.0f}% of children under 3 in Ireland were in formal childcare, compared "
                                 f"with {ev:.0f}% across the EU. Ireland's share was {place}.",
        notes=["Formal childcare includes crèches, preschools and other centre-based care, and childminders who are "
               "registered or paid through an organisation. Care by relatives, friends or unregistered childminders is "
               "not included.",
               "From the EU Survey on Income and Living Conditions (EU-SILC). The figures for small countries can move "
               "a lot from year to year."],
        value_format=".0f", suffix="%")


def under3_trend():
    eu.lines_chart(
        "childcare-under3-trend", TOPIC, "Formal childcare for under-3s over time",
        "Share of children under 3 in formal childcare for at least one hour a week, Ireland and the EU, {first} to {last}.",
        Source.eurostat("ilc_caindformal", "Children in formal childcare or education", name="childcare_formal"),
        _under3(_formal()),
        lambda w: (lambda a, b: f"In {b.year:.0f}, {b.ireland:.0f}% of children under 3 in Ireland were in formal "
                                f"childcare, compared with {a.ireland:.0f}% in {a.year:.0f}. The EU figure was "
                                f"{b.eu_average:.0f}%.")(w.dropna(subset=["ireland"]).iloc[0], w.dropna().iloc[-1]),
        notes=["Formal childcare includes crèches, preschools and other centre-based care, and registered childminders. "
               "Survey changes mean small year-to-year movements should be read with care."],
        value_format=".0f", suffix="%", y_range=[0, None])


ACCESS = {"Strongly Agree or Agree": ("Agree", None), "Neither Agree nor Disagree": ("Neither", None),
          "Disagree or Strongly Disagree": ("Disagree", None), "Not Stated": ("Not stated", None)}


def affordable_access():
    df = cso.fetch("CCA21")
    w = df.pivot_table(index="Region", columns="Statistic Label", values="VALUE")
    w = w.rename(columns={k: v[0] for k, v in ACCESS.items()})[["Agree", "Neither", "Disagree", "Not stated"]]
    state = w.loc["State"]
    regions = w.drop("State").sort_values("Disagree", ascending=False)
    order = ["State"] + list(regions.index)
    w = w.reindex(order)
    labels = ["Ireland" if r == "State" else r for r in w.index]
    fig = go.Figure()
    for col, colour in [("Agree", style.BLUE), ("Neither", style.CONTEXT), ("Disagree", style.ORANGE),
                        ("Not stated", style.GRID)]:
        fig.add_bar(y=labels, x=w[col], name=col, orientation="h", marker=dict(color=colour),
                    text=[f"{v:.0f}%" if v >= 8 else "" for v in w[col]], textposition="inside",
                    insidetextanchor="middle", textfont=dict(size=11),
                    hovertemplate=f"<b>%{{y}}</b><br>{col}: %{{x:.0f}}%<extra></extra>")
    fig.update_layout(style.base_layout(margin=dict(l=8, r=16, t=40, b=40), barmode="stack", bargap=0.3,
                                        showlegend=True, legend=dict(style.legend_top(), traceorder="normal"),
                                        xaxis=style.value_axis(ticksuffix="%", range=[0, 100]),
                                        yaxis=style.axis(automargin=True, autorange="reversed",
                                                         tickfont=dict(color=style.INK_2, size=12))))
    top = regions.iloc[0]
    out = w.rename_axis("region").reset_index()
    out["region"] = labels
    out.columns = ["region", "agree", "neither", "disagree", "not_stated"]
    Chart(
        id="childcare-affordable-access", topic=TOPIC, height=440,
        title="Access to affordable childcare",
        subtitle="Households asked whether they have access to affordable childcare in their community, by region, 2016.",
        sources=[Source.cso("CCA21", "Households who have access to affordable childcare in their community")],
        notes=["From a module on childcare in the CSO's Quarterly National Household Survey in the third quarter of 2016. "
               "This is the most recent official survey to ask the question. Childcare costs and supports have changed "
               "since then, including the National Childcare Scheme, which began in 2019.",
               "Regions are the eight NUTS 3 regions of the time. Shares may not add to 100% because of rounding."],
        key_fact=f"In 2016, {state['Disagree']:.0f}% of households disagreed that they had access to affordable childcare "
                 f"in their community, and {state['Agree']:.0f}% agreed. Disagreement was highest in "
                 f"{regions.index[0]}, at {top['Disagree']:.0f}%.",
        data=out, figure=fig,
    ).write()


TYPES = {"Unpaid relative or family member": "Unpaid relative or family member",
         "Paid relative or family member": "Paid relative or family member",
         "Childminder (in childminders home)": "Childminder, in the childminder's home",
         "Au pair/nanny/childminder (in childs home)": "Au pair, nanny or childminder, in the child's home",
         "Creche/montessori/playgroup/after school": "Crèche, Montessori, playgroup or after-school"}


def types():
    df = cso.fetch("F3050")
    df = df[(df.Sex == "Both sexes") & (df["Administrative Counties"] == "Ireland") &
            (df["Statistic Label"] == "Percentage of Children under 15 years of age in childcare") &
            df.Age.isin(["0 - 2 years", "3 - 4 years"]) & df["Type of Childcare"].isin(TYPES)]
    w = df.pivot_table(index="Type of Childcare", columns="Age", values="VALUE").reindex(list(TYPES)).rename(index=TYPES)
    w = w.rename(columns={"0 - 2 years": "aged_0_to_2", "3 - 4 years": "aged_3_to_4"}).rename_axis("type").reset_index()
    counts = cso.fetch("F3050")
    counts = counts[(counts.Sex == "Both sexes") & (counts["Administrative Counties"] == "Ireland") &
                    (counts["Type of Childcare"] == "All children aged under 15 years of age") &
                    (counts["Statistic Label"] == "Children under 15 years of age (Number) in childcare")]
    n = counts.set_index("Age").VALUE
    fig = go.Figure()
    for col, name, colour in [("aged_0_to_2", "Aged 0 to 2", style.BLUE), ("aged_3_to_4", "Aged 3 to 4", style.GOLD)]:
        fig.add_bar(y=w.type, x=w[col], name=name, orientation="h", marker=dict(color=colour, cornerradius=3),
                    text=[f"{v:.0f}%" for v in w[col]], textposition="outside", cliponaxis=False,
                    textfont=dict(color=style.INK, size=12),
                    hovertemplate=f"<b>%{{y}}</b><br>{name}: %{{x:.1f}}%<extra></extra>")
    fig.update_layout(style.base_layout(margin=dict(l=8, r=40, t=40, b=32), bargap=0.3, bargroupgap=0.08,
                                        barmode="group", showlegend=True, legend=style.legend_top(),
                                        xaxis=style.value_axis(ticksuffix="%"),
                                        yaxis=style.axis(automargin=True, autorange="reversed",
                                                         tickfont=dict(color=style.INK_2, size=12))))
    r = w.set_index("type")
    Chart(
        id="childcare-types", topic=TOPIC, height=420,
        title="Types of childcare used",
        subtitle="Children in childcare, by the type of childcare they mainly use and by age, 2022.",
        sources=[Source.cso("F3050", "Census of Population 2022, children under 15 in childcare")],
        notes=["From the 2022 census, which asked about the childcare each child mainly used. Shares are of children in "
               "any childcare, not of all children. A small number in other or unstated types are left out, so the "
               "shares add to a little under 100%.",
               f"The census counted {n['0 - 2 years']:,.0f} children aged 0 to 2 and {n['3 - 4 years']:,.0f} aged 3 to 4 "
               "in childcare."],
        key_fact=f"In 2022, {r.loc['Crèche, Montessori, playgroup or after-school', 'aged_0_to_2']:.0f}% of children aged "
                 f"0 to 2 in childcare were mainly in a crèche or similar setting, and "
                 f"{r.loc['Unpaid relative or family member', 'aged_0_to_2']:.0f}% were cared for by an unpaid relative.",
        data=w, figure=fig,
    ).write()


def fees_eu():
    raw = eurydice.table("B5", ["vl", "l", "m", "h", "free", "nd", "vl3", "l3", "m3", "free3", "nd3",
                                "under3_pps", "under3_euro_or_national", "over3_pps", "over3_national"])
    d = _eu_rows(raw)
    d["value"] = d.under3_pps.map(lambda v: 0.0 if str(v).strip() == "No fees" else _num(v))
    shown = d.dropna(subset=["value"]).copy()
    left_out = sorted(d[d.value.isna()].country)
    shown["geo"] = shown.country.map({"Ireland": "IE"}).fillna("")
    shown = shown.sort_values(["value", "country"], ascending=[False, True]).reset_index(drop=True)
    ie = d.set_index("country").loc["Ireland"]
    higher = int((shown.value > float(ie.under3_pps)).sum())
    fig = eu.bars(shown[["country", "geo", "value"]], ".0f")
    fig.data[0].text = ["Free" if v == 0 else f"{v:.0f}" for v in shown.value.iloc[::-1]]
    Chart(
        id="childcare-fees-eu", topic=TOPIC, height=600,
        title="Childcare fees for under-3s across the EU",
        subtitle="Average monthly fees for early childhood education and care for children under 3, after state "
                 "supports, in purchasing power standards (PPS), EU countries, 2023/2024.",
        sources=[eurydice.source("Figure B5")],
        notes=["Fees after deducting state subsidies and tax benefits, for full-time attendance where no average is "
               "available. Purchasing power standards adjust for differences in prices between countries, so one PPS "
               "buys about the same amount everywhere.",
               f"In Ireland the average fee was €{float(ie.under3_euro_or_national):.0f} a month, which Eurydice converts "
               f"to {float(ie.under3_pps):.0f} PPS. For children aged 3 and over it was €{float(ie.over3_national):.0f}, or "
               f"{float(ie.over3_pps):.0f} PPS, alongside the free preschool hours of the ECCE scheme.",
               f"Countries that give only a range or a maximum, or no figure, are left out: {', '.join(left_out)}. Belgium's figure is "
               "for the Flemish Community."],
        key_fact=f"Childcare for children under 3 in Ireland cost an average of €{float(ie.under3_euro_or_national):.0f} a "
                 f"month after state supports in 2023/2024. Adjusted for prices, "
                 + ("this was the highest" if higher == 0 else f"{higher} countries were higher")
                 + f" of the {len(shown)} EU countries that give a single figure.",
        data=d[["country", "under3_pps", "under3_euro_or_national", "over3_pps", "over3_national"]], figure=fig,
    ).write()


POBAL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "pobal")
POBAL = Source("Pobal", "Annual Early Years Sector Profile reports, 2016/2017 to 2020/2021",
               "https://www.pobal.ie/EarlyLearningandChildcaredata",
               licence="Quoted with acknowledgement", licence_url="")
POBAL_STOPS = ("Pobal published these figures in a yearly report until 2020/21. From 2021/22 the report was replaced by "
               "online dashboards, which have no option to download the figures, so later years are not shown here. "
               "Since September 2022, services in the Core Funding scheme have had their fees capped at the level they "
               "charged in September 2021.")
POBAL_METHOD = ("Each service reports its weekly fee for one child attending five days a week, for each age group, "
                "including any part paid by State subsidies such as ECCE. Pobal takes the median of each service's fees and "
                "averages these across services. Full day care is more than 5 hours a day, part-time 3.5 to 5 hours, and "
                "sessional about 2.25 to 3.5 hours.")


def fees_trend():
    w = pd.read_csv(os.path.join(POBAL_DIR, "fees_national.csv"))
    a, b = w.iloc[0], w.iloc[-1]
    fig = figures.lines(w, "year", {"full_day": "Full day", "part_time": "Part-time", "sessional": "Sessional"},
                        colours=[style.BLUE, style.GOLD, style.AQUA], value_format=".0f", prefix="€", y_range=[0, None])
    fig.update_xaxes(type="category")
    Chart(
        id="childcare-fees-trend", topic=TOPIC,
        title="Weekly childcare fees over time",
        subtitle=f"Average weekly fee per child in early learning and childcare services, by type of care, "
                 f"{a.year} to {b.year}. Not adjusted for inflation.",
        sources=[POBAL],
        notes=[POBAL_METHOD, POBAL_STOPS,
               "Years up to 2014 are labelled as Pobal labels them. From 2015/16 the figures are for a programme year."],
        key_fact=f"In {b.year}, the average weekly fee for full day childcare was €{b.full_day:.0f}, compared with "
                 f"€{a.full_day:.0f} in {a.year}. These are the latest figures in Pobal's yearly reports.",
        data=w.drop(columns="report"), figure=fig,
    ).write()


def fees_county():
    d = pd.read_csv(os.path.join(POBAL_DIR, "fees_by_county_2020_21.csv"))
    ie = d[d.area == "Ireland"].iloc[0]
    d = d[d.area != "Ireland"].sort_values("full_day", ascending=False).reset_index(drop=True)
    hi, lo = d.iloc[0], d.iloc[-1]
    colours = [style.ORANGE if v > ie.full_day else style.BLUE for v in d.full_day]
    fig = hbars(d, "area", "full_day", ".0f", "", colour=colours)
    fig.data[0].text = [f"€{v:.0f}" for v in d.full_day]
    fig.data[0].hovertemplate = "<b>%{y}</b>: €%{x:.2f} a week<extra></extra>"
    fig.update_xaxes(tickprefix="€")
    fig.add_vline(x=ie.full_day, line=dict(color=style.INK_3, width=1, dash="dot"))
    Chart(
        id="childcare-fees-county", topic=TOPIC, height=720,
        title="Weekly childcare fees by county",
        subtitle="Average weekly fee per child for full day childcare, by county or council area, 2020/21. "
                 "Orange bars are above the national average, shown by the dotted line.",
        sources=[POBAL],
        notes=[POBAL_METHOD, POBAL_STOPS,
               "Dublin and Cork are shown by council area, as Pobal publishes them. The data file also has part-time "
               "and sessional fees. The same table was given in a Dáil written answer in May 2024."],
        key_fact=f"In 2020/21, the average weekly fee for full day childcare was €{hi.full_day:.0f} in {hi.area}, the "
                 f"highest, and €{lo.full_day:.0f} in {lo.area}, the lowest. The national average was "
                 f"€{ie.full_day:.0f}.",
        data=d, figure=fig,
    ).write()


HP_AREAS = {"Dun Laoghaire/Rathdown": "Dún Laoghaire-Rathdown", "Dublin Fingal": "Fingal",
            "South County Dublin": "South Dublin", "County Cork": "Cork County", "County Galway": "Galway",
            "Galway City": "Galway", "County Limerick": "Limerick", "Limerick City": "Limerick",
            "County Waterford": "Waterford", "Waterford City": "Waterford", "Tipperary NR": "Tipperary",
            "Tipperary SR": "Tipperary"}


def fees_deprivation():
    hp = pd.read_csv(os.path.join(POBAL_DIR, "hp_index_2016_ed.csv"))
    hp["area"] = hp.area.replace(HP_AREAS)
    hp["weighted"] = hp.relative_score * hp.population
    a = hp.groupby("area")[["weighted", "population"]].sum()
    a = (a.weighted / a.population).round(1).rename("deprivation_score").reset_index()
    f = pd.read_csv(os.path.join(POBAL_DIR, "fees_by_county_2020_21.csv"))
    d = f[f.area != "Ireland"].merge(a, on="area", how="left")
    assert d.deprivation_score.notna().all(), d[d.deprivation_score.isna()].area.tolist()
    top = d.set_index("area").loc["Dún Laoghaire-Rathdown"]
    low = d[d.deprivation_score < 0]
    below_n = int((low.full_day < 185).sum())
    dub = d.area.isin(["Dún Laoghaire-Rathdown", "Fingal", "South Dublin", "Dublin City"])
    fig = go.Figure()
    for mask, name, colour in [(~dub, "Other counties and cities", style.BLUE), (dub, "Dublin council areas", style.ORANGE)]:
        p = d[mask]
        fig.add_scatter(x=p.deprivation_score, y=p.full_day, mode="markers", name=name,
                        marker=dict(color=colour, size=10, line=dict(color="#ffffff", width=1)), text=p.area,
                        hovertemplate="<b>%{text}</b><br>Deprivation index: %{x:+.1f}<br>Full day fee: €%{y:.0f} a week"
                                      "<extra></extra>")
    for _, row in d[d.area.isin(["Dún Laoghaire-Rathdown", "Carlow", "Donegal", "Wicklow", "Kildare",
                                 "Longford", "Meath"])].iterrows():
        fig.add_annotation(x=row.deprivation_score, y=row.full_day, text=row.area, showarrow=False, yshift=12,
                           font=dict(size=11, color=style.INK_2))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=16, t=40, b=48), showlegend=True,
                                        legend=style.legend_top(),
                                        xaxis=style.value_axis(title=dict(text="More deprived ← average Pobal HP Deprivation "
                                                                              "Index score, 2016 → more affluent",
                                                                         font=dict(size=12, color=style.INK_3)),
                                                               zeroline=True, zerolinecolor=style.CONTEXT),
                                        yaxis=style.value_axis(tickprefix="€")))
    Chart(
        id="childcare-fees-deprivation", topic=TOPIC, height=520,
        title="Childcare fees and affluence",
        subtitle="Average weekly fee for full day childcare in 2020/21, against the average Pobal HP Deprivation Index "
                 "score in 2016, by county or council area.",
        sources=[POBAL, Source("Pobal", "Pobal HP Deprivation Index 2016, scores by electoral division "
                                       "(Haase and Pratschke)", "https://www.pobal.ie/",
                               licence="Quoted with acknowledgement", licence_url="")],
        notes=[POBAL_METHOD, POBAL_STOPS,
               "The deprivation score for each area is the population-weighted average of the 2016 relative scores of "
               "its electoral divisions. The 2016 index is used because it is closer in time to the 2020/21 fees. "
               "Higher scores mean more affluent areas.",
               "Galway, Limerick and Waterford cities are combined with their counties, as in Pobal's fee table.",
               "More affluent areas are also more often urban, and Pobal reports that fees are higher in urban areas, "
               "so the chart does not show that one causes the other."],
        key_fact=f"In 2020/21, childcare fees were generally higher in more affluent areas. Dún Laoghaire-Rathdown, "
                 f"the most affluent area on the index, had the highest full day fee, at €{top.full_day:.0f} a week, while "
                 f"{below_n} of the {len(low)} areas with below-average scores had fees under €185.",
        data=d[["area", "full_day", "part_time", "sessional", "deprivation_score"]], figure=fig,
    ).write()


# Weeks of leave, from NI Direct (Northern Ireland, 2026/27) and the National Women's Council's
# Close the Gap booklet (Ireland, March 2026), which lists the entitlements from Citizens Information.
LEAVE = [
    # (type, place, paid weeks, unpaid weeks)
    ("Maternity", "Ireland", 26, 16),
    ("Maternity", "Northern Ireland", 39, 13),
    ("Adoptive", "Ireland", 24, 16),
    ("Adoptive", "Northern Ireland", 39, 13),
    ("Paternity", "Ireland", 2, 0),
    ("Paternity", "Northern Ireland", 2, 0),
    ("Parent's leave", "Ireland", 9, 0),
    ("Parental leave (unpaid)", "Ireland", 0, 26),
    ("Parental leave (unpaid)", "Northern Ireland", 0, 18),
]
NWCI = Source("National Women's Council", "Close the Gap: an information booklet on the gap between family leave and "
              "childcare (March 2026)",
              "https://togetherforpublic.nwci.ie/close-the-gap-an-information-booklet-on-the-gap-between-family-leave-and-childcare/",
              licence="Quoted with acknowledgement", licence_url="")
NIDIRECT = Source("NI Direct", "Statutory maternity, paternity, adoption and parental leave and pay",
                  "https://www.nidirect.gov.uk/articles/statutory-maternity-leave",
                  licence="Open Government Licence v3.0",
                  licence_url="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/")


def leave_ireland_ni():
    w = pd.DataFrame(LEAVE, columns=["leave", "place", "paid_weeks", "unpaid_weeks"])
    w["label"] = w.leave + " · " + w.place
    shown = w.iloc[::-1]
    fig = go.Figure()
    fig.add_bar(y=shown.label, x=shown.paid_weeks, name="Paid weeks", orientation="h",
                marker=dict(color=[style.ORANGE if p == "Ireland" else style.BLUE for p in shown.place]),
                hovertemplate="<b>%{y}</b><br>Paid: %{x} weeks<extra></extra>")
    fig.add_bar(y=shown.label, x=shown.unpaid_weeks, name="Unpaid weeks", orientation="h",
                marker=dict(color=style.CONTEXT), hovertemplate="<b>%{y}</b><br>Unpaid: %{x} weeks<extra></extra>")
    fig.update_layout(style.base_layout(margin=dict(l=8, r=24, t=40, b=40), barmode="stack", bargap=0.3,
                                        showlegend=False,
                                        xaxis=style.value_axis(ticksuffix=" wks"),
                                        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=12))))
    Chart(
        id="childcare-leave-ireland-ni", topic=TOPIC, height=460,
        title="Family leave in Ireland and Northern Ireland",
        subtitle="Weeks of statutory family leave for employees, by type of leave, 2026. Coloured bars are paid weeks "
                 "(orange for Ireland, blue for Northern Ireland) and grey bars are unpaid weeks.",
        sources=[NWCI, NIDIRECT],
        notes=["Statutory minimums for employees. Employers may offer more. Eligibility rules, such as social insurance "
               "contributions in Ireland or length of service in Northern Ireland, are not shown.",
               "In Ireland, maternity, adoptive, paternity and parent's benefit are paid at a flat rate of €299 a week "
               "(from 2026). In Northern Ireland, maternity and adoption pay is 90% of average earnings for the first six "
               "weeks, then £194.32 a week or 90% of earnings if less (2026/27), and paternity pay is £194.32 a week or "
               "90% of earnings if less.",
               "In Ireland, each parent gets 9 weeks of parent's leave in a child's first two years, and 26 weeks of unpaid "
               "parental leave before the child turns 12. In Northern Ireland, each parent gets 18 weeks of unpaid "
               "parental leave before the child turns 18, and parents can share part of the maternity or adoption leave "
               "as shared parental leave. Paternity leave in Northern Ireland can be one or two weeks.",
               "In Northern Ireland, intended parents in a surrogacy arrangement who apply for a parental order can "
               "qualify for adoption leave and pay. Surrogacy leave in Ireland is not shown."],
        key_fact="Maternity leave in Ireland is 26 paid weeks plus 16 unpaid, paid at a flat €299 a week. In Northern "
                 "Ireland it is 39 paid weeks plus 13 unpaid, with the first six weeks at 90% of earnings.",
        data=w[["leave", "place", "paid_weeks", "unpaid_weeks"]], figure=fig,
    ).write()


def paternity_uptake():
    df = cso.fetch("EMP31")
    df = df[df["Nace Rev 2 Activity"] == "All NACE Economic Sector"]
    w = df[["Year", "VALUE"]].rename(columns={"Year": "year", "VALUE": "uptake"})
    w["year"] = w.year.astype(int)
    a, b = w.iloc[0], w.iloc[-1]
    low = w.loc[w.uptake.idxmin()]
    fig = figures.lines(w, "year", {"uptake": "Uptake"}, colours=[style.BLUE], value_format=".0f", suffix="%",
                        y_range=[0, 100])
    Chart(
        id="childcare-paternity-uptake", topic=TOPIC,
        title="Fathers taking paternity benefit",
        subtitle=f"Share of eligible fathers in employment who took paternity benefit, {a.year:.0f} to {b.year:.0f}.",
        sources=[Source.cso("EMP31", "Rate of paternity benefit uptake")],
        notes=["Paternity benefit is paid by the State to employees and the self-employed who take paternity leave and "
               "have enough social insurance contributions. Fathers whose employer pays them in full during the leave may "
               "still claim it. The CSO links benefit records to employment records to work out the share of new fathers "
               "in employment who claimed it."],
        key_fact=f"In {b.year:.0f}, {b.uptake:.0f}% of eligible fathers in employment took paternity benefit, compared "
                 f"with {a.uptake:.0f}% in {a.year:.0f}. The lowest in the period was {low.uptake:.0f}% in {low.year:.0f}.",
        data=w, figure=fig,
    ).write()
