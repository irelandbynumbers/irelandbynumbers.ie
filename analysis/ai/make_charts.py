"""Artificial intelligence charts: electricity used by data centres, and how
businesses and people use AI, with EU comparisons."""
import pandas as pd
import plotly.graph_objects as go

from ibn import cso, eu, eurostat, figures, style
from ibn.chart import Chart, Source

TOPIC = "ai"
EU_GEO = eurostat.EU27 + [eurostat.EU]
METER_NOTE = "Covers electricity measured by meters on the electricity network."


def build():
    data_centre_electricity()
    business_use()
    business_use_eu()
    generative_ai_eu()
    generative_ai_by_age()
    familiarity()


def _annual_electricity():
    df = cso.fetch("MEC02")
    df["year"] = df.Quarter.str[:4].astype(int)
    quarters = df.groupby("year").Quarter.nunique()
    full = quarters[quarters == 4].index
    d = df[df.year.isin(full)].pivot_table(index="year", columns="Electricity Consumption", values="VALUE", aggfunc="sum")
    d = d.rename(columns={"All metered electricity consumption": "all_gwh", "Data centres": "data_centres_gwh",
                          "Customers other than data centres": "other_gwh"}).reset_index()
    d["data_centre_percent"] = (d.data_centres_gwh / d.all_gwh * 100).round(1)
    return d.astype({"all_gwh": int, "data_centres_gwh": int, "other_gwh": int})


def data_centre_electricity():
    d = _annual_electricity()
    a, b = d.iloc[0], d.iloc[-1]
    fig = figures.lines(d, "year", {"data_centre_percent": "Data centres"}, value_format=".0f", suffix="%",
                        y_range=[0, max(30, d.data_centre_percent.max() * 1.15)])
    Chart(
        id="ai-data-centre-electricity", topic=TOPIC,
        title="Electricity used by data centres",
        subtitle=f"Data centres' share of all metered electricity used in Ireland, {a.year:.0f} to {b.year:.0f}.",
        sources=[Source.cso("MEC02", "Data Centres Metered Electricity Consumption")],
        notes=[METER_NOTE,
               "Data centres store and process data for online services, including cloud computing and AI. Not all of "
               "their electricity use is for AI. The data file has the amounts in gigawatt hours (GWh)."],
        key_fact=f"Data centres used {b.data_centre_percent:.0f}% of all metered electricity in Ireland in {b.year:.0f}, up "
                 f"from {a.data_centre_percent:.0f}% in {a.year:.0f}.",
        data=d, figure=fig,
    ).write()

    g = d.assign(data_centres_twh=(d.data_centres_gwh / 1000).round(2), other_twh=(d.other_gwh / 1000).round(2))
    fig = figures.lines(g, "year", {"other_twh": "Other customers", "data_centres_twh": "Data centres"},
                        colours=[style.CONTEXT, style.BLUE], value_format=".1f", suffix=" TWh",
                        y_range=[0, g.other_twh.max() * 1.1])
    growth = b.data_centres_gwh / a.data_centres_gwh
    other_change = (b.other_gwh / a.other_gwh - 1) * 100
    Chart(
        id="ai-data-centre-electricity-amount", topic=TOPIC,
        title="Electricity used by data centres and other customers",
        subtitle=f"Metered electricity consumption, terawatt hours (TWh), {a.year:.0f} to {b.year:.0f}.",
        sources=[Source.cso("MEC02", "Data Centres Metered Electricity Consumption")],
        notes=[METER_NOTE, "One terawatt hour is 1,000 gigawatt hours, or a billion kilowatt hours."],
        key_fact=f"Data centres used {b.data_centres_gwh / 1000:.1f} TWh of electricity in {b.year:.0f}, {growth:.1f} times "
                 f"as much as in {a.year:.0f}. Use by all other customers {'rose' if other_change >= 0 else 'fell'} by "
                 f"{abs(other_change):.0f}% over the same period.",
        data=g[["year", "data_centres_gwh", "other_gwh", "all_gwh", "data_centres_twh", "other_twh"]], figure=fig,
    ).write()


