"""Education charts: pupils in primary and secondary schools, primary class
sizes, the Leaving Certificate and third-level education."""
import plotly.graph_objects as go

from ibn import cso, eu, eurostat, figures, ni, style
from ibn.chart import Chart, Source

TOPIC = "education"
PRIMARY = "All first level education institutions aided by the Department of Education and Skills"
SECONDARY = "Second level education institutions aided by the Department of Education "
EU = "EU27 countries (from 2020)"


def _years(fig, d):
    """Academic years read as categories, with every few labelled."""
    fig.update_xaxes(type="category", nticks=8, tickangle=0)
    return fig

EU_GEO = eurostat.EU27 + [eurostat.EU]


def build():
    pupils()
    class_size()
    leaving_cert_candidates()
    leaving_cert_levels()
    third_level_students()
    third_level_attainment()
    eu_comparisons()
    ni_comparisons()


def pupils():
    p = cso.fetch("EDA42", where={"Age": ["All ages"], "School Programme": [PRIMARY]})
    s = cso.fetch("EDA70", where={"Sex": ["Both sexes"], "School Programme": ["All second level school programmes"],
                                  "Type of School": [SECONDARY]})
    p = p[(p.Age == "All ages") & (p["School Programme"] == PRIMARY)][["Academic Year", "VALUE"]]
    s = s[(s.Sex == "Both sexes") & (s["School Programme"] == "All second level school programmes")
          & (s["Type of School"] == SECONDARY)][["Academic Year", "VALUE"]]
    d = p.rename(columns={"VALUE": "primary"}).merge(s.rename(columns={"VALUE": "secondary"}), on="Academic Year")
    d = d.rename(columns={"Academic Year": "school_year"}).sort_values("school_year").reset_index(drop=True)
    for c in ["primary", "secondary"]:
        d[c] = d[c].astype(int)
    fig = figures.lines(d, "school_year", {"primary": "Primary schools", "secondary": "Secondary schools"},
                        label_last=False, y_range=[0, d[["primary", "secondary"]].max().max() * 1.1])
    fig.update_layout(showlegend=True, legend=style.legend_top(), margin=dict(t=40))
    _years(fig, d)
    peak = d.loc[d.primary.idxmax()]
    y = d.iloc[-1]
    Chart(
        id="education-pupils", topic=TOPIC,
        title="Pupils in primary and secondary schools",
        subtitle=f"Number of pupils in primary schools and in secondary (second-level) schools aided by the Department of "
                 f"Education, school years {d.school_year.iloc[0]} to {y.school_year}.",
        sources=[Source.cso("EDA42", "Primary Pupils"), Source.cso("EDA70", "Pupils Enrolled in Second Level Schools")],
        notes=["Primary schools here include mainstream national schools and special schools aided by the Department of "
               "Education. Secondary schools include secondary, vocational, community and comprehensive schools. "
               "Private primary schools are not included.",
               "Each school year runs from September to June."],
        key_fact=f"In the {y.school_year} school year there were {y.primary:,} pupils in primary schools and {y.secondary:,} "
                 f"in secondary schools. Primary numbers peaked in {peak.school_year}, at {peak.primary:,}.",
        data=d, figure=fig,
    ).write()


def class_size():
    df = cso.fetch("EDA21")
    d = df[["Year", "VALUE"]].rename(columns={"Year": "school_year", "VALUE": "average_class_size"})
    d = d.sort_values("school_year").reset_index(drop=True)
    fig = figures.lines(d, "school_year", {"average_class_size": "Average class size"}, value_format=".1f",
                        label_last=False, y_range=[0, 30])
    _years(fig, d)
    last = d.iloc[-1]
    fig.add_annotation(x=last.school_year, y=last.average_class_size, yshift=14, showarrow=False,
                       text=f"<b>{last.average_class_size:.1f}</b>", font=dict(color=style.INK, size=13))
    peak = d.loc[d.average_class_size.idxmax()]
    Chart(
        id="education-primary-class-size", topic=TOPIC,
        title="Average class size in primary schools",
        subtitle=f"Average number of pupils in a mainstream class in primary schools, school years "
                 f"{d.school_year.iloc[0]} to {last.school_year}.",
        sources=[Source.cso("EDA21", "Average Class Size in Mainstream National Schools")],
        notes=["Mainstream classes in primary (national) schools aided by the Department of Education. Special classes "
               "and special schools, which are much smaller, are not included.",
               "Average class size is not the same as the pupil-teacher ratio, which also counts teachers who do not have a class of their own."],
        key_fact=f"The average primary school class had {last.average_class_size:.1f} pupils in {last.school_year}, "
                 f"down from {peak.average_class_size:.1f} in {peak.school_year}.",
        data=d, figure=fig,
    ).write()


