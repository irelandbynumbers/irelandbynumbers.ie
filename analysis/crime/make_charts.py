"""Crime charts, from CSO recorded crime statistics (Garda PULSE data)."""
from ibn import cso, figures, style
from ibn.chart import Chart, Source

TOPIC = "crime"

RESERVATION = ("The CSO publishes recorded crime figures as statistics under reservation. This means the "
               "quality of the underlying Garda data does not yet meet the standards the CSO requires of official "
               "statistics, and the figures should be read with that in mind.")

THEFT = {
    "Theft from shop (0822)": "Theft from shops",
    "Other thefts, handling stolen property (084)": "Other thefts",
    "Burglary (not aggravated) (0712)": "Burglary",
    "Theft/taking of vehicle and related offences (081)": "Theft or taking of vehicles",
    "Theft from person (0821)": "Theft from the person",
}


def build():
    thefts_by_type()


def thefts_by_type():
    df = cso.fetch("CJA01")
    d = df[df["Type of Offence"].isin(THEFT)].pivot_table(index="Year", columns="Type of Offence", values="VALUE").reset_index()
    cols = {k: v.lower().replace(" ", "_") for k, v in THEFT.items()}
    d = d.rename(columns=cols)[["Year", *cols.values()]]
    for c in cols.values():
        d[c] = d[c].astype(int)
    series = {cols[k]: v for k, v in THEFT.items()}
    fig = figures.lines(d, "Year", series, label_last=False, y_range=[0, d[list(cols.values())].max().max() * 1.08])
    fig.update_layout(showlegend=True, legend=style.legend_top(), margin=dict(t=64))
    Chart(
        id="crime-thefts", topic=TOPIC,
        title="Recorded thefts and burglaries",
        subtitle=f"Number of theft and burglary incidents recorded by An Garda Síochána each year, by type, {d.Year.min()} to {d.Year.max()}.",
        sources=[Source.cso("CJA01", "Recorded crime incidents")],
        notes=[RESERVATION,
               "Recorded crime counts incidents reported to or discovered by the Gardaí. Changes can reflect how often "
               "crimes are reported and recorded, as well as how often they happen.",
               "Other thefts covers thefts that fall outside the other categories shown, along with handling stolen property. "
               "This table does not show theft from vehicles separately. Burglary excludes aggravated burglary, which numbers a few hundred a year."],
        data=d, figure=fig,
    ).write()
