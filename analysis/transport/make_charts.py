"""Transport charts: road safety, how people travel, public transport use, and
the cars on Irish roads."""
import pandas as pd
import plotly.graph_objects as go

from ibn import cso, figures, style
from ibn.chart import Chart, Source

TOPIC = "transport"
RSA_NOTE = ("Road Safety Authority statistics, published by the CSO. Recent figures are provisional and may be "
            "revised.")
CENSUS_NOTE = ("The census asks how each person usually travels the longest part of their journey to work, school or "
               "college. People who work mainly at or from home, and people who did not answer, are left out.")


def build():
    road_deaths()
    road_deaths_by_user()
    serious_injuries()
    road_deaths_map()
    journeys_by_mode()
    travel_to_school()
    travel_to_work()
    public_transport_weekly()
    rail_journeys()
    new_cars()
    new_car_fuel()
    electric_cars_eu()


# Road safety

def road_deaths():
    df = cso.fetch("ROA12")
    d = df[df["Road User Type"] == "All road users"][["Year", "VALUE"]].rename(columns={"VALUE": "deaths"})
    d = d.astype(int).sort_values("Year").reset_index(drop=True)
    fig = figures.lines(d, "Year", {"deaths": "Road deaths"}, y_range=[0, d.deaths.max() * 1.1])
    a, b = d.iloc[0], d.iloc[-1]
    low = d.loc[d.deaths.idxmin()]
    Chart(
        id="transport-road-deaths", topic=TOPIC,
        title="Deaths on Irish roads",
        subtitle=f"Number of people killed in road collisions each year, {a.Year} to {b.Year}.",
        sources=[Source.cso("ROA12", "Persons Killed in Road Traffic Collisions")],
        notes=[RSA_NOTE],
        key_fact=f"{b.deaths} people were killed on Irish roads in {b.Year}, compared with {a.deaths} in {a.Year}. "
                 f"The lowest number was {low.deaths}, in {low.Year}.",
        data=d, figure=fig,
    ).write()


USERS = {"Pedestrians": "pedestrians", "Pedal cyclists": "cyclists", "Motor cyclists": "motorcyclists",
         "All Car users": "car_users"}


def road_deaths_by_user():
    df = cso.fetch("ROA12")
    d = df[df["Road User Type"].isin(USERS)].pivot_table(index="Year", columns="Road User Type", values="VALUE")
    d = d.rename(columns=USERS)[list(USERS.values())].reset_index().astype(int)
    fig = figures.lines(d, "Year", {"car_users": "Car drivers and passengers", "pedestrians": "Pedestrians",
                                    "motorcyclists": "Motorcyclists", "cyclists": "Cyclists"},
                        label_last=False, y_range=[0, d.car_users.max() * 1.1])
    fig.update_layout(showlegend=True, legend=style.legend_top(), margin=dict(t=40))
    a, b = d.iloc[0], d.iloc[-1]
    Chart(
        id="transport-road-deaths-by-user", topic=TOPIC,
        title="Road deaths by type of road user",
        subtitle=f"Number of people killed in road collisions, by how they were travelling, {a.Year} to {b.Year}.",
        sources=[Source.cso("ROA12", "Persons Killed in Road Traffic Collisions")],
        notes=["Car users include drivers and passengers. People travelling in buses, taxis and goods vehicles, and other "
               "or unknown road users, are not shown but are counted in the total on the chart above.", RSA_NOTE],
        key_fact=f"In {b.Year}, {b.car_users} car drivers and passengers, {b.pedestrians} pedestrians, {b.motorcyclists} "
                 f"motorcyclists and {b.cyclists} cyclists were killed on Irish roads.",
        data=d, figure=fig,
    ).write()


