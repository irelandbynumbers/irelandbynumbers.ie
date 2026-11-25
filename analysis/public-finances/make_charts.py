"""Public finances: where the State's money comes from, what it is spent on,
the surplus or deficit, and government debt. From the CSO's government
finance statistics, which follow the EU's ESA 2010 rules."""
import pandas as pd
import plotly.graph_objects as go

from ibn import cso, eu, eurostat, figures, per, style
from ibn.chart import Chart, Source

TOPIC = "public-finances"
GG_NOTE = ("Figures are for general government, which covers central government, local authorities and other public "
           "bodies, measured under the EU's ESA 2010 rules. They differ from the Exchequer figures the Department of "
           "Finance publishes each month, which cover central government only.")
NOMINAL = "Figures are in current prices, not adjusted for inflation."

EU_GEO = eurostat.EU27 + [eurostat.EU]


def build():
    revenue()
    tax_trends()
    spending()
    flows()
    by_purpose()
    departments()
    departments_next_year()
    balance()
    debt()
    eu_comparisons()


def _item(df, code):
    """Rows for one ESA 2010 item, picked by the code in brackets at the end of its label."""
    return df[df.Item.str.contains(code, regex=False)]


def _bars(d, label, value, money=True):
    fig = go.Figure(go.Bar(y=d[label], x=d[value], orientation="h", marker=dict(color=style.BLUE, cornerradius=4),
                           text=[f"€{v:.1f}bn" for v in d[value]], textposition="outside", cliponaxis=False,
                           textfont=dict(color=style.INK, size=12),
                           hovertemplate="<b>%{y}</b>: €%{x:.1f} billion<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=64, t=8, b=32), bargap=0.3,
                                        xaxis=style.value_axis(tickprefix="€", ticksuffix="bn"),
                                        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=12))))
    return fig


def revenue():
    df = cso.fetch("GFA03")
    year = int(df.Year.max())
    y = df[df.Year == year]
    v = lambda code: float(_item(y, code).VALUE.iloc[0])
    total, taxes = v("Code (TR)"), v("Code (D2 + D5 + D91)")
    income, corporation, vat = v("Income tax"), v("Corporation tax"), v("Code (D211)")
    social = v("Total Social contributions")
    rows = [("Income tax", income), ("Corporation tax", corporation), ("VAT", vat),
            ("Social insurance (PRSI)", social), ("Other taxes", taxes - income - corporation - vat),
            ("Other revenue", total - taxes - social)]
    d = pd.DataFrame(rows, columns=["source", "euro_million"])
    d["euro_billion"] = (d.euro_million / 1000).round(1)
    d["percent"] = (d.euro_million / total * 100).round(1)
    d = d.sort_values("euro_million").reset_index(drop=True)
    Chart(
        id="public-finances-revenue", topic=TOPIC, height=420,
        title="Where the State's money comes from",
        subtitle=f"General government revenue by source, € billion, {year}.",
        sources=[Source.cso("GFA03", "General Government: Detailed classification of revenue and output")],
        notes=[GG_NOTE,
               "Income tax includes the Universal Social Charge. Social insurance is mainly Pay Related Social Insurance "
               "(PRSI) paid by employees, employers and the self-employed. Other taxes include excise duties, stamp duty, "
               "local property tax, motor tax and capital taxes. Other revenue includes fees, sales and investment income."],
        key_fact=f"In {year} the State raised €{total / 1000:.0f} billion. Income tax brought in €{income / 1000:.1f} billion "
                 f"and corporation tax €{corporation / 1000:.1f} billion, together almost half of the total.",
        data=d.iloc[::-1][["source", "euro_million", "euro_billion", "percent"]].reset_index(drop=True),
        figure=_bars(d, "source", "euro_billion"),
    ).write()


def tax_trends():
    df = cso.fetch("GFA03")
    names = {"Income tax": "income_tax", "Corporation tax": "corporation_tax", "Code (D211)": "vat"}
    d = pd.concat([_item(df, k).set_index("Year").VALUE.rename(v) for k, v in names.items()], axis=1).reset_index()
    for c in names.values():
        d[c] = (d[c] / 1000).round(2)
    d["Year"] = d.Year.astype(int)
    fig = figures.lines(d, "Year", {"income_tax": "Income tax", "corporation_tax": "Corporation tax", "vat": "VAT"},
                        value_format=".1f", prefix="€", suffix="bn", y_range=[0, d[list(names.values())].max().max() * 1.1])
    a, b = d.iloc[0], d.iloc[-1]
    Chart(
        id="public-finances-tax-trends", topic=TOPIC,
        title="The three biggest taxes",
        subtitle=f"Revenue from income tax, corporation tax and VAT, € billion, {a.Year:.0f} to {b.Year:.0f}.",
        sources=[Source.cso("GFA03", "General Government: Detailed classification of revenue and output")],
        notes=[GG_NOTE, NOMINAL,
               "Corporation tax is paid on company profits. A large share comes from a small number of multinational "
               "companies, so it can rise or fall sharply from year to year."],
        key_fact=f"Corporation tax brought in €{b.corporation_tax:.1f} billion in {b.Year:.0f}, up from "
                 f"€{a.corporation_tax:.1f} billion in {a.Year:.0f}.",
        data=d, figure=fig,
    ).write()


