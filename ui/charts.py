"""Plotly price-history chart."""

import plotly.graph_objects as go

from ui.models import format_money
from ui.styles import ACCENT, FONT, GOOD, GRID, INK, LINE, MUTED

_HOUR_MS = 3_600_000
_DAY_MS = 24 * _HOUR_MS


def build_price_chart(history, current, lowest, target):
    """Return a price-history figure for one product.

    Straight segments (not a smoothed spline) are used on purpose: a
    spline would draw prices the product never actually had.
    """

    times = history["checked_at"]
    prices = history["price"]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=times,
            y=prices,
            mode="lines+markers",
            name="Price",
            line=dict(color=ACCENT, width=2.5),
            marker=dict(size=7, color="#FFFFFF", line=dict(color=ACCENT, width=2)),
            fill="tozeroy",
            fillcolor="rgba(67,56,202,0.07)",
            hovertemplate=(
                "<b>₹%{y:,.2f}</b><br>"
                "%{x|%d %b %Y, %I:%M %p}<extra></extra>"
            ),
        )
    )

    if len(prices):
        last_index = len(prices) - 1
        low_index = max(i for i, p in enumerate(prices) if p == prices.min())
        low_is_now = low_index == last_index

        # Lowest recorded price (most recent occurrence).
        if not low_is_now:
            fig.add_trace(
                go.Scatter(
                    x=[times.iloc[low_index]],
                    y=[prices.iloc[low_index]],
                    mode="markers+text",
                    text=["Lowest"],
                    textposition="bottom center",
                    textfont=dict(color=GOOD, size=11),
                    marker=dict(size=12, symbol="diamond", color=GOOD),
                    hovertemplate="<b>Lowest ₹%{y:,.2f}</b><extra></extra>",
                )
            )

        # Current price, highlighted.
        fig.add_trace(
            go.Scatter(
                x=[times.iloc[last_index]],
                y=[prices.iloc[last_index]],
                mode="markers+text",
                text=["Now · lowest" if low_is_now else "Now"],
                textposition="top left",
                textfont=dict(color=INK, size=11),
                marker=dict(
                    size=12,
                    color=GOOD if low_is_now else ACCENT,
                    symbol="diamond" if low_is_now else "circle",
                    line=dict(color="#FFFFFF", width=2),
                ),
                hovertemplate=(
                    f"<b>Now {format_money(current)}</b><extra></extra>"
                ),
            )
        )

    if target is not None:
        fig.add_hline(
            y=target,
            line=dict(color=GOOD, width=1.5, dash="dash"),
            annotation_text=f"Target {format_money(target)}",
            annotation_position="top left",
            annotation_font=dict(color=GOOD, size=11),
        )

    # Pad the y-range so labels never touch the frame, and include the
    # target line even when it is far from the recorded prices.
    values = list(prices) + ([target] if target is not None else [])
    low, high = min(values), max(values)
    span = high - low

    # Never zoom in tighter than 1% of the price, otherwise a target a
    # rupee away from the price produces a y-axis of meaningless decimals.
    pad = max(span * 0.2, high * 0.01, 1)

    whole = all(abs(v - round(v)) < 0.005 for v in values)
    tick_format = ",.0f" if whole or span >= 10 else ",.2f"

    xaxis = dict(
        showgrid=False,
        showline=True,
        linecolor=LINE,
        fixedrange=True,
        tickformatstops=[
            dict(dtickrange=[None, _HOUR_MS * 6], value="%H:%M<br>%d %b"),
            dict(dtickrange=[_HOUR_MS * 6, _DAY_MS * 2], value="%d %b<br>%H:%M"),
            dict(dtickrange=[_DAY_MS * 2, None], value="%d %b"),
        ],
    )

    # Leave a little room on the right so the "Now" marker is not clipped.
    if len(times) >= 2:
        extra = (times.iloc[-1] - times.iloc[0]) * 0.06
        xaxis["range"] = [times.iloc[0] - extra, times.iloc[-1] + extra]

    fig.update_layout(
        height=300,
        margin=dict(l=4, r=8, t=16, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=MUTED),
        showlegend=False,
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor=LINE,
            font=dict(family=FONT, size=13, color=INK),
        ),
        xaxis=xaxis,
        yaxis=dict(
            range=[low - pad, high + pad],
            tickprefix="₹",
            tickformat=tick_format,
            gridcolor=GRID,
            zeroline=False,
            fixedrange=True,
            automargin=True,
        ),
    )

    return fig