def serious_injuries():
    df = cso.fetch("ROA40")
    d = df.pivot_table(index=["Year", "Road User Type"], columns="Statistic Label", values="VALUE").reset_index()
    d = d.rename(columns={"Road User Type": "road_user", "Fatalities": "deaths", "Serious injuries": "serious_injuries",
                          "All fatalities and serious injuries": "deaths_and_serious_injuries"})
    order = {"Drivers": "Drivers", "Pedestrians": "Pedestrians", "Pedal cyclists": "Cyclists", "Motor cyclists": "Motorcyclists"}
    w = d.pivot_table(index="Year", columns="road_user", values="deaths_and_serious_injuries").reset_index()
    w = w.rename(columns={k: v.lower() for k, v in order.items()})
    cols = {v.lower(): v for v in order.values()}
    fig = figures.lines(w, "Year", cols, label_last=False, y_range=[0, w[list(cols)].max().max() * 1.1])
    fig.update_layout(showlegend=True, legend=style.legend_top(), margin=dict(t=40))
    fig.update_xaxes(dtick=1)
    year = int(d.Year.max())
    y = d[d.Year == year].set_index("road_user")
    first = d[d.Year == d.Year.min()].set_index("road_user")
    Chart(
        id="transport-serious-injuries", topic=TOPIC,
        title="People killed or seriously injured on the roads",
        subtitle=f"Number of people killed or seriously injured in road collisions, for four types of road user, "
                 f"{int(d.Year.min())} to {year}.",
        sources=[Source.cso("ROA40", "Road Traffic Fatalities and Serious Injuries")],
        notes=["Drivers are drivers of cars and other motor vehicles. Passengers, and other road users, are not included "
               "in this table. The table has no figures for cyclists in 2019 or for drivers in 2025.", RSA_NOTE],
        key_fact=f"In {year}, {y.loc['Pedal cyclists', 'deaths_and_serious_injuries']:.0f} cyclists and "
                 f"{y.loc['Pedestrians', 'deaths_and_serious_injuries']:.0f} pedestrians were killed or seriously injured "
                 f"on Irish roads.",
        data=w.astype("Int64"),
        figure=fig,
    ).write()


def road_deaths_map():
    df = cso.fetch("ROA15")
    last = int(df.Year.max())
    years = list(range(last - 4, last + 1))
    k = df[(df["Statistic Label"] == "Persons Killed") & df.Year.isin(years)].copy()
    k["county"] = k.County.str.replace("Co. ", "", regex=False)
    d = k.groupby("county").VALUE.sum().astype(int).rename("deaths").reset_index()
    pop = cso.fetch("F1001")
    pop = pop[(pop.Sex == "Both sexes") & pop.County.isin(figures.COUNTIES) & (pop.CensusYear == 2022)]
    d["population"] = d.county.map(dict(zip(pop.County, pop.VALUE))).astype(int)
    d["per_100000_people_per_year"] = (d.deaths / len(years) / d.population * 100000).round(1)
    fig = figures.county_map(d[["county", "per_100000_people_per_year", "deaths"]], "county", "per_100000_people_per_year",
                             value_format=".1f", legend_title="Deaths per 100,000 people a year",
                             hover_extra="%{customdata[2]} deaths in " + f"{years[0]} to {last}")
    d = d.sort_values("per_100000_people_per_year", ascending=False).reset_index(drop=True)
    hi, lo = d.iloc[0], d.iloc[-1]
    Chart(
        id="transport-road-deaths-map", topic=TOPIC, kind="map", height=560,
        title="Road deaths by county",
        subtitle=f"Average number of people killed in road collisions each year per 100,000 people, by county, "
                 f"{years[0]} to {last}.",
        sources=[Source.cso("ROA15", "Persons Killed and Injured in Road Traffic Collisions by County"),
                 Source.cso("F1001", "Census of Population, population by county")],
        notes=["Five years are added together because the numbers in smaller counties are low and vary a lot from "
               "year to year. Rates use each county's population at the 2022 census.", RSA_NOTE],
        key_fact=f"From {years[0]} to {last}, road deaths were highest relative to population in {hi.county}, at "
                 f"{hi.per_100000_people_per_year:.1f} a year per 100,000 people, and lowest in {lo.county}, at "
                 f"{lo.per_100000_people_per_year:.1f}.",
        data=d, figure=fig,
    ).write()


# How people travel