def spending():
    df = cso.fetch("GFA04")
    year = int(df.Year.max())
    y = df[df.Year == year]
    v = lambda code: float(_item(y, code).VALUE.iloc[0])
    total = v("Code (TE)")
    rows = [("Social welfare and other benefits", v("Code (D62 + D632)")),
            ("Pay of public sector staff", v("Compensation of employees - ESA2010 Code (D1)")),
            ("Goods and services", v("Code (P2 + D5 + D29)")),
            ("Investment in buildings, roads and equipment", v("Depreciation (Consumption of fixed capital) - ESA2010 Code (P51c)")
             + v("Code (P5 + NP - P51c)")),
            ("Grants, subsidies and transfers", v("Subsidies - ESA2010 Code (D3)") + v("Other current transfers - ESA2010 Code (D7)")
             + v("Capital transfers - ESA2010 Code (D9)")),
            ("Interest on debt", v("Code (D41)"))]
    d = pd.DataFrame(rows, columns=["category", "euro_million"])
    assert abs(d.euro_million.sum() - total) < 2, "spending categories should add up to the total"
    d["euro_billion"] = (d.euro_million / 1000).round(1)
    d["percent"] = (d.euro_million / total * 100).round(1)
    d = d.sort_values("euro_million").reset_index(drop=True)
    top = d.iloc[-1]
    Chart(
        id="public-finances-spending", topic=TOPIC, height=420,
        title="What the State spends money on",
        subtitle=f"General government spending by type, € billion, {year}.",
        sources=[Source.cso("GFA04", "General Government: Detailed classification of expenditure and consumption")],
        notes=[GG_NOTE,
               "Spending is grouped by type rather than by service. Social welfare and other benefits include pensions, "
               "jobseeker payments, child benefit, and services such as medical cards that the State pays others to "
               "provide. Pay covers wages and the employer's social insurance and pension contributions for public servants, such as "
               "nurses, teachers and Gardaí. Investment is gross capital spending, including the cost of replacing worn-out assets."],
        key_fact=f"The State spent €{total / 1000:.0f} billion in {year}. The largest share, €{top.euro_billion:.1f} billion "
                 f"({top.percent:.0f}%), went on social welfare and other benefits.",
        data=d.iloc[::-1][["category", "euro_million", "euro_billion", "percent"]].reset_index(drop=True),
        figure=_bars(d, "category", "euro_billion"),
    ).write()


def balance():
    df = cso.fetch("GFA10")
    d = df.pivot_table(index="Year", columns="Statistic Label", values="VALUE").reset_index()
    d.columns = ["Year", "euro_million", "percent_of_gdp"]
    d["euro_billion"] = (d.euro_million / 1000).round(1)
    d["Year"] = d.Year.astype(int)
    colours = [style.BLUE if v >= 0 else style.ORANGE for v in d.euro_billion]
    fig = go.Figure(go.Bar(x=d.Year, y=d.euro_billion, marker=dict(color=colours),
                           hovertemplate="<b>%{x}</b>: €%{y:.1f} billion<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=56, r=24, t=16, b=40), bargap=0.2,
                                        xaxis=style.axis(showline=True),
                                        yaxis=style.value_axis(tickprefix="€", ticksuffix="bn")))
    worst = d.loc[d.euro_billion.idxmin()]
    b = d.iloc[-1]
    surplus_years = d[(d.euro_billion > 0) & (d.Year >= 2018)].Year
    Chart(
        id="public-finances-balance", topic=TOPIC,
        title="Government surplus or deficit",
        subtitle=f"General government surplus (above zero) or deficit (below zero), € billion, {d.Year.min():.0f} to {b.Year:.0f}.",
        sources=[Source.cso("GFA10", "General Government Surplus/Deficit ESA2010")],
        notes=[GG_NOTE, NOMINAL,
               "A deficit means the State spent more than it raised in that year, and borrowed to cover the difference. "
               "The deficit in 2010 includes the cost of supporting the banks. The data file also gives each year's "
               "balance as a percentage of GDP."],
        key_fact=f"The State had a surplus of €{b.euro_billion:.1f} billion in {b.Year:.0f}. The largest deficit was "
                 f"€{-worst.euro_billion:.1f} billion, in {worst.Year:.0f}.",
        data=d[["Year", "euro_million", "euro_billion", "percent_of_gdp"]], figure=fig,
    ).write()


def debt():
    df = cso.fetch("GFA13")
    d = _item(df, "(GGDebt)").set_index("Year").VALUE.rename("euro_million").reset_index()
    na = cso.fetch("NA001")
    gni = na[na.Item == "10. Modified gross national income at current market prices"]
    gni = gni.assign(gni_star_billion=(gni.VALUE / 1000).round(1))[["Year", "gni_star_billion"]]
    d = d.merge(gni, on="Year", how="left")
    d["euro_billion"] = (d.euro_million / 1000).round(1)
    d["percent_of_gni_star"] = (d.euro_billion / d.gni_star_billion * 100).round(1)
    d["Year"] = d.Year.astype(int)
    fig = figures.lines(d, "Year", {"euro_billion": "Government debt"}, value_format=".0f", prefix="€", suffix="bn",
                        y_range=[0, d.euro_billion.max() * 1.1])
    peak = d.loc[d.percent_of_gni_star.idxmax()]
    b = d.iloc[-1]
    Chart(
        id="public-finances-debt", topic=TOPIC,
        title="Government debt",
        subtitle=f"Gross general government debt at the end of each year, € billion, {d.Year.min():.0f} to {b.Year:.0f}.",
        sources=[Source.cso("GFA13", "General Government Gross and Net Debt ESA2010"),
                 Source.cso("NA001", "Modified Gross National Income at Current Market Prices")],
        notes=[GG_NOTE, NOMINAL,
               "Gross debt is the total the State owes, at face value. The data file also gives debt as a percentage of "
               "GNI*, a measure of the size of the Irish economy that leaves out most of the effect of multinational "
               "companies, and so is a better guide than GDP to how heavy the debt is for Ireland."],
        key_fact=f"Government debt was €{b.euro_billion:.0f} billion at the end of {b.Year:.0f}, or {b.percent_of_gni_star:.0f}% "
                 f"of GNI*. Relative to GNI*, it peaked in {peak.Year:.0f} at {peak.percent_of_gni_star:.0f}%.",
        data=d[["Year", "euro_million", "euro_billion", "gni_star_billion", "percent_of_gni_star"]], figure=fig,
    ).write()


