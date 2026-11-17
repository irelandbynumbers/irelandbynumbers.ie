"""Gender-based violence charts: sexual violence over a lifetime from the CSO's
Sexual Violence Survey 2022, recorded victims of sexual offences by sex, and the
relationship between victims and suspected offenders. Figures only."""
import plotly.graph_objects as go

from ibn import cso, figures, style
from ibn.chart import Chart, Source

TOPIC = "gender"
RESERVATION = ("The CSO publishes recorded crime figures as Statistics under Reservation, because of concerns about the "
               "quality of the underlying Garda records. Recorded crime counts only offences reported to An Garda Síochána, "
               "and many sexual offences are never reported.")


def build():
    lifetime()
    recorded_victims()
    partner()


def _grouped(w, label_col, cols, names, colours, xmax=None):
    fig = go.Figure()
    for col, name, colour in zip(cols, names, colours):
        fig.add_bar(y=w[label_col], x=w[col], name=name, orientation="h", marker=dict(color=colour, cornerradius=3),
                    text=[f"{v:.0f}%" for v in w[col]], textposition="outside", cliponaxis=False,
                    textfont=dict(color=style.INK, size=12),
                    hovertemplate=f"<b>%{{y}}</b><br>{name}: %{{x:.0f}}%<extra></extra>")
    fig.update_layout(style.base_layout(margin=dict(l=8, r=40, t=40, b=32), bargap=0.3, bargroupgap=0.08,
                                        barmode="group", showlegend=True,
                                        legend=dict(style.legend_top(), traceorder="normal"),
                                        xaxis=style.value_axis(ticksuffix="%", range=[0, xmax] if xmax else None),
                                        yaxis=style.axis(automargin=True, autorange="reversed",
                                                         tickfont=dict(color=style.INK_2, size=12))))
    return fig


def lifetime():
    df = cso.fetch("SVS01")
    df = df[df["Statistic Label"] == "Experience of sexual violence at least once in their lifetime - Yes"]
    w = df.pivot_table(index="Age Group", columns="Sex", values="VALUE")
    order = ["All ages", "18 - 24 years", "25 -34 years", "35 - 44 years", "45 - 54 years", "55 - 64 years",
             "65 years and over"]
    w = w.reindex(order).rename_axis("age").reset_index()
    w["age"] = w.age.str.replace("25 -34", "25 - 34").str.replace(" - ", " to ").replace({"All ages": "All adults"})
    w = w.rename(columns={"Female": "women", "Male": "men", "Both sexes": "all"})
    a = w.iloc[0]
    young = w.set_index("age").loc["18 to 24 years"]
    Chart(
        id="gender-sexual-violence-lifetime", topic=TOPIC, height=460,
        title="Experience of sexual violence",
        subtitle="Share of adults who have experienced sexual violence at least once in their lifetime, as a child or an "
                 "adult, by age and sex, 2022.",
        sources=[Source.cso("SVS01", "Sexual Violence Survey 2022, experience of sexual violence")],
        notes=["From the CSO's Sexual Violence Survey, which interviewed adults aged 18 and over in 2022. Sexual violence "
               "covers unwanted sexual contact, including sexual touching and attempted or completed sexual intercourse.",
               "Ages are ages at the time of the survey, not when the violence happened."],
        key_fact=f"In 2022, {a.women:.0f}% of women and {a.men:.0f}% of men in Ireland said they had experienced sexual "
                 f"violence at some point in their lives. Among women aged 18 to 24 the share was {young.women:.0f}%.",
        data=w[["age", "women", "men", "all"]],
        figure=_grouped(w, "age", ["women", "men"], ["Women", "Men"], [style.ORANGE, style.BLUE]),
    ).write()