def _grouped_bars(d, label, groups, colours, suffix="%"):
    """Horizontal bars, one group per row of `d`, one bar per column in `groups`."""
    fig = go.Figure()
    for (col, name), colour in zip(groups.items(), colours):
        fig.add_trace(go.Bar(y=d[label], x=d[col], name=name, orientation="h",
                             marker=dict(color=colour, cornerradius=3),
                             text=[f"{v:.0f}{suffix}" for v in d[col]], textposition="outside", cliponaxis=False,
                             textfont=dict(color=style.INK_2, size=11),
                             hovertemplate=f"<b>%{{y}}</b>, {name}: %{{x:.1f}}{suffix}<extra></extra>"))
    fig.update_layout(style.base_layout(
        barmode="group", bargap=0.25, bargroupgap=0.05, showlegend=True, legend=dict(style.legend_top(), traceorder="normal"),
        margin=dict(l=8, r=48, t=40, b=32),
        xaxis=style.value_axis(ticksuffix=suffix),
        yaxis=style.axis(automargin=True, autorange="reversed", tickfont=dict(color=style.INK_2, size=12))))
    return fig


def journeys_by_mode():
    df = cso.fetch("NTA10")
    year = int(df.Year.max())
    modes = {"Private car - driver/passenger": "Car", "Walk": "Walking", "Bus": "Bus", "Cycle": "Cycling",
             "Rail/DART/Luas": "Train, DART or Luas", "Taxi/hackney": "Taxi", "Van": "Van",
             "Lorry/motorcycle": "Motorcycle or lorry", "Other mode of transport n.e.c.": "Other"}
    y = df[(df.Year == year) & df["Mode of Travel"].isin(modes)]
    d = y[y.Region == "Ireland"].assign(mode=lambda x: x["Mode of Travel"].map(modes))
    d = d.set_index("mode").loc[list(modes.values())].reset_index()[["mode", "VALUE"]].rename(columns={"VALUE": "percent"})
    d = pd.concat([d[d["mode"] != "Other"].sort_values("percent", ascending=False), d[d["mode"] == "Other"]])
    shown = d.iloc[::-1]
    fig = go.Figure(go.Bar(y=shown["mode"], x=shown.percent, orientation="h", marker=dict(color=style.BLUE, cornerradius=3),
                           text=[f"{v:.1f}%" for v in shown.percent], textposition="outside", cliponaxis=False,
                           textfont=dict(color=style.INK_2, size=12),
                           hovertemplate="<b>%{y}</b>: %{x:.1f}%<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=48, t=8, b=32), bargap=0.3,
                                        xaxis=style.value_axis(ticksuffix="%"),
                                        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=12))))
    r = d.set_index("mode").percent
    regions = y.pivot_table(index="Region", columns="Mode of Travel", values="VALUE")[list(modes)]
    regions = regions.rename(columns=modes).reset_index()
    Chart(
        id="transport-journeys-by-mode", topic=TOPIC, height=420,
        title="How people make their journeys",
        subtitle=f"Share of all journeys by main mode of travel, {year}.",
        sources=[Source.cso("NTA10", "National Travel Survey, distribution of journeys by mode of travel")],
        notes=["From the CSO's National Travel Survey, which asks a sample of people about the journeys they make. "
               "Journeys for any reason are included, not just to work or school. Cycling includes electric bikes. "
               "Car includes drivers and passengers. As a survey, its figures are estimates.",
               "The data file also has the figures for each region."],
        key_fact=f"In {year}, {r['Car']:.0f}% of journeys were made by car, {r['Walking']:.0f}% on foot, "
                 f"{r['Bus']:.0f}% by bus and {r['Cycling']:.0f}% by bike.",
        data=regions, figure=fig,
    ).write()


CENSUS_MODES = {"On Foot": "Walking", "Bicycle": "Cycling", "Bus, minibus or coach": "Bus or coach",
                "Train, DART or LUAS": "Train, DART or Luas", "Car passenger": "Car, as passenger",
                "Car Driver": "Car, as driver"}