def eu_comparisons():
    df = eurostat.fetch("gov_10dd_edpt1", geo=EU_GEO, na_item="GD", sector="S13", unit="PC_GDP")
    eu.rank_chart(
        "public-finances-debt-eu", TOPIC, "Government debt across the EU",
        "Gross general government debt, % of GDP, EU countries, {year}.",
        Source.eurostat("gov_10dd_edpt1", "Government deficit/surplus, debt and associated data"), df,
        lambda y, ie, ev, place: f"Ireland's government debt was {ie:.0f}% of GDP in {y}, {place}. The EU average was "
                                 f"{ev:.0f}%.",
        notes=["GDP overstates the size of the Irish economy because of the profits of multinational companies, so "
               "Ireland's debt looks smaller here than it is relative to the incomes of people in Ireland. Measured "
               "against GNI*, Ireland's debt is much higher; see the chart of government debt above."],
        value_format=".0f", suffix="%")


# Spending by purpose, from the EU's classification of the functions of government (COFOG).
# Plainer names for the ten areas, and for the sub-areas whose official names are hard to follow.
AREAS = {
    "GF01": "Government and debt interest", "GF02": "Defence", "GF03": "Police, courts and prisons",
    "GF04": "Transport and the economy", "GF05": "Environment", "GF06": "Housing and water",
    "GF07": "Health", "GF08": "Culture and sport", "GF09": "Education",
    "GF10": "Social protection",
}
SUB_AREAS = {
    "GF0101": "Government, tax collection and foreign affairs", "GF0103": "General services of government",
    "GF0104": "Basic research", "GF0107": "Interest on government debt",
    "GF0108": "Transfers between levels of government", "GF0302": "Fire services",
    "GF0401": "Business, trade and employment supports", "GF0402": "Agriculture, forestry and fishing",
    "GF0403": "Fuel and energy", "GF0404": "Mining, manufacturing and construction",
    "GF0601": "Housing development", "GF0603": "Water supply",
    "GF0701": "Medicines and medical equipment", "GF0702": "GP, dental and other outpatient services",
    "GF0703": "Hospitals", "GF0704": "Public health services",
    "GF0801": "Sport and recreation", "GF0803": "Broadcasting and publishing", "GF0804": "Religious and community services",
    "GF0901": "Pre-primary and primary schools", "GF0902": "Secondary schools",
    "GF0903": "Further education", "GF0904": "Third level", "GF0906": "School transport, meals and other services",
    "GF1001": "Illness and disability", "GF1002": "Old age, including pensions", "GF1003": "Widows, widowers and other survivors",
    "GF1004": "Families and children", "GF1005": "Unemployment", "GF1006": "Housing supports, such as rent supports",
    "GF1007": "Other help for people on low incomes",
}
COFOG_NOTE = ("Spending by purpose follows the EU's classification of the functions of government (COFOG). Eurostat "
              "last revised this breakdown before the CSO's latest totals, so each area has been scaled by the same "
              "small amount so that the areas add up to the CSO's total spending for the year. The adjustment is "
              "{adj} or less in every year shown.")
POOLED_NOTE = ("Taxes and other revenue go into a common pool rather than being set aside for particular services, so "
               "the chart shows totals in and out, not which tax pays for which service. The main exception is "
               "PRSI, which is paid into the Social Insurance Fund and pays for State pensions and other social "
               "insurance benefits. That fund is part of general government, so it is included in both sides.")


def _sub_label(code, label):
    if code in SUB_AREAS:
        return SUB_AREAS[code]
    label = label.replace(" n.e.c.", ", other")
    return label[0].upper() + label[1:]