def leaving_cert_candidates():
    df = cso.fetch("EDA93", where={"Sex": ["Both sexes"]})
    d = df[(df.Sex == "Both sexes") & (df["Type of Candidate"] == "All leaving certificate")]
    d = d[["Academic Year", "VALUE"]].rename(columns={"Academic Year": "school_year", "VALUE": "candidates"})
    d["candidates"] = d.candidates.astype(int)
    d = d.sort_values("school_year").reset_index(drop=True)
    fig = figures.lines(d, "school_year", {"candidates": "Leaving Cert candidates"}, label_last=False,
                        y_range=[0, d.candidates.max() * 1.15])
    _years(fig, d)
    y = d.iloc[-1]
    Chart(
        id="education-leaving-cert-candidates", topic=TOPIC,
        title="Leaving Certificate candidates",
        subtitle=f"Number of people who sat the Leaving Certificate (secondary school), school years "
                 f"{d.school_year.iloc[0]} to {y.school_year}.",
        sources=[Source.cso("EDA93", "Junior and Leaving Certificate Examination Candidates (Number)")],
        notes=["Includes everyone who sat the Leaving Certificate in the year, including the Leaving Certificate Applied, "
               "repeat students and external candidates, as published by the CSO from State Examinations Commission records."],
        key_fact=f"{y.candidates:,} people sat the Leaving Certificate in the {y.school_year} school year.",
        data=d, figure=fig,
    ).write()


def leaving_cert_levels():
    df = cso.fetch("WMI09", where={"Sex": ["Both sexes"]})
    year = int(df.Year.max())
    d = df[(df.Sex == "Both sexes") & (df.Year == year)].pivot_table(index="Subject", columns="Statistic Label",
                                                                     values="VALUE").reset_index()
    d = d.rename(columns={"Subject": "subject", "Higher Level": "higher", "Ordinary Level": "ordinary"}).fillna(0)
    d["candidates"] = (d.higher + d.ordinary).astype(int)
    d = d.sort_values("candidates", ascending=False).head(10)
    d["percent_higher"] = (d.higher / d.candidates * 100).round(1)
    d[["higher", "ordinary"]] = d[["higher", "ordinary"]].astype(int)
    d = d.sort_values("percent_higher").reset_index(drop=True)
    fig = go.Figure(go.Bar(y=d.subject, x=d.percent_higher, orientation="h", marker=dict(color=style.BLUE, cornerradius=4),
                           text=[f"{v:.0f}%" for v in d.percent_higher], textposition="outside", cliponaxis=False,
                           textfont=dict(color=style.INK, size=12),
                           hovertemplate="<b>%{y}</b>: %{x:.1f}% at higher level<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=48, t=8, b=32), bargap=0.3,
                                        xaxis=style.value_axis(ticksuffix="%", range=[0, 100]),
                                        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=12))))
    maths = d[d.subject == "Mathematics"]
    fact = (f"In {year}, {maths.percent_higher.iloc[0]:.0f}% of Leaving Cert Mathematics candidates took the higher-level "
            "paper, the lowest share of the ten largest subjects." if len(maths) and maths.index[0] == 0 else
            f"In {year}, {d.subject.iloc[-1]} had the highest share of Leaving Cert candidates taking the higher-level paper, "
            f"at {d.percent_higher.iloc[-1]:.0f}%.")
    Chart(
        id="education-leaving-cert-levels", topic=TOPIC, height=480,
        title="Leaving Certificate subjects taken at higher level",
        subtitle=f"Percentage of Leaving Certificate (secondary school) candidates in the ten largest subjects who took the "
                 f"higher-level paper rather than the ordinary-level paper, {year}.",
        sources=[Source.cso("WMI09", "Level of Leaving Certificate Subjects")],
        notes=["Counts candidates sitting each subject at higher or ordinary level. Irish and Mathematics also have a "
               "foundation level, which is not included here.",
               "The ten largest subjects are those with the most candidates at higher and ordinary level combined."],
        key_fact=fact,
        data=d[["subject", "higher", "ordinary", "candidates", "percent_higher"]], figure=fig,
    ).write()


def third_level_students():
    df = cso.fetch("MIP41")
    d = df[["Academic Year", "VALUE"]].rename(columns={"Academic Year": "academic_year", "VALUE": "students"})
    d["students"] = d.students.astype(int)
    d = d.sort_values("academic_year").reset_index(drop=True)
    fig = figures.lines(d, "academic_year", {"students": "Students"}, label_last=False, y_range=[0, d.students.max() * 1.15])
    _years(fig, d)
    a, b = d.iloc[0], d.iloc[-1]
    Chart(
        id="education-third-level-students", topic=TOPIC,
        title="Students in third-level education",
        subtitle=f"Number of students enrolled in third-level education (universities, technological universities and "
                 f"colleges), academic years {a.academic_year} to {b.academic_year}.",
        sources=[Source.cso("MIP41", "Students enrolled in third level education")],
        notes=["Published by the CSO in its Measuring Ireland's Progress series, from Higher Education Authority figures. "
               "Includes full-time and part-time students."],
        key_fact=f"{b.students:,} students were enrolled in third-level education in {b.academic_year}, up from "
                 f"{a.students:,} in {a.academic_year}.",
        data=d, figure=fig,
    ).write()