def _census_shares(statistic):
    rows = []
    for code, year in [("SAP2016T11T1PROV", 2016), ("SAP2022T11T1PROV", 2022)]:
        df = cso.fetch(code)
        df = df[df["Statistic Label"] == statistic]
        area = next(c for c in df.columns if c.startswith("Province"))
        s = df.groupby("Means of Travel").VALUE.sum() if year == 2016 else df[df[area] == "Ireland"].set_index("Means of Travel").VALUE
        travelling = s["Total"] - s.get("Work mainly at or from home", 0) - s["Not stated"]
        for k, v in CENSUS_MODES.items():
            rows.append(dict(year=year, mode=v, people=int(s[k]), percent=round(s[k] / travelling * 100, 1)))
        other = travelling - sum(s[k] for k in CENSUS_MODES)
        rows.append(dict(year=year, mode="Other", people=int(other), percent=round(other / travelling * 100, 1)))
    long = pd.DataFrame(rows)
    wide = long.pivot_table(index="mode", columns="year", values="percent").reindex(list(CENSUS_MODES.values()) + ["Other"])
    wide.columns = [f"percent_{c}" for c in wide.columns]
    return long, wide.reset_index()


def travel_to_school():
    long, d = _census_shares("Population aged 5 years and over by means of travel to school or college")
    fig = _grouped_bars(d, "mode", {"percent_2016": "2016", "percent_2022": "2022"}, [style.CONTEXT, style.BLUE])
    r = d.set_index("mode")
    car = r.loc["Car, as passenger"] + r.loc["Car, as driver"]
    Chart(
        id="transport-travel-to-school", topic=TOPIC, height=440,
        title="How pupils and students travel to school or college",
        subtitle="Share of people aged 5 and over travelling to school or college, by main means of travel, census 2016 "
                 "and 2022.",
        sources=[Source.cso("SAP2016T11T1PROV", "Census 2016 Small Area Population Statistics, means of travel"),
                 Source.cso("SAP2022T11T1PROV", "Census 2022 Small Area Population Statistics, means of travel")],
        notes=[CENSUS_NOTE,
               "Includes primary and secondary pupils, and students at college or university. Most car journeys to "
               "school are as passengers. Other includes motorcycles, vans and lorries."],
        key_fact=f"At the 2022 census, {car.percent_2022:.0f}% of pupils and students went to school or college by car, "
                 f"{r.loc['Walking', 'percent_2022']:.0f}% walked and {r.loc['Cycling', 'percent_2022']:.1f}% cycled.",
        data=long, figure=fig,
    ).write()


def travel_to_work():
    long, d = _census_shares("Population aged 5 years and over by means of travel to work")
    fig = _grouped_bars(d, "mode", {"percent_2016": "2016", "percent_2022": "2022"}, [style.CONTEXT, style.BLUE])
    r = d.set_index("mode")
    Chart(
        id="transport-travel-to-work", topic=TOPIC, height=440,
        title="How people travel to work",
        subtitle="Share of people travelling to work, by main means of travel, census 2016 and 2022.",
        sources=[Source.cso("SAP2016T11T1PROV", "Census 2016 Small Area Population Statistics, means of travel"),
                 Source.cso("SAP2022T11T1PROV", "Census 2022 Small Area Population Statistics, means of travel")],
        notes=[CENSUS_NOTE, "Other includes motorcycles, vans and lorries. Many more people worked from home in 2022 "
               "than in 2016, and they are not included here."],
        key_fact=f"At the 2022 census, {r.loc['Car, as driver', 'percent_2022']:.0f}% of people travelling to work drove, "
                 f"{r.loc['Walking', 'percent_2022']:.0f}% walked and {r.loc['Cycling', 'percent_2022']:.0f}% cycled.",
        data=long, figure=fig,
    ).write()


# Public transport

def _week_start(label):
    y, w = label.lower().split(" week ")
    return pd.to_datetime(f"{y}-W{int(w):02d}-1", format="%G-W%V-%u")