def _cofog():
    """COFOG spending by area and sub-area, € million, scaled to the CSO's total spending for each year.
    Returns the rows and the largest scaling adjustment, in percent."""
    df = eurostat.fetch("gov_10a_exp", name="gov_cofog_ie", geo="IE", sector="S13", na_item="TE", unit="MIO_EUR")
    df = df[df.time >= 2000]
    te = _item(cso.fetch("GFA04"), "Code (TE)").set_index("Year").VALUE
    rows, adj = [], 0.0
    for year, y in df.groupby("time"):
        total = float(y[y.cofog99 == "TOTAL"].value.iloc[0])
        factor = float(te.loc[year]) / total
        adj = max(adj, abs(factor - 1) * 100)
        for _, r in y[y.cofog99.str.len() == 6].iterrows():
            rows.append(dict(Year=int(year), area_code=r.cofog99[:4], area=AREAS[r.cofog99[:4]],
                             sub_area_code=r.cofog99, sub_area=_sub_label(r.cofog99, r.cofog99_label),
                             euro_million=round(r.value * factor, 1)))
    d = pd.DataFrame(rows)
    # Each area's sub-areas should add up to the area as published.
    areas = df[df.cofog99.str.len() == 4].groupby(["time", "cofog99"]).value.sum()
    subs = df[df.cofog99.str.len() == 6].assign(a=lambda x: x.cofog99.str[:4]).groupby(["time", "a"]).value.sum()
    assert (areas.values - subs.reindex(areas.index).values).__abs__().max() < 5, "COFOG sub-areas should add up"
    return d, adj


def _revenue_by_source():
    """General government revenue by source, € million, for every year, as in the revenue chart."""
    df = cso.fetch("GFA03")
    out = []
    for year, y in df.groupby("Year"):
        v = lambda code: float(_item(y, code).VALUE.iloc[0])
        total, taxes = v("Code (TR)"), v("Code (D2 + D5 + D91)")
        income, corporation, vat = v("Income tax"), v("Corporation tax"), v("Code (D211)")
        social = v("Total Social contributions")
        for source, value in [("Income tax and USC", income), ("PRSI", social),
                              ("VAT", vat), ("Corporation tax", corporation),
                              ("Other taxes", taxes - income - corporation - vat),
                              ("Other revenue", total - taxes - social)]:
            out.append(dict(Year=int(year), source=source, euro_million=value))
    return pd.DataFrame(out)


def flows():
    """Money in, by source, and money out, by purpose, as a flow chart with a year slider."""
    cofog, adj = _cofog()
    rev = _revenue_by_source()
    balance = cso.fetch("GFA10")
    balance = balance[balance.UNIT == "Euro Million"].set_index("Year").VALUE
    years = sorted(set(cofog.Year) & set(rev.Year))
    sources = list(rev.source.unique())
    rows = []
    for year in years:
        r = rev[rev.Year == year]
        s = cofog[cofog.Year == year].groupby("area").euro_million.sum().sort_values(ascending=False)
        inflow, outflow = r.euro_million.sum(), s.sum()
        assert abs((inflow - outflow) - float(balance.loc[year])) < 5, f"revenue less spending should equal the balance in {year}"
        for _, x in r.iterrows():
            rows.append(dict(Year=year, direction="in", item=x.source, euro_million=round(x.euro_million, 1)))
        if inflow < outflow:
            rows.append(dict(Year=year, direction="in", item="Borrowing", euro_million=round(outflow - inflow, 1)))
        for area, value in s.items():
            rows.append(dict(Year=year, direction="out", item=area, euro_million=round(value, 1)))
        if inflow > outflow:
            rows.append(dict(Year=year, direction="out", item="Surplus", euro_million=round(inflow - outflow, 1)))
    d = pd.DataFrame(rows)
    d["euro_billion"] = (d.euro_million / 1000).round(1)

    in_colour = {s: style.BLUE for s in sources} | {"Borrowing": style.RED}
    out_colour = {"Surplus": style.AQUA}
    POOL = "Public money"

    def rgba(hex_, a):
        h = hex_.lstrip("#")
        return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"

    def trace(year):
        y = d[d.Year == year]
        ins, outs = y[y.direction == "in"], y[y.direction == "out"]
        total_in = ins.euro_million.sum()
        labels = [f"{i} €{v:.1f}bn" for i, v in zip(ins.item, ins.euro_billion)]
        labels += [f"{POOL} €{total_in / 1000:.0f}bn"]
        labels += [f"{i} €{v:.1f}bn" for i, v in zip(outs.item, outs.euro_billion)]
        n_in, pool = len(ins), len(ins)
        colours = [in_colour[i] for i in ins.item] + [style.INK_2] + [out_colour.get(i, style.ORANGE) for i in outs.item]
        share = lambda v: v / total_in * 100
        return go.Sankey(
            arrangement="fixed", valueformat=".1f", valuesuffix="bn",
            textfont=dict(family=style.FONT, size=12, color=style.INK),
            node=dict(label=labels, color=colours, pad=10, thickness=14, line=dict(width=0),
                      customdata=[f"€{v:.1f} billion" for v in list(ins.euro_billion) + [round(total_in / 1000, 1)] + list(outs.euro_billion)],
                      hovertemplate="%{customdata}<extra></extra>"),
            link=dict(source=list(range(n_in)) + [pool] * len(outs),
                      target=[pool] * n_in + list(range(n_in + 1, n_in + 1 + len(outs))),
                      value=list(ins.euro_billion) + list(outs.euro_billion),
                      color=[rgba(in_colour[i], 0.35) for i in ins.item] + [rgba(out_colour.get(i, style.ORANGE), 0.3) for i in outs.item],
                      customdata=[f"<b>{i}</b><br>€{v:.1f} billion, {share(m):.0f}% of the total"
                                  for i, v, m in zip(list(ins.item) + list(outs.item),
                                                     list(ins.euro_billion) + list(outs.euro_billion),
                                                     list(ins.euro_million) + list(outs.euro_million))],
                      hovertemplate="%{customdata}<extra></extra>"),
        )

    latest = years[-1]
    fig = go.Figure(data=[trace(latest)])
    fig.frames = [go.Frame(name=str(y), data=[trace(y)]) for y in years]
    fig.update_layout(style.base_layout(margin=dict(l=8, r=8, t=8, b=70), sliders=[dict(
        active=len(years) - 1, x=0.05, len=0.9, y=0, yanchor="top", pad=dict(t=10, b=0),
        currentvalue=dict(prefix="", font=dict(size=14, color=style.INK)),
        font=dict(color=style.INK_3, size=11), bgcolor=style.LAND, bordercolor=style.GRID, activebgcolor=style.BLUE,
        steps=[dict(label=str(y), method="animate",
                    args=[[str(y)], dict(mode="immediate", frame=dict(duration=0, redraw=True), transition=dict(duration=0))])
               for y in years])]))

    y = d[d.Year == latest]
    total_in = y[y.direction == "in"].euro_million.sum()
    outs = y[(y.direction == "out") & (y.item != "Surplus")].sort_values("euro_million", ascending=False)
    first, second = outs.iloc[0], outs.iloc[1]
    surplus = y[y.item == "Surplus"].euro_billion
    tail = (f" This left a surplus of €{surplus.iloc[0]:.1f} billion."
            if len(surplus) else "")
    Chart(
        id="public-finances-flows", topic=TOPIC, height=640,
        title="Money in and money out",
        subtitle=f"General government revenue by source and spending by purpose, € billion, {years[0]} to {latest}. "
                 "Use the slider to choose a year.",
        sources=[Source.cso("GFA03", "General Government: Detailed classification of revenue and output"),
                 Source.cso("GFA04", "General Government: Detailed classification of expenditure and consumption"),
                 Source.cso("GFA10", "General Government Surplus/Deficit ESA2010"),
                 Source.eurostat("gov_10a_exp", "General government expenditure by function (COFOG)", name="gov_cofog_ie")],
        notes=[GG_NOTE, POOLED_NOTE,
               "In years when the State spends more than it raises, the gap is shown as borrowing. In years when it raises "
               "more than it spends, the difference is shown as a surplus. The surplus in 2024 includes a once-off "
               "payment of tax owed by Apple, following a ruling of the Court of Justice of the European Union. Borrowing in "
               "2010 includes the cost of supporting the banks, which is counted under transport and the economy.",
               COFOG_NOTE.format(adj=f"{adj:.1f}%"),
               "Income tax includes the Universal Social Charge. Social protection covers pensions, jobseeker and "
               "disability payments, child benefit and housing supports. Government and debt interest covers running "
               "departments, collecting taxes, foreign affairs and interest on government debt. Transport and the economy "
               "covers roads and public transport, farming, energy, research and supports for business and employment. "
               "PRSI includes other social contributions, such as those paid by public servants towards their pensions.",
               NOMINAL],
        key_fact=f"In {latest}, €{total_in / 1000:.0f} billion came in. The largest areas of spending were "
                 f"{first['item'].lower()}, at €{first.euro_billion:.1f} billion, and {second['item'].lower()}, at "
                 f"€{second.euro_billion:.1f} billion.{tail}",
        data=d[["Year", "direction", "item", "euro_million", "euro_billion"]], figure=fig,
    ).write()


