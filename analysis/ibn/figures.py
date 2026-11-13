"""Ready-made figures in the house style: lines over time and county maps.

Each returns a plotly Figure to pass to Chart(figure=...). Build anything
else with plotly directly, starting from style.base_layout().
"""
import json
import os

import plotly.graph_objects as go

from . import style

GEO_FILE = os.path.join(os.path.dirname(__file__), "ireland_counties.geojson")
COUNTIES = [f["id"] for f in json.load(open(GEO_FILE, encoding="utf-8"))["features"] if f["id"] != "Northern Ireland"]
# Charts load the outlines from one shared file (copied to charts/lib/ by
# Chart.write), so a map with a slider doesn't repeat them in every frame.
GEO = "lib/ireland_counties.geojson"


def lines(df, x, series, colours=None, value_format=",.0f", suffix="", prefix="",
          label_last=True, y_range=None, y_title="", hover_x=None):
    """One line per column in `series` (a dict of column -> label), with the
    latest value labelled at the end of each line so no legend is needed."""
    colours = colours or style.SLOTS
    fig = go.Figure()
    for (col, label), colour in zip(series.items(), colours):
        d = df[[x, col]].dropna()
        fig.add_trace(go.Scatter(
            x=d[x], y=d[col], mode="lines", name=label, line=dict(color=colour, width=2.5),
            hovertemplate=f"<b>{label}</b>: {prefix}%{{y:{value_format}}}{suffix}<extra></extra>",
        ))
        if label_last and len(d):
            last = d.iloc[-1]
            fig.add_trace(go.Scatter(x=[last[x]], y=[last[col]], mode="markers", hoverinfo="skip",
                                     marker=dict(color=colour, size=8, line=dict(color=style.SURFACE, width=2))))
            text = f"{prefix}{format(last[col], value_format)}{suffix}"
            fig.add_annotation(x=last[x], y=last[col], xanchor="left", xshift=8, showarrow=False,
                               text=f"<b>{label}</b><br>{text}" if len(series) > 1 else f"<b>{text}</b>",
                               align="left", font=dict(color=style.INK, size=13))
    fig.update_layout(style.base_layout(
        hovermode="x unified",
        margin=dict(l=56, r=120 if label_last else 24, t=16, b=40),
        xaxis=style.axis(showline=True, range=[df[x].min(), df[x].max()] if label_last else None, showspikes=True, spikecolor=style.INK_3, spikethickness=1,
                         spikedash="solid", hoverformat=hover_x),
        yaxis=style.value_axis(range=y_range, tickformat=value_format.replace(".0f", "~s") if value_format == ",.0f" else value_format,
                               ticksuffix=suffix, tickprefix=prefix, title=dict(text=y_title)),
    ))
    return fig


def county_map(df, county, value, time=None, colorscale=None, value_format=",.0f", suffix="",
               legend_title="", zmin=None, zmax=None, hover_extra=None):
    """A choropleth of the 26 counties. With `time`, a slider steps through
    each period (the latest shown first) on one fixed colour scale, so the
    change is visible."""
    colorscale = colorscale or style.SEQUENTIAL
    missing = set(df[county]) - set(COUNTIES)
    assert not missing, f"county names not in the map: {sorted(missing)}"
    zmin = df[value].min() if zmin is None else zmin
    zmax = df[value].max() if zmax is None else zmax
    periods = sorted(df[time].unique()) if time else [None]

    def trace(period):
        d = df if period is None else df[df[time] == period]
        extra = "" if not hover_extra else "<br>" + hover_extra
        return go.Choropleth(
            geojson=GEO, locations=d[county], z=d[value], featureidkey="id",
            colorscale=colorscale, zmin=zmin, zmax=zmax,
            marker_line=dict(color="#ffffff", width=0.8),
            colorbar=dict(title=dict(text=legend_title, side="top", font=dict(size=12, color=style.INK_2)),
                          orientation="h", x=0, xanchor="left", y=1.0, yanchor="bottom", len=0.6, thickness=10,
                          tickformat=value_format.replace(".0f", "~s") if value_format == ",.0f" else value_format,
                          ticksuffix=suffix, tickfont=dict(size=11, color=style.INK_3), outlinewidth=0),
            customdata=d[[county]].values if not hover_extra else d.values,
            hovertemplate=f"<b>%{{location}}</b><br>%{{z:{value_format}}}{suffix}{extra}<extra></extra>",
        )

    context = go.Choropleth(  # Northern Ireland as a quiet outline, for context
        geojson=GEO, locations=["Northern Ireland"], z=[0], featureidkey="id",
        colorscale=[[0, "#fafaf8"], [1, "#fafaf8"]], showscale=False,
        marker_line=dict(color=style.CONTEXT, width=0.6), hoverinfo="skip")
    latest = periods[-1]
    fig = go.Figure(data=[context, trace(latest)])
    fig.update_geos(visible=False, projection_type="mercator", lonaxis_range=[-10.7, -5.4],
                    lataxis_range=[51.35, 55.45], bgcolor=style.SURFACE)
    layout = style.base_layout(margin=dict(l=0, r=0, t=40, b=0 if time is None else 70),
                               geo=dict(bgcolor=style.SURFACE))
    if time is not None and len(periods) > 1:
        fig.frames = [go.Frame(name=str(p), data=[context, trace(p)]) for p in periods]
        layout["sliders"] = [dict(
            active=len(periods) - 1, x=0.05, len=0.9, y=0, yanchor="top", pad=dict(t=10, b=0),
            currentvalue=dict(prefix="", font=dict(size=14, color=style.INK)),
            font=dict(color=style.INK_3, size=11), bgcolor=style.LAND, bordercolor=style.GRID,
            activebgcolor=style.BLUE,
            steps=[dict(label=str(p), method="animate",
                        args=[[str(p)], dict(mode="immediate", frame=dict(duration=0, redraw=True), transition=dict(duration=0))])
                   for p in periods],
        )]
    fig.update_layout(layout)
    return fig