def recorded_victims():
    df = cso.fetch("CVA06")
    df = df[(df["Age of Victim when Incident Occurred"] == "All ages") &
            (df["Time between Date Occurred and Date Reported"] == "All time periods")]
    w = df.pivot_table(index="Year Reported", columns="Sex of Victim", values="VALUE").reset_index()
    w = w.rename(columns={"Year Reported": "year", "Female": "women", "Male": "men", "Both sexes": "all"})
    late = cso.fetch("CVA06")
    late = late[(late["Age of Victim when Incident Occurred"] == "All ages") & (late["Sex of Victim"] == "Female") &
                (late["Time between Date Occurred and Date Reported"] == "1 year or more")]
    late = late.set_index("Year Reported").VALUE
    w["women_reported_a_year_or_more_later"] = w.year.map(late)
    a, b = w.iloc[0], w.iloc[-1]
    share_f = b.women / b["all"] * 100
    share_late = b.women_reported_a_year_or_more_later / b.women * 100
    fig = figures.lines(w, "year", {"women": "Women and girls", "men": "Men and boys"},
                        colours=[style.ORANGE, style.BLUE], value_format=",.0f", y_range=[0, None])
    Chart(
        id="gender-sexual-offence-victims", topic=TOPIC,
        title="Victims of recorded sexual offences",
        subtitle=f"Victims of sexual offences recorded by An Garda Síochána, by sex and year reported, "
                 f"{a.year:.0f} to {b.year:.0f}.",
        sources=[Source.cso("CVA06", "Victims of recorded crime, sexual offences, by sex and age")],
        notes=[RESERVATION,
               "Victims are counted in the year the offence was reported, which can be many years after it happened. "
               "Changes over time can reflect changes in reporting as well as in offending.",
               "The CSO does not publish these figures by county or Garda division, so they cannot be mapped."],
        key_fact=f"In {b.year:.0f}, {b.women:,.0f} women and girls were recorded as victims of sexual offences, "
                 f"{share_f:.0f}% of all victims, compared with {a.women:,.0f} in {a.year:.0f}. "
                 f"{share_late:.0f}% of them reported the offence a year or more after it happened.",
        data=w, figure=fig,
    ).write()


REL = {"Current intimate partner/spouse": "Current partner or spouse",
       "Former intimate partner/spouse": "Former partner or spouse",
       "Blood relative": "Blood relative", "Other household member": "Other household member",
       "Friend/aquaintance": "Friend or acquaintance", "Colleague or work relationship": "Colleague",
       "Authority or care relationship": "Authority or care relationship",
       "Other suspected offender known to victim": "Someone else known to the victim",
       "Suspected offender not known to victim": "A stranger"}


def partner():
    df = cso.fetch("CVA12")
    year = int(df["Year Reported"].max())
    df = df[(df["Year Reported"] == year) &
            (df["ICCS Offence Group"] == "Attempts/threats to murder, assaults, harassments and related offences (03)")]
    w = df.pivot_table(index="Nature of relationship with suspected offender", columns="Sex of Victim", values="VALUE")
    w = w.reindex(list(REL)).rename(index=REL).rename_axis("relationship").reset_index()
    w = w.rename(columns={"Female": "women", "Male": "men", "Both sexes": "all"})
    r = w.set_index("relationship")
    pf = r.loc["Current partner or spouse", "women"] + r.loc["Former partner or spouse", "women"]
    pm = r.loc["Current partner or spouse", "men"] + r.loc["Former partner or spouse", "men"]
    Chart(
        id="gender-assault-relationship", topic=TOPIC, height=520,
        title="Who the suspected offender was",
        subtitle=f"Victims of recorded assaults, threats and harassment, by their relationship with the suspected "
                 f"offender and by sex, {year}.",
        sources=[Source.cso("CVA12", "Victims of recorded crime by relationship with suspected offender")],
        notes=[RESERVATION,
               "Covers attempts or threats to murder, assaults, harassment and related offences. Shares are of victims "
               "of each sex and may not add to 100% because of rounding."],
        key_fact=f"In {year}, a current or former partner was the suspected offender for {pf:.0f}% of women and girls "
                 f"who were victims of recorded assaults, threats or harassment, compared with {pm:.0f}% of men and boys.",
        data=w[["relationship", "women", "men", "all"]],
        figure=_grouped(w, "relationship", ["women", "men"], ["Women and girls", "Men and boys"],
                        [style.ORANGE, style.BLUE]),
    ).write()