def by_purpose():
    """Spending in the latest year as a treemap, from ten areas down to sub-areas."""
    cofog, adj = _cofog()
    year = int(cofog.Year.max())
    d = cofog[(cofog.Year == year) & (cofog.euro_million > 0)].copy()
    pop = cso.fetch("PEA01")
    pop = pop[(pop["Age Group"] == "All ages") & (pop["Sex"] == "Both sexes")].set_index("Year").VALUE * 1000
    people = float(pop.loc[year])
    total = d.euro_million.sum()
    d["euro_billion"] = (d.euro_million / 1000).round(2)
    d["percent"] = (d.euro_million / total * 100).round(1)
    d["euro_per_person"] = (d.euro_million * 1e6 / people).round(0).astype(int)
    d = d.sort_values(["area", "euro_million"], ascending=[True, False])

    areas = d.groupby("area").euro_million.sum().sort_values(ascending=False)
    colour = {a: style.SLOTS[i % len(style.SLOTS)] for i, a in enumerate(areas.index)}
    ROOT = "All spending"
    ids = [ROOT] + list(areas.index) + [f"{a}/{s}" for a, s in zip(d.area, d.sub_area)]
    labels = [ROOT] + list(areas.index) + list(d.sub_area)
    parents = [""] + [ROOT] * len(areas) + list(d.area)
    values = [total] + list(areas.values) + list(d.euro_million)
    colours = [style.SURFACE] + [colour[a] for a in areas.index] + [colour[a] for a in d.area]
    custom = [[v / 1000, v / total * 100, v * 1e6 / people] for v in values]
    fig = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=values, branchvalues="total", maxdepth=2,
        marker=dict(colors=colours, line=dict(color=style.SURFACE, width=1.5)),
        customdata=custom, texttemplate="<b>%{label}</b><br>€%{customdata[0]:.1f}bn", textfont=dict(family=style.FONT),
        hovertemplate="<b>%{label}</b><br>€%{customdata[0]:.2f} billion, %{customdata[1]:.1f}% of all spending"
                      "<br>About €%{customdata[2]:,.0f} per person<extra></extra>",
        pathbar=dict(visible=True, textfont=dict(family=style.FONT, size=13)), tiling=dict(pad=2),
        root=dict(color=style.SURFACE)))
    fig.update_layout(style.base_layout(margin=dict(l=0, r=0, t=28, b=0)))

    health = areas.get("Health", 0)
    Chart(
        id="public-finances-by-purpose", topic=TOPIC, height=600,
        title="What public money is spent on",
        subtitle=f"General government spending by purpose, € billion, {year}. Select an area to see what it is made up of.",
        sources=[Source.eurostat("gov_10a_exp", "General government expenditure by function (COFOG)", name="gov_cofog_ie"),
                 Source.cso("GFA04", "General Government: Detailed classification of expenditure and consumption"),
                 Source.cso("PEA01", "Population Estimates (Persons in April)")],
        notes=[GG_NOTE, COFOG_NOTE.format(adj=f"{adj:.1f}%"),
               "Spending per person divides each amount by the estimated population in April of the same year.",
               "Some spending is counted under its purpose rather than the department that pays it. For example, rent "
               "supports appear under social protection, and school transport under education."],
        key_fact=f"Public spending in {year} came to about €{total * 1e6 / people:,.0f} for every person living in "
                 f"the State, including €{health * 1e6 / people:,.0f} on health.",
        data=d[["Year", "area", "sub_area", "sub_area_code", "euro_million", "euro_billion", "percent", "euro_per_person"]],
        figure=fig,
    ).write()


