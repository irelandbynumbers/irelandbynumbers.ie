"""House style for every chart, shared with Fianaise.

Categorical colours go in fixed slot order; greys are for context and chrome.
"""
FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_3 = "#8a8984"
GRID = "#e8e7e3"
SURFACE = "#ffffff"
CONTEXT = "#c9c7c0"
LAND = "#f3f2ee"

BLUE, ORANGE, AQUA, PURPLE, GOLD, RED = "#2a78d6", "#eb6834", "#1baf7a", "#7a5cc7", "#c9930e", "#c93a3a"
SLOTS = [BLUE, ORANGE, AQUA, PURPLE, GOLD, RED]

# Sequential ramp for maps (light to dark blue) and a diverging one for change
# (orange for falls, blue for rises, a neutral middle).
SEQUENTIAL = [[0, "#eaf2fc"], [0.25, "#b7d3f4"], [0.5, "#6fa6e6"], [0.75, "#2a78d6"], [1, "#104281"]]
DIVERGING = [[0, "#b8441b"], [0.25, "#f0a07c"], [0.5, "#f3f2ee"], [0.75, "#7fb0ea"], [1, "#104281"]]


def base_layout(**kw):
    """Layout shared by every chart. Titles live in the page, not the plot."""
    layout = dict(
        font=dict(family=FONT, size=14, color=INK_2),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(family=FONT, size=13, color=INK)),
        margin=dict(l=56, r=24, t=16, b=40),
        showlegend=False,
    )
    layout.update(kw)
    return layout


def axis(**kw):
    a = dict(showgrid=False, zeroline=False, linecolor=GRID, ticks="",
             tickfont=dict(color=INK_3, size=12), title=dict(text=""))
    a.update(kw)
    return a


def value_axis(**kw):
    """The y axis of a line or bar chart: light gridlines, no line."""
    return axis(showgrid=True, gridcolor=GRID, linecolor="rgba(0,0,0,0)", **kw)


def legend_top():
    return dict(orientation="h", x=0, xanchor="left", y=1.02, yanchor="bottom",
                font=dict(color=INK, size=13), bgcolor="rgba(255,255,255,0)")
