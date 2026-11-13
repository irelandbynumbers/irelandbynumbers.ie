"""County pages: one page per county, with its population at each census and
the average rent on new tenancies, from the same CSO tables as the Population
and Housing charts.

Writes a small chart pair per county (kept off the All charts list), the page
counties/<county>.qmd, and the list of counties on counties/index.qmd
(counties/_list.md). The pages are generated, so edit this script rather than
the .qmd files.
"""
import os

import plotly.graph_objects as go

from ibn import cso, figures, style
from ibn.chart import ROOT, Chart, Source

TOPIC = "counties"
OUT = os.path.join(ROOT, "counties")


def slug(county):
    return county.lower().replace(" ", "-")


def rank_words(n, top, bottom, total=26):
    """'largest', '5th largest', 'second smallest', 'smallest' for a rank out of `total`."""
    from_bottom = total - n + 1
    if from_bottom <= 3 and n > 3:
        return {1: "", 2: "second ", 3: "third "}[from_bottom] + bottom
    return ordinal(n) + top


def ordinal(n):
    if n <= 3:
        return {1: "", 2: "second ", 3: "third "}[n]
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix} "


def build():
    pop = cso.fetch("F1001")
    pop = pop[(pop["Sex"] == "Both sexes") & pop["County"].isin(figures.COUNTIES)]
    pop = pop[["CensusYear", "County", "VALUE"]].rename(columns={"CensusYear": "census_year", "County": "county", "VALUE": "population"})
    # Same selection as the rents map in analysis/housing, so both read the same saved table.
    rent = cso.fetch("RIA02", where={"Number of Bedrooms": ["All bedrooms"], "Property Type": ["All property types"],
                                     "Location": figures.COUNTIES})
    rent = rent[["Year", "Location", "VALUE"]].rename(columns={"Year": "year", "Location": "county", "VALUE": "average_monthly_rent"})
    rent = rent.dropna()
    rent["average_monthly_rent"] = rent["average_monthly_rent"].round().astype(int)

    latest_census = pop.census_year.max()
    latest_rent = rent.year.max()
    rent_rank = (rent[rent.year == latest_rent].set_index("county")["average_monthly_rent"]
                 .rank(ascending=False, method="min").astype(int))
    pop_rank = (pop[pop.census_year == latest_census].set_index("county")["population"]
                .rank(ascending=False, method="min").astype(int))

    os.makedirs(OUT, exist_ok=True)
    for county in sorted(figures.COUNTIES):
        p = pop[pop.county == county].sort_values("census_year").reset_index(drop=True)
        r = rent[rent.county == county].sort_values("year").reset_index(drop=True)
        population_chart(county, p)
        rent_chart(county, r)
        write_page(county, p, r, pop_rank[county], rent_rank[county], latest_rent)
    write_list()


def population_chart(county, d):
    fig = figures.lines(d, "census_year", {"population": "Population"}, y_range=[0, d.population.max() * 1.1])
    fig.data[0].mode = "lines+markers"
    fig.data[0].marker = dict(size=4, color=style.BLUE)
    Chart(
        id=f"county-{slug(county)}-population", topic=TOPIC, listed=False, height=380,
        title=f"Population of County {county} at each census",
        subtitle=f"Number of people counted in County {county} at each census, {d.census_year.min()} to {d.census_year.max()}.",
        sources=[Source.cso("F1001", "Population at Each Census")],
        notes=["The census counts everyone present in the State on census night. Censuses were held every ten years "
               "until 1911, and more often since 1946. There was no census between 1911 and 1926."],
        data=d[["census_year", "population"]], figure=fig,
    ).write()


def rent_chart(county, d):
    fig = figures.lines(d, "year", {"average_monthly_rent": "Average rent"}, prefix="€",
                        y_range=[0, d.average_monthly_rent.max() * 1.15])
    fig.update_yaxes(tickformat=",.0f")
    Chart(
        id=f"county-{slug(county)}-rent", topic=TOPIC, listed=False, height=380,
        title=f"Average rent in County {county}",
        subtitle=f"Average monthly rent on new private tenancies registered with the Residential Tenancies Board, "
                 f"{d.year.min()} to {d.year.max()}.",
        sources=[Source.cso("RIA02", "RTB Average Monthly Rent Report")],
        notes=["Rents are those agreed on new tenancies registered with the RTB in each year, for all property types "
               "and sizes. They are not adjusted for inflation.",
               "Rents on existing tenancies, and social housing rents, are not included."],
        data=d[["year", "average_monthly_rent"]], figure=fig,
    ).write()


def write_page(county, p, r, pop_rank, rent_rank, latest_rent):
    last, first = p.iloc[-1], p.iloc[0]
    prev = p.iloc[-2]
    change = (last.population / prev.population - 1) * 100
    grew = f"up {change:.1f}%" if change > 0 else f"down {abs(change):.1f}%"
    share = last.population / first.population * 100
    facts = [
        f"At the {last.census_year} census, {last.population:,} people lived in County {county}, "
        f"{grew} on {prev.census_year}. It had the {rank_words(pop_rank, 'largest', 'smallest')} population of the 26 counties.",
        f"Its population in {last.census_year} was "
        + (f"{share / 100:.1f} times" if share >= 150 else f"{share:.0f}% of")
        + f" its population in {first.census_year}, the last census before the Great Famine.",
    ]
    rr = r[r.year == latest_rent]
    if len(rr):
        facts.append(f"In {latest_rent}, the average monthly rent on a new tenancy in County {county} was "
                     f"€{rr.average_monthly_rent.iloc[0]:,}, the {rank_words(rent_rank, 'highest', 'lowest')} of the 26 counties.")
    s = slug(county)
    text = f'''---
title: "{county}"
description: "Population and rents in County {county}, from the census and the Residential Tenancies Board."
image: ../images/social/county-{s}-population.png
---

<!-- Generated by analysis/counties/make_charts.py. Edit the script, not this file. -->

::: {{.key-facts}}
{(chr(10) * 2).join(facts)}
:::

## Population

{{{{< chart county-{s}-population height=560 >}}}}

The [Where people live](/population/counties.qmd) page compares every county with its population in 1841.

## Rents

{{{{< chart county-{s}-rent height=560 >}}}}

The [Rents](/housing/rents.qmd) page maps rents in every county.
'''
    with open(os.path.join(OUT, f"{s}.qmd"), "w", encoding="utf-8") as f:
        f.write(text)


def write_list():
    links = " · ".join(f"[{c}]({slug(c)}.qmd)" for c in sorted(figures.COUNTIES))
    with open(os.path.join(OUT, "_list.md"), "w", encoding="utf-8") as f:
        f.write("<!-- Generated by analysis/counties/make_charts.py. -->\n\n::: {.county-list}\n" + links + "\n:::\n")
