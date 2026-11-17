"""Energy charts: renewable energy, where Ireland's electricity comes from,
reliance on imported energy, and household electricity prices, compared with
the EU. Emissions are in the environment topic and data centres in the AI topic."""
import plotly.graph_objects as go

from ibn import eu, eurostat, figures, style
from ibn.chart import Chart, Source

TOPIC = "energy"
EU_GEO = eurostat.EU27 + [eurostat.EU]
REN_SOURCE = ("nrg_ind_ren", "Share of energy from renewable sources")
REN_NOTE = ("Measured as a share of gross final energy consumption, the energy used by homes, businesses and "
            "transport, using the method set out in EU rules on renewable energy.")


def build():
    renewables()
    renewable_electricity_eu()
    electricity_sources()
    import_dependency()
    electricity_prices_eu()


def _ren(balance):
    df = eurostat.fetch("nrg_ind_ren", geo=EU_GEO, nrg_bal=["REN", "REN_ELC"], unit="PC")
    return df[df.nrg_bal == balance]


def renewables():
    eu.lines_chart(
        "energy-renewables", TOPIC, "Renewable energy in Ireland and the EU",
        "Share of energy used that comes from renewable sources, {first} to {last}.",
        Source.eurostat(*REN_SOURCE), _ren("REN"),
        lambda w: (lambda a, b: f"In {b.year:.0f}, {b.ireland:.1f}% of the energy used in Ireland came from renewable "
                                f"sources, up from {a.ireland:.1f}% in {a.year:.0f}. The EU figure was {b.eu_average:.1f}%.")
                  (w.iloc[0], w.dropna().iloc[-1]),
        notes=[REN_NOTE, "Covers all energy, including heating and transport, not just electricity."],
        suffix="%", y_range=[0, None])


def renewable_electricity_eu():
    eu.rank_chart(
        "energy-renewable-electricity-eu", TOPIC, "Renewable electricity across the EU",
        "Share of electricity consumption from renewable sources, EU countries, {year}.",
        Source.eurostat(*REN_SOURCE), _ren("REN_ELC"),
        lambda y, ie, ev, place: f"In {y}, {ie:.1f}% of the electricity used in Ireland came from renewable sources, "
                                 f"compared with {ev:.1f}% across the EU. Ireland's share was {place}.",
        notes=["Measured using the method set out in EU rules on renewable energy, which evens out year-to-year "
               "changes in wind and rainfall."],
        suffix="%")


SOURCES = {"Natural gas": ["G3000"], "Wind": ["RA300"], "Coal and peat": ["C0000X0350-0370", "P1000"],
           "Oil": ["O4000XBIO"], "Other renewables": ["RA100", "RA420", "BIOE", "W6210"]}


def electricity_sources():
    df = eurostat.fetch("nrg_bal_peh", geo="IE", nrg_bal="GEP", unit="GWH")
    p = df.pivot_table(index="time", columns="siec", values="value")
    w = p[["TOTAL"]].copy()
    for name, codes in SOURCES.items():
        w[name] = p[[c for c in codes if c in p]].fillna(0).sum(axis=1)
    w["Other"] = (w.TOTAL - w[list(SOURCES)].sum(axis=1)).clip(lower=0)
    shares = (w[list(SOURCES) + ["Other"]].div(w.TOTAL, axis=0) * 100).round(1).reset_index().rename(columns={"time": "year"})
    shares["year"] = shares.year.astype(int)
    a, b = shares.iloc[0], shares.iloc[-1]
    cols = ["Natural gas", "Wind", "Coal and peat", "Oil", "Other renewables"]
    fig = figures.lines(shares, "year", {c: c for c in cols},
                        colours=[style.INK_3, style.AQUA, style.INK, style.ORANGE, style.GOLD], value_format=".0f",
                        suffix="%", y_range=[0, 100])
    fig.update_layout(margin=dict(r=170))
    Chart(
        id="energy-electricity-sources", topic=TOPIC,
        title="Where Ireland's electricity comes from",
        subtitle=f"Share of electricity generated in Ireland, by source, {a.year:.0f} to {b.year:.0f}.",
        sources=[Source.eurostat("nrg_bal_peh", "Gross production of electricity and derived heat by fuel")],
        notes=["Gross electricity generation in Ireland. Electricity imported through the interconnectors with Great "
               "Britain is not included.",
               "Other renewables are hydro, solar, bioenergy and the renewable part of waste. Hydro includes pumped "
               "storage. The data file also has a small 'Other' group."],
        key_fact=f"In {b.year:.0f}, {b.Wind:.0f}% of the electricity generated in Ireland came from wind and "
                 f"{b['Natural gas']:.0f}% from natural gas. In {a.year:.0f}, {a['Coal and peat']:.0f}% came from coal "
                 f"and peat.",
        data=shares, figure=fig,
    ).write()


def import_dependency():
    df = eurostat.fetch("nrg_ind_id", geo=EU_GEO, siec="TOTAL", unit="PC")
    eu.lines_chart(
        "energy-import-dependency", TOPIC, "Reliance on imported energy",
        "Net energy imports as a share of all energy used, Ireland and the EU, {first} to {last}.",
        Source.eurostat("nrg_ind_id", "Energy import dependency by products"), df,
        lambda w: (lambda b: f"In {b.year:.0f}, Ireland imported {b.ireland:.0f}% of the energy it used, compared with "
                             f"{b.eu_average:.0f}% for the EU as a whole.")(w.dropna().iloc[-1]),
        notes=["Net imports are imports minus exports. The share is of gross available energy, all the energy "
               "supplied in the country, including fuel for international ships and aircraft."],
        value_format=".0f", suffix="%", y_range=[0, 100])


def electricity_prices_eu():
    df = eurostat.fetch("nrg_pc_204", geo=EU_GEO, siec="E7000", nrg_cons="KWH2500-4999", unit="KWH", tax="I_TAX",
                        currency="EUR")
    df = df.dropna(subset=["value"])
    counts = df[df.geo.isin(eurostat.EU27)].groupby("time").geo.nunique()
    periods = [t for t in counts[counts >= 20].index if not df[(df.time == t) & (df.geo == "IE")].empty]
    period = max(periods)
    half = {"S1": "first", "S2": "second"}[period[-2:]]
    d = df[df.time == period].assign(time=int(period[:4]))
    eu.rank_chart(
        "energy-electricity-prices-eu", TOPIC, "Household electricity prices across the EU",
        "Average price of electricity for households, euro per kilowatt hour including taxes, EU countries, " + half +
        " half of {year}.",
        Source.eurostat("nrg_pc_204", "Electricity prices for household consumers, bi-annual data"), d,
        lambda y, ie, ev, place: f"In the {half} half of {y}, households in Ireland paid on average €{ie:.3f} per "
                                 f"kilowatt hour of electricity, including taxes, compared with €{ev:.3f} across the EU. "
                                 f"Ireland's price was {place}.",
        notes=["For households using between 2,500 and 4,999 kilowatt hours a year, a typical amount. Prices include "
               "network charges, taxes and levies, averaged over the half year.",
               "Prices are in euro and are not adjusted for differences in incomes or the cost of living."],
        value_format=".3f", prefix="€")