# Department budgets, from the Appropriation Accounts (audited, planned and actual) and the
# Department of Public Expenditure's Databank (allocations for the current year). These count
# voted spending by government department, which is measured differently from the general
# government figures above, so the two are never added together or compared directly.
ACCOUNTS_YEAR = 2025
VOTED_NOTE = ("These figures are voted spending, the money the Dáil approves for each government department and office "
              "each year, grouped into Votes. They are counted in cash, by department, and do not include spending by "
              "local authorities from their own income, interest on the national debt, or the Social Insurance Fund, "
              "which pays the State Pension (Contributory) and other social insurance benefits. They are measured "
              "differently from the general government figures in the charts above, so the totals do not match.")
GROSS_NOTE = ("Amounts are gross spending, before deducting appropriations-in-aid, which are receipts a department "
              "keeps, such as pension contributions from staff and EU funding.")


def _money(thousand):
    """€ thousand as plain words: €2.3 billion, €451 million, €350,000."""
    v = thousand * 1000
    if abs(v) >= 1e9:
        return f"€{v / 1e9:.1f} billion"
    if abs(v) >= 1e6:
        return f"€{v / 1e6:.1f} million" if abs(v) < 1e7 else f"€{v / 1e6:.0f} million"
    return f"€{v:,.0f}"


def _against_plan(planned, spent):
    if planned <= 0:
        return "No amount was set aside for this in the estimate." if spent > 0 else ""
    diff = (spent - planned) / planned * 100
    if abs(diff) < 0.5:
        return "Spending was in line with the plan."
    gap = _money(abs(spent - planned))
    return f"{gap} ({abs(diff):.0f}%) {'more' if diff > 0 else 'less'} than planned."


SEARCH_HTML = """<div class="dept-search">
  <label for="dept-q">Search for a scheme, service or department</label>
  <input id="dept-q" type="search" autocomplete="off" placeholder="For example, Child Benefit or school transport">
  <ul id="dept-results" role="listbox" hidden></ul>
</div>
<style>
  .dept-search { position: relative; margin: 0 0 8px; max-width: 520px; }
  .dept-search label { display: block; font-size: 13px; margin-bottom: 2px; }
  .dept-search input { width: 100%; font: inherit; padding: 6px 10px; border: 1px solid #c9c7c0; border-radius: 4px; }
  .dept-search ul { position: absolute; z-index: 5; left: 0; right: 0; margin: 2px 0 0; padding: 0; list-style: none;
    background: #fff; border: 1px solid #c9c7c0; border-radius: 4px; max-height: 280px; overflow: auto; }
  .dept-search li { padding: 6px 10px; cursor: pointer; font-size: 14px; }
  .dept-search li span { color: #8a8984; font-size: 13px; }
  .dept-search li[aria-selected="true"], .dept-search li:hover { background: #f3f2ee; }
</style>"""