def style_price_figure(fig, history, current, lowest, target):
    """Apply the app theme to the figure app.py already built.

    Visual only: existing traces (price history, forecast low/high) and the
    forecast shading are kept and restyled; the current-price marker,
    lowest-price marker and target line are drawn from values app.py has
    already computed. Nothing here changes a price or a prediction.
    """

    times = history["checked_at"]
    prices = history["price"]

    # Price line (first trace made by px.line).
    fig.update_traces(
        selector=dict(mode="lines+markers"),
        name="Price",
        line=dict(color=ACCENT, width=2.5),
        marker=dict(size=7, color="#FFFFFF", line=dict(color=ACCENT, width=2)),
        hovertemplate="<b>\u20b9%{y:,.2f}</b><extra></extra>",
    )
    fig.update_traces(
        selector=dict(name="Forecast (Low)"),
        line=dict(dash="dash", color=GOOD, width=2),
        hovertemplate="Forecast low <b>\u20b9%{y:,.0f}</b><extra></extra>",
    )
    fig.update_traces(
        selector=dict(name="Forecast (High)"),
        line=dict(dash="dash", color="#E0861A", width=2),
        hovertemplate="Forecast high <b>\u20b9%{y:,.0f}</b><extra></extra>",
    )
    fig.update_shapes(
        selector=dict(type="rect"), fillcolor="rgba(67,56,202,0.06)", line_width=0
    )

    if len(prices):
        low_index = max(i for i, p in enumerate(prices) if p == prices.min())
        last_index = len(prices) - 1

        if low_index != last_index:
            fig.add_scatter(
                x=[times.iloc[low_index]], y=[prices.iloc[low_index]],
                mode="markers+text", text=["Lowest"], textposition="bottom center",
                textfont=dict(color=GOOD, size=11),
                marker=dict(size=11, symbol="diamond", color=GOOD),
                showlegend=False, hoverinfo="skip",
            )

        fig.add_scatter(
            x=[times.iloc[last_index]], y=[prices.iloc[last_index]],
            mode="markers+text", text=["Now"], textposition="top left",
            textfont=dict(color=INK, size=11),
            marker=dict(size=13, color=ACCENT, line=dict(color="#FFFFFF", width=2)),
            showlegend=False, hoverinfo="skip",
        )

    if target is not None:
        fig.add_hline(
            y=target,
            line=dict(color=GOOD, width=1.5, dash="dash"),
            annotation_text=f"Target {format_money(target)}",
            annotation_position="top left",
            annotation_font=dict(color=GOOD, size=11),
        )

    # Pad the y-range and make sure the target line is always in view.
    values = [float(v) for trace in fig.data if trace.y is not None for v in trace.y]
    if target is not None:
        values.append(float(target))
    if not values:
        return fig
    low, high = min(values), max(values)
    pad = max((high - low) * 0.15, high * 0.01, 1)
    tick_format = ",.0f" if (high - low) >= 10 else ",.2f"

    fig.update_layout(
        height=340,
        margin=dict(l=4, r=8, t=28, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=12, color=MUTED),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=LINE,
                        font=dict(family=FONT, size=13, color=INK)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    title_text=""),
        xaxis=dict(title_text="", showgrid=False, showline=True, linecolor=LINE),
        yaxis=dict(title_text="Price (\u20b9)", range=[low - pad, high + pad],
                   tickprefix="\u20b9", tickformat=tick_format,
                   gridcolor=GRID, zeroline=False, automargin=True),
    )

    return fig