def business_use():
    df = cso.fetch("ICA237")
    df = df[df["Statistic Label"] == "Enterprises using Artificial Intelligence"]
    d = df.pivot_table(index="Enterprise Size Class", columns="Year", values="VALUE")
    order = ["Small (10 to 49)", "Medium (50 to 249)", "Large (250 or more)", "All Enterprises"]
    d = d.loc[order].rename(index={"Small (10 to 49)": "Small (10 to 49 staff)", "Medium (50 to 249)": "Medium (50 to 249 staff)",
                                   "Large (250 or more)": "Large (250 or more staff)", "All Enterprises": "All businesses"})
    years = list(d.columns)
    fig = go.Figure()
    for y, colour in zip(years, ["#b7d3f4", "#6fa6e6", style.BLUE]):
        fig.add_trace(go.Bar(y=d.index, x=d[y], name=str(y), orientation="h", marker=dict(color=colour, cornerradius=3),
                             text=[f"{v:.0f}%" for v in d[y]], textposition="outside", cliponaxis=False,
                             textfont=dict(color=style.INK_2, size=11),
                             hovertemplate=f"<b>%{{y}}</b>, {y}: %{{x:.1f}}%<extra></extra>"))
    fig.update_layout(style.base_layout(
        barmode="group", bargap=0.25, showlegend=True, legend=dict(style.legend_top(), traceorder="normal"),
        margin=dict(l=8, r=48, t=40, b=32), xaxis=style.value_axis(ticksuffix="%"),
        yaxis=style.axis(automargin=True, autorange="reversed", tickfont=dict(color=style.INK_2, size=12))))
    first, last = years[0], years[-1]
    r = d.loc["All businesses"]
    Chart(
        id="ai-business-use", topic=TOPIC, height=420,
        title="Businesses using AI",
        subtitle=f"Share of businesses with 10 or more staff that use at least one AI technology, by size, {first} to {last}.",
        sources=[Source.cso("ICA237", "Enterprise use of Artificial Intelligence")],
        notes=["From the CSO's survey of information and communication technology in enterprises. AI technologies "
               "include text mining, speech recognition, generating written or spoken language, image recognition, "
               "machine learning, and software that automates workflows or helps make decisions. Financial businesses "
               "and businesses with fewer than 10 staff are not covered."],
        key_fact=f"{r[last]:.0f}% of businesses with 10 or more staff used AI in {last}, up from {r[first]:.0f}% in {first}. "
                 f"Large businesses were the most likely to use it, at {d.loc['Large (250 or more staff)', last]:.0f}%.",
        data=d.reset_index().rename(columns={"Enterprise Size Class": "business_size"}), figure=fig,
    ).write()


def business_use_eu():
    df = cso.fetch("BIIESA20")
    df = df[df["Statistic Label"] == "Enterprises using Artificial Intelligence"]
    d = _as_eu(pd.DataFrame({"geo_label": df.Country, "time": df.Year, "value": df.VALUE}))
    eu.rank_chart(
        "ai-business-use-eu", TOPIC, "Businesses using AI across the EU",
        "Share of businesses with 10 or more staff that use at least one AI technology, EU countries, {year}.",
        Source.cso("BIIESA20", "Enterprise use of Artificial Intelligence and Cloud Computing"), d,
        lambda y, ie, ev, place: f"In {y}, {ie:.1f}% of businesses in Ireland with 10 or more staff used AI, compared "
                                 f"with {ev:.1f}% across the EU.",
        notes=["From the survey of ICT use in enterprises, which every EU country carries out in the same way. Financial "
               "businesses and businesses with fewer than 10 staff are not covered."],
        suffix="%")


def _as_eu(d):
    """Give countries matched by name the geo codes the EU helpers expect."""
    codes = {"Austria": "AT", "Belgium": "BE", "Bulgaria": "BG", "Croatia": "HR", "Cyprus": "CY", "Czechia": "CZ",
             "Denmark": "DK", "Estonia": "EE", "Finland": "FI", "France": "FR", "Germany": "DE", "Greece": "EL",
             "Hungary": "HU", "Ireland": "IE", "Italy": "IT", "Latvia": "LV", "Lithuania": "LT", "Luxembourg": "LU",
             "Malta": "MT", "Netherlands (the)": "NL", "Poland": "PL", "Portugal": "PT", "Romania": "RO",
             "Slovakia": "SK", "Slovenia": "SI", "Spain": "ES", "Sweden": "SE", "EU27 countries (from 2020)": eurostat.EU}
    d = d.copy()
    d["geo"] = d.geo_label.map(codes)
    d["geo_label"] = d.geo_label.replace({"Netherlands (the)": "Netherlands"})
    return d


def generative_ai_eu():
    df = eurostat.fetch("isoc_ai_iaiu", geo=EU_GEO, ind_type="IND_TOTAL", indic_is="I_IUAI", unit="PC_IND")
    eu.rank_chart(
        "ai-generative-ai-eu", TOPIC, "Use of generative AI across the EU",
        "Share of people aged 16 to 74 who used generative AI tools in the previous three months, EU countries, {year}.",
        Source.eurostat("isoc_ai_iaiu", "Individuals - use of generative AI tools"), df,
        lambda y, ie, ev, place: f"In {y}, {ie:.0f}% of people aged 16 to 74 in Ireland had used generative AI tools in "
                                 f"the previous three months, compared with {ev:.0f}% across the EU. Ireland's share was {place}.",
        notes=["Generative AI tools create text, images, computer code or other content from a prompt. Examples include "
               "chatbots such as ChatGPT. From the survey of ICT use in households, carried out in the same way in every "
               "EU country."],
        suffix="%")