SEARCH_JS = r"""
(function () {
  const q = document.getElementById("dept-q"), list = document.getElementById("dept-results");
  const t = FIG.data[0];
  const nodes = t.ids.map((id, i) => ({id, label: t.labels[i], parent: t.parents[i], i}))
    .filter((n) => n.parent !== "");
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const path = (n) => { const out = []; let p = byId[n.parent]; while (p) { out.unshift(p.label); p = byId[p.parent]; } return out; };
  let matches = [], active = -1;
  function show(n) {
    // Open the box that holds the match, so it shows with its neighbours.
    const level = n.id.split("/").length > 1 ? n.parent : n.id;
    Plotly.restyle(gd, {level: [level]}, [0]);
    list.hidden = true; q.value = n.label;
    gd.scrollIntoView({block: "nearest"});
  }
  function render() {
    list.innerHTML = "";
    matches.forEach((n, k) => {
      const li = document.createElement("li");
      li.setAttribute("role", "option"); li.setAttribute("aria-selected", String(k === active));
      li.textContent = n.label + " ";
      const s = document.createElement("span"); s.textContent = path(n).join(" › ") + ", " + t.customdata[n.i][3];
      li.append(s);
      li.addEventListener("mousedown", (e) => { e.preventDefault(); show(n); });
      list.append(li);
    });
    list.hidden = matches.length === 0;
  }
  q.addEventListener("input", () => {
    const words = q.value.toLowerCase().split(/\s+/).filter(Boolean);
    active = -1;
    matches = words.length && q.value.length > 1
      ? nodes.filter((n) => words.every((w) => (n.label + " " + path(n).join(" ")).toLowerCase().includes(w)))
          .sort((a, b) => t.values[b.i] - t.values[a.i]).slice(0, 12)
      : [];
    render();
  });
  q.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" && matches.length) { active = (active + 1) % matches.length; render(); e.preventDefault(); }
    else if (e.key === "ArrowUp" && matches.length) { active = (active - 1 + matches.length) % matches.length; render(); e.preventDefault(); }
    else if (e.key === "Enter" && matches.length) { show(matches[Math.max(active, 0)]); e.preventDefault(); }
    else if (e.key === "Escape") { list.hidden = true; }
  });
  q.addEventListener("blur", () => setTimeout(() => { list.hidden = true; }, 150));
})();
"""


def departments():
    """Every department's spending in the latest audited year, from department to programme to
    subhead, with what was planned and what was spent."""
    year = ACCOUNTS_YEAR
    d = per.accounts(year)
    d["programme_name"] = d.programme_name.fillna("")
    d["planned"], d["spent"] = d.estimate_thousand, d.outturn_thousand
    d["size"] = d.spent.clip(lower=0)
    d = d[(d.planned != 0) | (d.spent != 0)]

    ROOT = "All departments"
    ids, labels, parents, values, planned, spent = [ROOT], [ROOT], [""], [d["size"].sum()], [d.planned.sum()], [d.spent.sum()]
    votes = d.groupby(["vote", "vote_name"])[["size", "planned", "spent"]].sum().reset_index().sort_values("size", ascending=False)
    colour_of = {v: style.SLOTS[i % len(style.SLOTS)] for i, v in enumerate(votes.vote)}
    colours = [style.SURFACE]
    for _, v in votes.iterrows():
        vid = f"v{v.vote}"
        ids.append(vid); labels.append(v.vote_name); parents.append(ROOT)
        values.append(v["size"]); planned.append(v.planned); spent.append(v.spent); colours.append(colour_of[v.vote])
        rows = d[d.vote == v.vote]
        for prog, p in rows.groupby("programme_name", sort=False):
            parent = vid
            if prog and (rows.programme_name.nunique() > 1 or len(p) > 1):
                pid = f"{vid}/{prog}"
                ids.append(pid); labels.append(prog); parents.append(vid)
                values.append(p["size"].sum()); planned.append(p.planned.sum()); spent.append(p.spent.sum())
                colours.append(colour_of[v.vote])
                parent = pid
            for _, s in p.iterrows():
                ids.append(f"{vid}/{s.subhead}"); labels.append(s.subhead_name); parents.append(parent)
                values.append(s["size"]); planned.append(s.planned); spent.append(s.spent); colours.append(colour_of[v.vote])
    total_planned, total_spent = planned[0], spent[0]
    custom = [[_money(s), _money(p), _against_plan(p, s), _money(s).replace(" billion", "bn").replace(" million", "m")]
              for p, s in zip(planned, spent)]
    fig = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=values, branchvalues="total", maxdepth=2, sort=True,
        marker=dict(colors=colours, line=dict(color=style.SURFACE, width=1.5)),
        customdata=custom, texttemplate="<b>%{label}</b><br>%{customdata[3]}", textfont=dict(family=style.FONT),
        hovertemplate="<b>%{label}</b><br>Spent %{customdata[0]}<br>Planned %{customdata[1]}<br>%{customdata[2]}<extra></extra>",
        pathbar=dict(visible=True, textfont=dict(family=style.FONT, size=13)), tiling=dict(pad=2),
        root=dict(color=style.SURFACE)))
    fig.update_layout(style.base_layout(margin=dict(l=0, r=0, t=28, b=0)))

    top = votes.iloc[0]
    out = d[["year", "vote", "vote_name", "programme", "programme_name", "subhead", "subhead_name", "planned", "spent"]].rename(
        columns={"vote": "vote_number", "vote_name": "department", "planned": "planned_euro_thousand",
                 "spent": "spent_euro_thousand"})
    Chart(
        id="public-finances-departments", topic=TOPIC, height=640,
        title="Department budgets and what was spent",
        subtitle=f"Spending by government department, programme and scheme, {year}. Box sizes show what was spent. "
                 "Select a box to see what it is made up of, or search for a scheme.",
        sources=[per.accounts_source(year)],
        notes=[VOTED_NOTE, GROSS_NOTE,
               "Planned spending is the amount the Dáil provided for the year, including any supplementary estimate "
               "agreed later in the year. What was spent is the outturn, audited by the Comptroller and Auditor General. "
               "Each department's account explains the reasons for large differences between the two.",
               "A department's budget is divided into programmes, and each programme into subheads, the lines on which "
               "money is provided and accounted for. Health and Social Protection each have a single programme, so "
               "their subheads are grouped here under the headings used in their accounts.",
               "A few subheads record a small refund rather than spending, and are shown with no size."],
        key_fact=f"Government departments spent {_money(total_spent)} in {year}, {_money(total_planned - total_spent)} less "
                 f"than planned. {top.vote_name} spent the most, {_money(top.spent)}.",
        data=out, figure=fig, controls=SEARCH_HTML, script=SEARCH_JS,
    ).write()