def third_level_attainment():
    df = cso.fetch("EATR04", where={"Sex": ["Both sexes"]})
    d = df[(df.Sex == "Both sexes") & df["EU Member State"].isin(["Ireland", EU])]
    d = d.pivot_table(index="Year", columns="EU Member State", values="VALUE").reset_index()
    d = d.rename(columns={"Ireland": "ireland", EU: "eu_27"})[["Year", "ireland", "eu_27"]]
    d["Year"] = d.Year.astype(int)
    fig = figures.lines(d, "Year", {"ireland": "Ireland", "eu_27": "EU average"}, value_format=".0f", suffix="%",
                        colours=[style.BLUE, style.INK_3], y_range=[0, 100])
    fig.update_xaxes(dtick=1)
    y = d.iloc[-1]
    Chart(
        id="education-third-level-attainment", topic=TOPIC,
        title="Young adults with a third-level qualification",
        subtitle=f"Percentage of people aged 30 to 34 with a third-level qualification, Ireland and the 27 EU countries, "
                 f"{d.Year.min()} to {d.Year.max()}.",
        sources=[Source.cso("EATR04", "Persons aged 30-34 years with a Third Level Education in EU Member States")],
        notes=["From the Labour Force Survey in each country, as published by Eurostat and the CSO. Third-level covers "
               "qualifications from higher certificates and ordinary degrees up to doctorates.",
               "Figures are published rounded to the nearest whole percentage."],
        key_fact=f"In {y.Year:.0f}, {y.ireland:.0f}% of people aged 30 to 34 in Ireland had a third-level qualification, "
                 f"compared with an EU average of {y.eu_27:.0f}%.",
        data=d, figure=fig,
    ).write()


def eu_comparisons():
    df = eurostat.fetch("edat_lfse_14", geo=EU_GEO, sex="T", wstatus="POP", age="Y18-24", unit="PC")
    eu.rank_chart(
        "education-early-leavers-eu", TOPIC, "Early school leavers across the EU",
        "Share of people aged 18 to 24 who left education early, EU countries, {year}.",
        Source.eurostat("edat_lfse_14", "Early leavers from education and training"), df,
        lambda y, ie, ev, place: f"In {y}, {ie:.1f}% of people aged 18 to 24 in Ireland had left education early, "
                                 f"compared with {ev:.1f}% across the EU. Ireland's share was {place}.",
        notes=["Early leavers are people aged 18 to 24 who finished at most lower secondary education, which in Ireland "
               "means the Junior Cycle, and who are not in any education or training.",
               "From the Labour Force Survey in each country. Figures for smaller countries are less precise."],
        suffix="%")


def ni_comparisons():
    df = cso.fetch("CPNI51")
    df = df[df.Sex == "Both sexes"]
    keep = ["Basic qualification", "Intermediate and advanced qualification", "Higher and professional qualification",
            "Other qualification"]
    names = {"Basic qualification": "Basic or none", "Intermediate and advanced qualification": "Intermediate or advanced",
             "Higher and professional qualification": "Higher or professional", "Other qualification": "Other"}
    d = ni.census_shares(df, "Level of Education", keep, names)
    r = d.set_index("category")
    Chart(
        id="education-ni-qualifications", topic=TOPIC, height=360,
        title="Qualifications in Ireland and Northern Ireland",
        subtitle="Share of people aged 16 and over by highest level of qualification, census 2022 in Ireland and 2021 "
                 "in Northern Ireland.",
        sources=[Source.cso("CPNI51", "Level of education, Ireland and Northern Ireland")],
        notes=[ni.CENSUS_NOTE, ni.STATE_NOTE, "The two education systems differ, so the CSO and NISRA grouped "
               "qualifications into broad levels. Higher or professional covers degrees and similar qualifications. "
               "People who did not state a qualification are left out. The figures are not adjusted for differences in the "
               "age of the two populations."],
        key_fact=f"{r.loc['Higher or professional', 'ireland']:.0f}% of people aged 16 and over in Ireland had a higher or "
                 f"professional qualification, compared with {r.loc['Higher or professional', 'northern_ireland']:.0f}% in "
                 f"Northern Ireland.",
        data=d, figure=ni.grouped_bars(d, "category"),
    ).write()
