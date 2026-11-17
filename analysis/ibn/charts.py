"""Small chart helpers shared by several topics."""
import plotly.graph_objects as go

from . import style

def hbars(d, label, value, value_format=".0f", suffix="%", colour=None):
    fig = go.Figure(go.Bar(y=d[label], x=d[value], orientation="h", marker=dict(color=colour or style.BLUE, cornerradius=3),
                           text=[f"{format(v, value_format)}{suffix}" for v in d[value]], textposition="outside",
                           cliponaxis=False, textfont=dict(color=style.INK, size=12),
                           hovertemplate=f"<b>%{{y}}</b>: %{{x:{value_format}}}{suffix}<extra></extra>"))
    fig.update_layout(style.base_layout(margin=dict(l=8, r=48, t=8, b=32), bargap=0.35,
                                        xaxis=style.value_axis(ticksuffix=suffix),
                                        yaxis=style.axis(automargin=True, autorange="reversed",
                                                         tickfont=dict(color=style.INK_2, size=12))))
    return fig