def public_transport_weekly():
    t = cso.fetch("THA25")
    t["Week"] = t.Week.str.replace("week", "Week")   # one week is labelled in lower case
    t = t.pivot_table(index="Week", columns="Mode of Transport", values="VALUE").reset_index()
    luas = cso.fetch("TII03")
    luas = luas[luas["Luas Line"] == "All Luas lines"][["Week", "VALUE"]].rename(columns={"VALUE": "luas"})
    d = t.merge(luas, on="Week", how="outer")
    d = d.rename(columns={"Week": "week", "Dublin Metro Bus": "dublin_bus", "Bus, excluding Dublin Metro": "other_bus",
                          "Rail": "rail"})
    d = d[~d.week.str.endswith("Week 53")]   # a 53rd week appears only in some years and is mostly empty
    d["week_starting"] = d.week.map(_week_start)
    d = d.sort_values("week_starting").reset_index(drop=True)
    d = d[d.week_starting <= t["Week"].map(_week_start).max()]
    cols = {"dublin_bus": "Dublin city buses", "other_bus": "Other buses", "rail": "Rail", "luas": "Luas"}
    s = d[["week_starting"]].copy()
    for c in cols:
        s[c] = (d[c].rolling(4, min_periods=4).mean() / 1e6).round(2)
    fig = figures.lines(s, "week_starting", cols, value_format=".1f", suffix="m", label_last=False,
                        y_range=[0, s[list(cols)].max().max() * 1.1], hover_x="%d %b %Y")
    fig.update_layout(showlegend=True, legend=style.legend_top(), margin=dict(t=40))
    last = d.iloc[-1]
    year = last.week_starting.year
    def total(y, c):
        x = d[d.week_starting.dt.year == y]
        return x[c].sum() / 1e6
    Chart(
        id="transport-public-transport", topic=TOPIC,
        title="Public transport journeys each week",
        subtitle=f"Passenger journeys per week by bus, rail and Luas, million, average of the last four weeks, "
                 f"{d.week.iloc[0][:4]} to {last.week[:4]}.",
        sources=[Source.cso("THA25", "Weekly Public Transport Passenger Journeys"),
                 Source.cso("TII03", "Weekly Luas Passenger Numbers")],
        notes=["Dublin city buses are the services the CSO labels Dublin Metro bus. Other buses are the remaining bus "
               "services in the National Transport Authority's figures. Rail includes the DART. Rail figures start in "
               "2020. Bus and rail figures come from the National Transport Authority, and Luas figures from Transport "
               "Infrastructure Ireland. Recent weeks may include estimates.",
               "Each point is the average of four weeks, to smooth out holidays. The data file has the weekly figures."],
        key_fact=f"In the four weeks to {(last.week_starting + pd.Timedelta(days=6)):%-d %B %Y}, Dublin city buses carried "
                 f"an average of {s.dublin_bus.iloc[-1]:.1f} million passenger journeys a week, rail "
                 f"{s.rail.iloc[-1]:.1f} million and Luas {s.luas.iloc[-1]:.1f} million.",
        data=d[["week", "week_starting", "dublin_bus", "other_bus", "rail", "luas"]].assign(
            week_starting=d.week_starting.dt.strftime("%Y-%m-%d")),
        figure=fig,
    ).write()


def rail_journeys():
    df = cso.fetch("TCA01")
    d = df[df["Type of Journey"] == "All journeys"][["Year", "VALUE"]].rename(columns={"VALUE": "thousand_journeys"})
    d["million_journeys"] = (d.thousand_journeys / 1000).round(1)
    d = d.sort_values("Year").reset_index(drop=True)
    fig = figures.lines(d, "Year", {"million_journeys": "Rail journeys"}, value_format=".1f", suffix="m",
                        y_range=[0, d.million_journeys.max() * 1.1])
    a, b = d.iloc[0], d.iloc[-1]
    prev = d[d.Year < b.Year].loc[lambda x: x.million_journeys.idxmax()]
    Chart(
        id="transport-rail-journeys", topic=TOPIC,
        title="Rail journeys each year",
        subtitle=f"Passenger journeys on Iarnród Éireann trains, including the DART, million, {a.Year:.0f} to {b.Year:.0f}.",
        sources=[Source.cso("TCA01", "Passenger Journeys by Rail")],
        notes=["Includes mainline, Dublin suburban, DART and international journeys. Luas is not included."],
        key_fact=f"There were {b.million_journeys:.1f} million rail journeys in {b.Year:.0f}"
                 + (f", the highest number in figures going back to {a.Year:.0f}." if b.million_journeys >= prev.million_journeys else
                    f". The highest was {prev.million_journeys:.1f} million, in {prev.Year:.0f}."),
        data=d.assign(Year=d.Year.astype(int))[["Year", "thousand_journeys", "million_journeys"]], figure=fig,
    ).write()


