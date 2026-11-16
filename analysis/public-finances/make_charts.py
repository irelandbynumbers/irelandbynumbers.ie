"""Public finances: where the State's money comes from, what it is spent on,
the surplus or deficit, and government debt. From the CSO's government
finance statistics, which follow the EU's ESA 2010 rules."""
import pandas as pd
import plotly.graph_objects as go

from ibn import cso, figures, style
from ibn.chart import Chart, Source

TOPIC = "public-finances"
GG_NOTE = ("Figures are for general government, which covers central government, local authorities and other public "
           "bodies, measured under the EU's ESA 2010 rules. They differ from the Exchequer figures the Department of "
           "Finance publishes each month, which cover central government only.")
NOMINAL = "Figures are in current prices, not adjusted for inflation."


def build():
    revenue()
    tax_trends()
    spending()
    balance()
    debt()


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
        subtitle=f"General government surplus (above zero) or deficit (below zero), € billion, {d.Year.min()} to {b.Year}.",
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
        subtitle=f"Gross general government debt at the end of each year, € billion, {d.Year.min()} to {b.Year}.",
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
