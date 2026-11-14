"""Irish language charts, from Census 2022."""
import plotly.graph_objects as go

from ibn import cso, style
from ibn.chart import Chart, Source

TOPIC = "irish-language"

FREQ = {
    "Speaks Irish daily": "Daily, outside school",
    "Speaks Irish weekly": "Weekly, outside school",
    "Speaks Irish less often": "Less often",
    "Never speaks Irish outside the education system only": "Never outside school",
    "Speaks Irish daily within the education system only": "Only in school",
    "Not stated": "Not stated",
}

CENSUS_NOTE = ("The census asks whether each person aged 3 and over can speak Irish, and if so how often they speak it. "
               "Answers are as given on the census form, so they describe what people report rather than a test of ability.")


def build():
    frequency()
    gaeltacht()


def frequency():
    df = cso.fetch("F8001", where={"Gaeltacht Areas": ["State"], "Sex": ["Both sexes"], "Age Group": ["All ages"],
                                   "Level of Irish Spoken": ["Speaks Irish - Total"]})
    df = df[(df["Gaeltacht Areas"] == "State") & (df.Sex == "Both sexes") & (df["Age Group"] == "All ages") &
            (df["Level of Irish Spoken"] == "Speaks Irish - Total")]
    year = int(df["Census Year"].max())
    total = int(df[df["Frequency of speaking Irish"] == "All Irish speakers"].VALUE.iloc[0])
    d = df[df["Frequency of speaking Irish"].isin(FREQ)][["Frequency of speaking Irish", "VALUE"]]
    d = d.rename(columns={"Frequency of speaking Irish": "cso_frequency", "VALUE": "irish_speakers"})
    d["frequency"] = d.cso_frequency.map(FREQ)
    d["irish_speakers"] = d.irish_speakers.astype(int)
    d["percent_of_irish_speakers"] = (d.irish_speakers / total * 100).round(1)
    d = d.set_index("cso_frequency").loc[list(FREQ)].reset_index()[["frequency", "cso_frequency", "irish_speakers", "percent_of_irish_speakers"]]
    p = d.iloc[::-1]
    fig = go.Figure(go.Bar(y=p.frequency, x=p.irish_speakers, orientation="h",
                           marker=dict(color=[style.BLUE if f.startswith(("Daily", "Weekly")) else style.CONTEXT for f in p.frequency],
                                       cornerradius=4),
                           text=[f"{v:,}" for v in p.irish_speakers], textposition="outside", cliponaxis=False,
                           textfont=dict(color=style.INK, size=12),
                           hovertemplate="<b>%{y}</b>: %{x:,} people<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=72, t=8, b=32), bargap=0.3,
                                        xaxis=style.value_axis(tickformat="~s"),
                                        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=12))))
    daily = d[d.frequency == "Daily, outside school"].iloc[0]
    Chart(
        id="irish-language-frequency", topic=TOPIC, height=420,
        title="How often Irish speakers speak Irish",
        subtitle=f"People aged 3 and over who said they could speak Irish, by how often they speak it, Census {year}.",
        sources=[Source.cso("F8001", "Irish speakers aged 3 years and over")],
        notes=[CENSUS_NOTE,
               "Only in school means people who speak Irish every day in school or college but not outside it. "
               "Daily and weekly outside school include people who also speak it in school. "
               f"In total, {total:,} people said they could speak Irish."],
        key_fact=f"At the {year} census, {total:,} people said they could speak Irish, and {daily.irish_speakers:,} "
                 f"({daily.percent_of_irish_speakers:.0f}% of them) said they spoke it every day outside school.",
        data=d, figure=fig,
    ).write()


def gaeltacht():
    df = cso.fetch("F8033")
    d = df[df["Statistic Label"] == "Percentage of daily Irish speakers aged 3 years and over"]
    d = d.pivot_table(index="Gaeltacht Areas", columns="Census Year", values="VALUE").reset_index()
    years = [c for c in d.columns if c != "Gaeltacht Areas"]
    d.columns = ["area"] + [f"percent_{y}" for y in years]
    d["area"] = d.area.str.replace(" Gaeltacht Areas", "").str.replace("All", "All Gaeltacht areas")
    last = f"percent_{years[-1]}"
    d = d.sort_values(last).reset_index(drop=True)
    fig = go.Figure()
    for y, colour in zip(years, [style.CONTEXT, style.INK_3, style.BLUE]):
        fig.add_trace(go.Bar(y=d.area, x=d[f"percent_{y}"], name=str(y), orientation="h",
                             marker=dict(color=colour, cornerradius=3),
                             hovertemplate=f"<b>%{{y}}</b>, {y}: %{{x:.1f}}%<extra></extra>"))
    fig.update_layout(style.base_layout(barmode="group", bargap=0.25, bargroupgap=0.05, showlegend=True,
                                        legend=dict(style.legend_top(), traceorder="normal"),
                                        margin=dict(l=8, r=24, t=40, b=32),
                                        xaxis=style.value_axis(ticksuffix="%"),
                                        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=12))))
    all_ = d[d.area == "All Gaeltacht areas"].iloc[0]
    Chart(
        id="irish-language-gaeltacht", topic=TOPIC, height=560,
        title="Daily Irish speakers in the Gaeltacht",
        subtitle=f"Percentage of people aged 3 and over in each Gaeltacht area who speak Irish every day outside school, "
                 f"Census {', '.join(str(y) for y in years[:-1])} and {years[-1]}.",
        sources=[Source.cso("F8033", "Daily Irish speakers aged 3 years and over")],
        notes=[CENSUS_NOTE,
               "The Gaeltacht is the set of areas, mostly along the west coast, that the State recognises as Irish-speaking. "
               "Each area here combines the Gaeltacht districts in that county or city."],
        key_fact=f"In {years[-1]}, {all_[last]:.0f}% of people in the Gaeltacht spoke Irish every day outside school, "
                 f"compared with {all_[f'percent_{years[0]}']:.0f}% in {years[0]}.",
        data=d, figure=fig,
    ).write()