# Cars

def new_cars():
    df = cso.fetch("TEA01")
    names = {"New Private Cars": "new_cars", "Secondhand Private Cars": "imported_used_cars"}
    d = df[df["Taxation Class"].isin(names)].pivot_table(index="Year", columns="Taxation Class", values="VALUE")
    d = d.rename(columns=names).reset_index().astype(int)
    fig = figures.lines(d, "Year", {"new_cars": "New cars", "imported_used_cars": "Used imports"},
                        y_range=[0, d[list(names.values())].max().max() * 1.1])
    b = d.iloc[-1]
    peak = d.loc[d.new_cars.idxmax()]
    Chart(
        id="transport-new-cars", topic=TOPIC,
        title="New and imported used cars",
        subtitle=f"Number of private cars licensed in Ireland for the first time, {d.Year.iloc[0]} to {b.Year}.",
        sources=[Source.cso("TEA01", "Vehicles Licensed for the First Time")],
        notes=["New cars are cars registered new in Ireland. Imported used cars are cars first registered abroad, "
               "and licensed in Ireland for the first time."],
        key_fact=f"{b.new_cars:,} new cars were licensed in {b.Year}, along with {b.imported_used_cars:,} imported used "
                 f"cars. New car sales peaked in {peak.Year}, at {peak.new_cars:,}.",
        data=d, figure=fig,
    ).write()


FUELS = {"Petrol": "Petrol", "Diesel": "Diesel", "hybrid": "Hybrid", "Petrol or Diesel plug-in hybrid electric": "Plug-in hybrid",
         "Electric": "Electric"}


def new_car_fuel():
    df = cso.fetch("TEA17")
    c = df[df["Type of Vehicle Registration"] == "New Private Cars"].pivot_table(index="Year", columns="Type of Fuel",
                                                                                 values="VALUE")
    c["hybrid"] = c["Petrol and electric hybrid"] + c["Diesel and electric hybrid"]
    d = pd.DataFrame({"Year": [int(y) for y in c.index]})
    for k, v in FUELS.items():
        d[v.lower().replace(" ", "_").replace("-", "_")] = c[k].values
    total = c["All fuel types"].values
    d["all_new_cars"] = total.astype(int)
    keys = [v.lower().replace(" ", "_").replace("-", "_") for v in FUELS.values()]
    colours = [style.CONTEXT, style.INK_3, style.GOLD, style.AQUA, style.BLUE]
    fig = go.Figure()
    for k, label, colour in zip(keys, FUELS.values(), colours):
        share = d[k] / total * 100
        d[f"{k}_percent"] = share.round(1)
        fig.add_trace(go.Bar(x=d.Year, y=share, name=label, marker=dict(color=colour),
                             hovertemplate=f"<b>{label}</b>: %{{y:.0f}}%<extra></extra>"))
    fig.update_layout(style.base_layout(barmode="stack", bargap=0.2, showlegend=True,
                                        legend=dict(style.legend_top(), traceorder="reversed"), hovermode="x unified",
                                        margin=dict(l=48, r=16, t=40, b=40),
                                        xaxis=style.axis(showline=True, dtick=1),
                                        yaxis=style.value_axis(ticksuffix="%", range=[0, 100])))
    a, b = d.iloc[0], d.iloc[-1]
    Chart(
        id="transport-new-car-fuel", topic=TOPIC,
        title="New cars by fuel type",
        subtitle=f"Share of new private cars licensed for the first time, by fuel, {a.Year:.0f} to {b.Year:.0f}.",
        sources=[Source.cso("TEA17", "New Vehicles Licensed for the First Time by Fuel Type")],
        notes=["Electric means battery electric cars only. Plug-in hybrids have a battery that can be charged from the "
               "mains as well as a petrol or diesel engine. Hybrids have a petrol or diesel engine and a smaller battery "
               "that cannot be plugged in. A handful of cars using other fuels are not shown.",
               "Covers new cars only, not imported used cars."],
        key_fact=f"In {b.Year:.0f}, {b.electric_percent:.0f}% of new cars were fully electric and a further "
                 f"{b.plug_in_hybrid_percent:.0f}% were plug-in hybrids, up from {a.electric_percent:.1f}% and "
                 f"{a.plug_in_hybrid_percent:.1f}% in {a.Year:.0f}.",
        data=d, figure=fig,
    ).write()