AGES = {"Y16_24": "16 to 24", "Y25_34": "25 to 34", "Y35_44": "35 to 44", "Y45_54": "45 to 54", "Y55_64": "55 to 64",
        "Y65_74": "65 to 74"}


def generative_ai_by_age():
    df = eurostat.fetch("isoc_ai_iaiu", name="isoc_ai_iaiu_ie_age", geo=["IE", eurostat.EU], ind_type=list(AGES),
                        indic_is="I_IUAI", unit="PC_IND")
    year = int(df.time.max())
    d = df[df.time == year].pivot_table(index="ind_type", columns="geo", values="value").loc[list(AGES)]
    d.index = [AGES[i] for i in d.index]
    d = d.rename(columns={"IE": "ireland", eurostat.EU: "eu_average"}).reset_index().rename(columns={"index": "age_group"})
    fig = go.Figure()
    for col, name, colour in [("ireland", "Ireland", style.ORANGE), ("eu_average", "EU average", style.INK_3)]:
        fig.add_trace(go.Bar(x=d.age_group, y=d[col], name=name, marker=dict(color=colour, cornerradius=3),
                             text=[f"{v:.0f}%" for v in d[col]], textposition="outside", cliponaxis=False,
                             textfont=dict(color=style.INK_2, size=11),
                             hovertemplate=f"<b>%{{x}}</b>, {name}: %{{y:.1f}}%<extra></extra>"))
    fig.update_layout(style.base_layout(
        barmode="group", bargap=0.25, showlegend=True, legend=style.legend_top(), margin=dict(l=48, r=16, t=40, b=48),
        xaxis=style.axis(showline=True, title=dict(text="Age")), yaxis=style.value_axis(ticksuffix="%", range=[0, 100])))
    young, old = d.iloc[0], d.iloc[-1]
    Chart(
        id="ai-generative-ai-by-age", topic=TOPIC,
        title="Use of generative AI by age",
        subtitle=f"Share of people who used generative AI tools in the previous three months, by age, Ireland and the "
                 f"EU, {year}.",
        sources=[Source.eurostat("isoc_ai_iaiu", "Individuals - use of generative AI tools", "isoc_ai_iaiu_ie_age")],
        notes=["Generative AI tools create text, images, computer code or other content from a prompt. From the survey "
               "of ICT use in households.", eu.NOTE],
        key_fact=f"In {year}, {young.ireland:.0f}% of people aged 16 to 24 in Ireland had used generative AI tools in the "
                 f"previous three months, compared with {old.ireland:.0f}% of those aged 65 to 74.",
        data=d, figure=fig,
    ).write()


def familiarity():
    df = cso.fetch("TRA226")
    df = df[df.Gender == "Both male and female"]
    order = ["Understand it well and could explain it to others", "General idea of what it means, but struggle to explain it",
             "Not familiar with the term", "Prefer not to answer"]
    labels = {order[0]: "Understand it well and could explain it", order[1]: "Have a general idea, but would struggle to explain it",
              order[2]: "Not familiar with the term", order[3]: "Prefer not to answer"}
    d = df.set_index("Familiarity with AI").VALUE.loc[order].rename(index=labels).rename("percent").reset_index()
    d = d.rename(columns={"Familiarity with AI": "answer"})
    year = int(df.Year.max())
    fig = go.Figure(go.Bar(y=d.answer, x=d.percent, orientation="h", marker=dict(color=style.BLUE, cornerradius=3),
                           text=[f"{v:.0f}%" for v in d.percent], textposition="outside", cliponaxis=False,
                           textfont=dict(color=style.INK, size=12), hovertemplate="<b>%{y}</b>: %{x:.0f}%<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=48, t=8, b=32), bargap=0.35,
                                        xaxis=style.value_axis(ticksuffix="%"),
                                        yaxis=style.axis(automargin=True, autorange="reversed",
                                                         tickfont=dict(color=style.INK_2, size=12))))
    r = d.set_index("answer").percent
    a = cso.fetch("TRA227")
    age = a[a["Familiarity with AI"] == order[0]].set_index("Age").VALUE
    Chart(
        id="ai-familiarity", topic=TOPIC, height=320,
        title="How familiar people are with the term AI",
        subtitle=f"Share of adults by how well they understand the term artificial intelligence (AI), {year}.",
        sources=[Source.cso("TRA226", "Respondents familiarity with the term artificial intelligence (AI)"),
                 Source.cso("TRA227", "Respondents familiarity with the term artificial intelligence (AI), by age")],
        notes=["From a CSO survey of adults, who were asked how familiar they are with the term artificial intelligence."],
        key_fact=f"In {year}, {r.iloc[0]:.0f}% of adults said they understood the term AI well enough to explain it to "
                 f"others. The share ranged from {age.iloc[0]:.0f}% of people aged 18 to 29 to {age.iloc[-1]:.0f}% of those "
                 f"aged 50 and over.",
        data=d, figure=fig,
    ).write()
