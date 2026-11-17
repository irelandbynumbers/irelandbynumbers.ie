"""Childhood charts: how many children there are, children's health and
children in care, with an EU comparison. Child poverty is in the poverty topic."""
import plotly.graph_objects as go

from ibn import cso, eu, eurostat, figures, style
from ibn.chart import Chart, Source
from ibn.charts import hbars

TOPIC = "childhood"
EU_GEO = eurostat.EU27 + [eurostat.EU]
CHILD_AGES = ["Under 1 year"] + [f"{a} year" if a == 1 else f"{a} years" for a in range(1, 18)]


def build():
    children_population()
    infant_mortality()
    low_birth_weight()
    general_health()
    in_care()




def children_population():
    df = cso.fetch("PEA11")
    df = df[df.Sex == "Both sexes"]
    kids = df[df["Single Year of Age"].isin(CHILD_AGES)].groupby("Year").VALUE.sum()
    total = df[df["Single Year of Age"] == "All ages"].set_index("Year").VALUE
    d = (kids.rename("children").to_frame().join(total.rename("population"))).reset_index().rename(columns={"Year": "year"})
    d["percent_children"] = (d.children / d.population * 100).round(1)
    d = d.astype({"year": int, "children": int, "population": int})
    a, b = d.iloc[0], d.iloc[-1]
    peak = d.loc[d.percent_children.idxmax()]
    fig = figures.lines(d, "year", {"percent_children": "Children under 18"}, value_format=".0f", suffix="%",
                        y_range=[0, d.percent_children.max() * 1.15])
    Chart(
        id="childhood-children-population", topic=TOPIC,
        title="Children as a share of the population",
        subtitle=f"Children aged under 18 as a share of the population, {a.year:.0f} to {b.year:.0f}.",
        sources=[Source.cso("PEA11", "Population estimates from 1926, by single year of age")],
        notes=["Figures for census years before 1996 are from the census. Later years are CSO estimates for April of "
               "each year. The data file has the number of children as well."],
        key_fact=f"There were about {b.children / 1e6:.2f} million children aged under 18 in Ireland in {b.year:.0f}, "
                 f"{b.percent_children:.0f}% of the population. The highest share in these figures was "
                 f"{peak.percent_children:.0f}%, in {peak.year:.0f}.",
        data=d, figure=fig,
    ).write()






def infant_mortality():
    df = eurostat.fetch("demo_minfind", geo=EU_GEO, indic_de="INFMORRT")
    eu.lines_chart(
        "childhood-infant-mortality", TOPIC, "Infant mortality in Ireland and the EU",
        "Deaths of babies under one year old per 1,000 live births, {first} to {last}.",
        Source.eurostat("demo_minfind", "Infant mortality rates"), df,
        lambda w: (lambda a, b: f"In {b.year:.0f}, {b.ireland:.1f} babies in every 1,000 born in Ireland died before their "
                                f"first birthday, down from {a.ireland:.1f} in {a.year:.0f}.")(w.iloc[0], w.iloc[-1]),
        value_format=".1f", y_range=[0, 45])


def low_birth_weight():
    df = cso.fetch("HSPAA35")
    col = "Birthweight (grams)"
    low = df[df[col].str.startswith("L")].groupby("Year").VALUE.sum()
    total = df[df[col] == "All Births"].set_index("Year").VALUE
    d = (low / total * 100).round(1).rename("percent_under_2500g").reset_index().rename(columns={"Year": "year"})
    d["year"] = d.year.astype(int)
    b = d.iloc[-1]
    fig = go.Figure(go.Bar(x=d.year.astype(str), y=d.percent_under_2500g, marker=dict(color=style.BLUE, cornerradius=3),
                           text=[f"{v:.1f}%" for v in d.percent_under_2500g], textposition="outside", cliponaxis=False,
                           textfont=dict(color=style.INK, size=12), hovertemplate="<b>%{x}</b>: %{y:.1f}%<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=8, t=8, b=32), bargap=0.4,
                                        xaxis=style.axis(type="category"), yaxis=style.value_axis(ticksuffix="%")))
    Chart(
        id="childhood-low-birth-weight", topic=TOPIC, height=320,
        title="Babies born with a low birth weight",
        subtitle=f"Share of births weighing under 2,500 grams, selected years {d.year.iloc[0]} to {b.year:.0f}.",
        sources=[Source.cso("HSPAA35", "Prevalence of low birth-weight infants")],
        notes=["A low birth weight is under 2,500 grams (about 5.5 pounds). The CSO publishes 2009 and then each year "
               "from 2019."],
        key_fact=f"In {b.year:.0f}, {b.percent_under_2500g:.1f}% of babies born in Ireland weighed under 2,500 grams.",
        data=d, figure=fig,
    ).write()


def general_health():
    df = cso.fetch("IHSC01")
    df = df[(df.Sex == "Both sexes") & (df["Statistic Label"] == "Percentage of children")
            & (df["Self-perceived general health"] == "Good or Very Good")]
    d = df[["Age", "VALUE"]].rename(columns={"Age": "age", "VALUE": "percent_good_or_very_good"})
    d["age"] = d.age.str.replace(" - ", " to ", regex=False).replace({"3 to 14 years": "All aged 3 to 14"})
    year = int(df.Year.max())
    r = d.set_index("age").percent_good_or_very_good
    Chart(
        id="childhood-general-health", topic=TOPIC, height=300,
        title="Children's general health",
        subtitle=f"Share of children whose health was described as good or very good, by age, {year}.",
        sources=[Source.cso("IHSC01", "Self-perceived general health of children aged 3 to 14 years")],
        notes=["From a CSO survey of households. Health is as described in the survey, not measured by a doctor."],
        key_fact=f"In {year}, the health of {r['All aged 3 to 14']:.0f}% of children aged 3 to 14 was described as good or "
                 f"very good.",
        data=d, figure=hbars(d, "age", "percent_good_or_very_good", ".1f"),
    ).write()


def in_care():
    df = cso.fetch("EAACC12")
    n = df[df["Statistic Label"] == "Children in care in January 2025"].set_index("Placement Type").VALUE
    total = int(n["Total number of children in care placements"])
    labels = {"Foster Care (General)": "Foster care, general", "Foster Care (Relative)": "Foster care with relatives",
              "Residential Care (General)": "Residential care", "Residential Special Care": "Special care",
              "Other Care Placements": "Other placements"}
    d = n.drop("Total number of children in care placements").rename(index=labels).rename("children")
    d = d.rename_axis("placement").reset_index()
    d["percent"] = (d.children / total * 100).round(1)
    foster = d.children.iloc[:2].sum() / total * 100
    Chart(
        id="childhood-in-care", topic=TOPIC, height=300,
        title="Children in care by type of placement",
        subtitle="Number of children in the care of the State, by type of placement, January 2025.",
        sources=[Source.cso("EAACC12", "Placement type of children in care in January 2025")],
        notes=["Children in care are in the care of Tusla, the Child and Family Agency. Special care is a secure "
               "placement ordered by the High Court."],
        key_fact=f"There were {total:,} children in care in January 2025. {foster:.0f}% of them were in foster care, "
                 f"including with relatives.",
        data=d, figure=hbars(d, "placement", "children", ",.0f", ""),
    ).write()