def electric_cars_eu():
    df = cso.fetch("TEA30")
    year = int(df.Year.max())
    y = df[df.Year == year].pivot_table(index="Country", columns="Statistic Label", values="VALUE")
    d = pd.DataFrame({
        "country": y.index,
        "electric_registrations": y["Electric passenger vehicle registrations"].astype(int).values,
        "all_registrations": y["Passenger vehicle fleet registrations"].astype(int).values,
        "electric_stock": y["Electric passenger vehicle stock"].astype(int).values,
        "all_stock": y["Passenger vehicle fleet stock"].astype(int).values,
    })
    d["country"] = d.country.replace({"Netherlands (the)": "Netherlands", "EU27 countries (from 2020)": "EU average"})
    d["electric_share_of_new"] = (d.electric_registrations / d.all_registrations * 100).round(1)
    d["electric_share_of_all_cars"] = (d.electric_stock / d.all_stock * 100).round(1)
    d = d.sort_values("electric_share_of_new").reset_index(drop=True)
    colours = [style.ORANGE if c == "Ireland" else style.INK_3 if c == "EU average" else style.CONTEXT for c in d.country]
    fig = go.Figure(go.Bar(y=d.country, x=d.electric_share_of_new, orientation="h", marker=dict(color=colours, cornerradius=3),
                           text=[f"{v:.0f}%" for v in d.electric_share_of_new], textposition="outside", cliponaxis=False,
                           textfont=dict(color=style.INK_2, size=11),
                           hovertemplate="<b>%{y}</b>: %{x:.1f}%<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=40, t=8, b=32), bargap=0.25,
                                        xaxis=style.value_axis(ticksuffix="%"),
                                        yaxis=style.axis(automargin=True, tickfont=dict(color=style.INK_2, size=11))))
    r = d.set_index("country")
    ie, eu = r.loc["Ireland"], r.loc["EU average"]
    rank = int((d[d.country != "EU average"].electric_share_of_new > ie.electric_share_of_new).sum()) + 1
    Chart(
        id="transport-electric-cars-eu", topic=TOPIC, height=640,
        title="Electric cars in Ireland and the EU",
        subtitle=f"Fully electric cars as a share of new passenger cars registered, EU countries, {year}.",
        sources=[Source.cso("TEA30", "Electric Passenger Vehicles, Ireland and EU")],
        notes=["Battery electric cars only. Plug-in hybrids are not included. Figures for Ireland differ slightly from "
               "the CSO's count of new cars licensed for the first time, shown in the chart above.",
               "The data file also shows the share of all cars on the road that are electric."],
        key_fact=f"In {year}, {ie.electric_share_of_new:.1f}% of new cars registered in Ireland were fully electric, "
                 f"compared with {eu.electric_share_of_new:.1f}% across the EU. Ireland had the {rank}{'st' if rank % 10 == 1 and rank != 11 else 'nd' if rank % 10 == 2 and rank != 12 else 'rd' if rank % 10 == 3 and rank != 13 else 'th'} highest share of the 27 countries. "
                 f"Electric cars made up {ie.electric_share_of_all_cars:.1f}% of all cars on Irish roads.",
        data=d.iloc[::-1].reset_index(drop=True), figure=fig,
    ).write()