def _key(name):
    """A department's name reduced to its main words, so the same department can be matched across years."""
    import re
    import unicodedata
    n = unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode()
    n = n.replace("&", "and").replace("’", "'")
    n = re.sub(r"'s\b", "", n)
    n = re.sub(r"[^a-z ]", " ", n)
    stop = {"office", "of", "the", "department", "and", "minister", "for", "an", "agus", "employment", "affairs"}
    return frozenset(w for w in n.split() if w not in stop)


def _title(name):
    """The Databank writes names in title case. Lower-case the small words."""
    import re
    small = r"\b(And|Of|The|For|In|On|To|An|Agus)\b"
    name = re.sub(small, lambda m: m.group(1).lower(), name.replace(" & ", " and "))
    return name[0].upper() + name[1:]


def departments_next_year():
    """Each department's allocation for the current year, from the Databank, next to what it spent
    in the latest audited year."""
    db = per.databank()
    year = int(db.year.max())
    cur = db[(db.year == year) & (db.type == "Program") & db.vote.str.fullmatch(r"\d+")]
    alloc = cur.groupby(["vote", "vote_name"]).value.sum().reset_index()
    acc = per.accounts(ACCOUNTS_YEAR).groupby("vote_name").outturn_thousand.sum()
    keys = {_key(n): n for n in acc.index}

    def match(name):
        k = _key(name)
        if k in keys:
            return keys[k]
        for kk, n in keys.items():
            if k and kk and (k <= kk or kk <= k):
                return n
        return None
    alloc["department"] = [match(n) or _title(n) for n in alloc.vote_name]
    alloc["spent_last_year"] = [acc.get(match(n), float("nan")) for n in alloc.vote_name]
    alloc = alloc.sort_values("value", ascending=False).reset_index(drop=True)
    total = alloc.value.sum()

    TOP = 15
    shown = alloc.iloc[:TOP].copy()
    rest = alloc.iloc[TOP:]
    shown.loc[len(shown)] = dict(vote="", vote_name="", department=f"The other {len(rest)} departments and offices",
                                 value=rest.value.sum(), spent_last_year=rest.spent_last_year.sum())
    shown = shown.iloc[::-1]
    bn = lambda s: s / 1e6
    fig = go.Figure([
        go.Bar(y=shown.department, x=bn(shown.value), orientation="h", name=f"Allocated for {year}",
               marker=dict(color=style.BLUE, cornerradius=4),
               text=[f"€{v:.1f}bn" for v in bn(shown.value)], textposition="outside", cliponaxis=False,
               textfont=dict(color=style.INK, size=12),
               hovertemplate=f"<b>%{{y}}</b><br>Allocated for {year}: €%{{x:.2f}} billion<extra></extra>"),
        go.Scatter(y=shown.department, x=bn(shown.spent_last_year), mode="markers", name=f"Spent in {ACCOUNTS_YEAR}",
                   marker=dict(color=style.INK, symbol="line-ns", size=16, line=dict(width=3, color=style.INK)),
                   hovertemplate=f"<b>%{{y}}</b><br>Spent in {ACCOUNTS_YEAR}: €%{{x:.2f}} billion<extra></extra>"),
    ])
    fig.update_layout(style.base_layout(margin=dict(l=8, r=64, t=8, b=32), bargap=0.3, showlegend=True,
                                        legend=style.legend_top(),
                                        xaxis=style.value_axis(tickprefix="€", ticksuffix="bn"),
                                        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=12))))
    top = alloc.iloc[0]
    out = alloc[["vote", "department", "value", "spent_last_year"]].rename(columns={
        "vote": "vote_number", "value": f"allocated_{year}_euro_thousand",
        "spent_last_year": f"spent_{ACCOUNTS_YEAR}_euro_thousand"})
    Chart(
        id="public-finances-departments-budget", topic=TOPIC, height=620,
        title=f"Department budgets for {year}",
        subtitle=f"Gross voted spending allocated to each government department, € billion, {year}, with what each "
                 f"spent in {ACCOUNTS_YEAR}.",
        sources=[per.databank_source(), per.accounts_source(ACCOUNTS_YEAR)],
        notes=[VOTED_NOTE, GROSS_NOTE,
               f"Allocations for {year} are those published by the Department of Public Expenditure, Infrastructure, "
               "Public Service Reform and Digitalisation in its Databank. They can change during the year, for example "
               f"through supplementary estimates. Spending in {ACCOUNTS_YEAR} is the audited outturn from the "
               "Appropriation Accounts.",
               "Some departments changed between the two years, as functions moved from one to another, so the two "
               "figures for a department are not always like for like. The data file lists every department and office.",
               "Databank figures are published under the Creative Commons Attribution 4.0 licence."],
        key_fact=f"Government departments were allocated €{total / 1e6:.0f} billion for {year}. The largest budget is "
                 f"{top.department}'s, at €{top.value / 1e6:.1f} billion.",
        data=out, figure=fig,
    ).write()
