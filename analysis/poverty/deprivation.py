"""Area deprivation charts from the Pobal HP Deprivation Index 2022, which
scores every electoral division on census measures such as education,
unemployment, lone parenthood and housing. Figures only."""
import os

import pandas as pd

from ibn import figures, style
from ibn.chart import Chart, Source
from ibn.charts import hbars

TOPIC = "poverty"
DATA = os.path.join(os.path.dirname(__file__), "..", "data", "pobal")
HP = Source("Pobal", "Pobal HP Deprivation Index 2022, scores by electoral division (Haase and Pratschke)",
            "https://www.pobal.ie/",
            licence="Quoted with acknowledgement", licence_url="")
ABOUT = ("The Pobal HP Deprivation Index, developed by Trutz Haase and Jonathan Pratschke, scores every electoral "
         "division from census figures on education, social class, unemployment, lone parenthood, age dependency, "
         "housing tenure and overcrowding. These are relative scores, set so that the national average is about 0. "
         "Scores above 10 are labelled affluent and scores below -10 disadvantaged.")
ORDER = ["Affluent", "Marginally Above Average", "Marginally Below Average", "Disadvantaged", "Very Disadvantaged",
         "Extremely Disadvantaged"]
COUNTY = {"Cork City": "Cork", "Cork County": "Cork", "Galway City": "Galway", "Galway County": "Galway",
          "Limerick City": "Limerick", "Limerick County": "Limerick", "Waterford City": "Waterford",
          "Waterford County": "Waterford", "Dublin City": "Dublin", "Dublin (outside Dublin City)": "Dublin"}


def build():
    county_map()
    categories()


def eds():
    d = pd.read_csv(os.path.join(DATA, "hp_index_2022_ed.csv"), dtype={"ed_id": str})
    d["county"] = d.area.replace(COUNTY)
    return d


def county_map():
    d = eds()
    d["weighted"] = d.relative_score * d.population
    d["disadvantaged_pop"] = d.population.where(d.relative_score < -10, 0)
    c = d.groupby("county")[["weighted", "population", "disadvantaged_pop"]].sum()
    c["score"] = (c.weighted / c.population).round(1)
    c["percent_disadvantaged"] = (c.disadvantaged_pop / c.population * 100).round(1)
    c = c.reset_index().sort_values("score", ascending=False)
    hi, lo = c.iloc[0], c.iloc[-1]
    m = max(abs(c.score.min()), abs(c.score.max()))
    fig = figures.county_map(c[["county", "score", "percent_disadvantaged"]], "county", "score",
                             colorscale=style.DIVERGING, value_format="+.1f", legend_title="Average score",
                             zmin=-m, zmax=m, hover_extra="%{customdata[2]:.0f}% live in disadvantaged areas")
    Chart(
        id="poverty-deprivation-map", topic=TOPIC, kind="map",
        title="Affluence and deprivation by county",
        subtitle="Average Pobal HP Deprivation Index score by county, weighted by population, 2022. Blue is more "
                 "affluent than average and orange more deprived.",
        sources=[HP],
        notes=[ABOUT,
               "County scores are the population-weighted average of the scores of the electoral divisions in each "
               "county. A county average can hide large differences between neighbouring areas, which the index is "
               "designed to show.",
               "The data file also gives the share of each county's population living in electoral divisions scored "
               "as disadvantaged, very disadvantaged or extremely disadvantaged."],
        key_fact=f"In 2022, {hi.county} had the highest average score on the Pobal HP Deprivation Index, at "
                 f"{hi.score:+.1f}, and {lo.county} the lowest, at {lo.score:+.1f}.",
        data=c[["county", "score", "percent_disadvantaged", "population"]], figure=fig,
    ).write()


def categories():
    d = eds()
    c = d.groupby("category").population.sum().reindex(ORDER)
    w = (c / c.sum() * 100).round(1).rename("percent").rename_axis("category").reset_index()
    w["people"] = c.values
    w["label"] = w.category.str.capitalize()
    disadv = w[w.category.str.contains("Disadvantaged")]
    colours = [style.BLUE, style.CONTEXT, style.CONTEXT, style.ORANGE, style.ORANGE, style.ORANGE]
    fig = hbars(w, "label", "percent", ".0f", "%", colour=colours)
    Chart(
        id="poverty-deprivation-categories", topic=TOPIC, height=340,
        title="People living in affluent and deprived areas",
        subtitle="Share of the population by the Pobal HP Deprivation Index category of the electoral division they "
                 "live in, 2022.",
        sources=[HP],
        notes=[ABOUT,
               "Categories are bands of 10 points on the relative score. Not everyone living in a disadvantaged area "
               "is disadvantaged, and not everyone in an affluent area is affluent."],
        key_fact=f"In 2022, {disadv.percent.sum():.0f}% of people, about {disadv.people.sum() / 1000:,.0f},000, lived "
                 f"in electoral divisions the Pobal HP Deprivation Index scores as disadvantaged or worse.",
        data=w[["category", "percent", "people"]], figure=fig,
    ).write()
