"""HTML builders for the dashboard.

Every string that can originate outside the app (product names, URLs,
email addresses, error text) goes through `esc()` before it reaches
`unsafe_allow_html`. Product names come from third-party web pages, so
they must never be trusted as markup.
"""

import html
import re

import streamlit as st

from ui.models import (
    NotificationStatus,
    ProductView,
    Summary,
    format_interval,
    format_money,
    format_pct,
    format_timestamp,
    time_ago,
)

# Lucide-style stroke icons (24x24 grid).
_ICONS = {
    "cart": '<circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/>',
    "package": '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
    "tag": '<path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "bell": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "down": '<polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/>',
    "up": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "flat": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="13 6 19 12 13 18"/>',
    "check": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>',
    "alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "plus": '<path d="M5 12h14"/><path d="M12 5v14"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "sparkles": '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
    "bot": '<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
}


def esc(value):
    """Escape text for HTML. Also stops `$...$` becoming LaTeX."""

    return html.escape(str(value), quote=True).replace("$", "&#36;")


def icon(name, size=18):
    """Return an inline SVG icon (decorative, hidden from screen readers)."""

    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{_ICONS[name]}</svg>'
    )


def render(markup):
    """Render an HTML snippet.

    Whitespace between tags is collapsed so Markdown never mistakes
    indentation or blank lines for a code block.
    """

    st.markdown(re.sub(r">\s+<", "><", markup.strip()), unsafe_allow_html=True)


# --------------------------------------------------
# PAGE CHROME
# --------------------------------------------------

def header_html(interval_seconds, notifications: NotificationStatus):
    notif_class = "pt-pill--good" if notifications.enabled else ""

    return f"""
    <div class="pt-header">
      <div class="pt-brand">
        <span class="pt-logo">{icon("tag", 24)}</span>
        <div>
          <div class="pt-title" role="heading" aria-level="1">Price Tracker</div>
          <div class="pt-tagline">Track prices. Catch the best deals.</div>
        </div>
      </div>
      <div class="pt-header-status">
        <span class="pt-pill pt-pill--accent"
              title="Run scheduler.py to check prices automatically.">
          <span class="pt-dot"></span>Scheduler: Configured
          ({esc(format_interval(interval_seconds))})
        </span>
        <span class="pt-pill {notif_class}"
              title="{esc(notifications.detail)}">
          <span class="pt-dot"></span>Notifications: {esc(notifications.headline)}
        </span>
      </div>
    </div>
    """


def section_heading(title, meta="", anchor=""):
    anchor_attr = f' id="{esc(anchor)}"' if anchor else ""
    meta_html = f'<span class="pt-section-meta">{esc(meta)}</span>' if meta else ""

    return (
        f'<div class="pt-section"{anchor_attr}>'
        f'<span class="pt-section-title" role="heading" aria-level="2">'
        f"{esc(title)}</span>{meta_html}</div>"
    )


def _metric(icon_name, label, value, sub, chip="", trend=""):
    return f"""
    <div class="pt-metric">
      <div class="pt-metric-top">
        <span class="pt-icon-chip {chip}">{icon(icon_name, 18)}</span>{esc(label)}
      </div>
      <div class="pt-metric-value">{esc(value)}</div>
      <div class="pt-metric-sub" title="{esc(sub)}">{esc(sub)}</div>
      {trend}
    </div>
    """


def metrics_html(summary: Summary):
    if summary.count == 0:
        cards = [
            _metric("package", "Tracked products", "0", "Nothing tracked yet"),
            _metric("tag", "Lowest price", "—", "Across tracked products"),
            _metric("chart", "Average price", "—", "Across tracked products"),
            _metric("target", "Targets reached", "0", "No targets set"),
        ]
        return f'<div class="pt-metrics">{"".join(cards)}</div>'

    trend = ""
    change = summary.average_change_pct

    if change is not None:
        if abs(change) < 0.005:
            trend = (
                f'<span class="pt-trend pt-trend--neutral">{icon("flat", 14)}'
                "No change overall</span>"
            )
        else:
            kind, arrow = ("good", "down") if change < 0 else ("bad", "up")
            word = "Down" if change < 0 else "Up"
            trend = (
                f'<span class="pt-trend pt-trend--{kind}">{icon(arrow, 14)}'
                f"{word} {format_pct(change)} overall</span>"
            )

    plural = "" if summary.count == 1 else "s"
    reached_chip = "pt-icon-chip--good" if summary.reached else ""

    cards = [
        _metric(
            "package", "Tracked products", str(summary.count),
            f"{summary.with_target} with a target price",
        ),
        _metric(
            "tag", "Lowest price", format_money(summary.lowest),
            summary.lowest_name or "",
        ),
        _metric(
            "chart", "Average price", format_money(summary.average),
            f"Across {summary.count} product{plural}", trend=trend,
        ),
        _metric(
            "target", "Targets reached", str(summary.reached),
            f"Of {summary.with_target} with a target"
            if summary.with_target else "No targets set",
            chip=reached_chip,
        ),
    ]

    return f'<div class="pt-metrics">{"".join(cards)}</div>'


def alert_html(kind, title, body=""):
    """kind: good | bad | warn | info."""

    icon_name = {"good": "check", "bad": "alert", "warn": "alert", "info": "info"}[kind]
    role = "alert" if kind in ("bad", "warn") else "status"
    body_html = f'<div class="pt-alert-body">{esc(body)}</div>' if body else ""

    return (
        f'<div class="pt-alert pt-alert--{kind}" role="{role}">{icon(icon_name, 20)}'
        f'<div><div class="pt-alert-title">{esc(title)}</div>{body_html}</div></div>'
    )


def empty_state_html(cta=True, body=None):
    body = body or (
        "Start tracking a product to monitor price changes and receive deal alerts."
    )
    cta_html = (
        f'<a class="pt-cta" href="#track-product">{icon("plus", 16)}'
        "Track your first product</a>"
        if cta else ""
    )

    return f"""
    <div class="pt-empty">
      <div class="pt-empty-icon">{icon("cart", 30)}</div>
      <div class="pt-empty-title">No products tracked yet</div>
      <div class="pt-empty-body">{esc(body)}</div>
      {cta_html}
    </div>
    """


def no_results_html(query):
    return f"""
    <div class="pt-empty">
      <div class="pt-empty-icon">{icon("search", 28)}</div>
      <div class="pt-empty-title">No matching products</div>
      <div class="pt-empty-body">Nothing in your list matches
      &ldquo;{esc(query)}&rdquo;. Check the spelling or clear the search.</div>
    </div>
    """


def footer_html():
    return f"""
    <div class="pt-footer">
      <b>{icon("cart", 16)}E-Commerce Price Tracker</b>
      <span>Python &bull; Streamlit &bull; SQLite &bull; BeautifulSoup &bull; Plotly</span>
    </div>
    """


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

def side_title(icon_name, title):
    return f'<div class="pt-side-title">{icon(icon_name, 18)}{esc(title)}</div>'


def notification_card_html(status: NotificationStatus, smtp_ok):
    if status.enabled:
        head = f'<span class="pt-badge pt-badge--good">{icon("check", 14)}Notifications enabled</span>'
    else:
        head = f'<span class="pt-badge pt-badge--neutral">{icon("bell", 14)}Notifications off</span>'

    warning = ""

    if status.enabled and not smtp_ok:
        warning = (
            '<div class="pt-side-muted" style="margin-top:.5rem">'
            "Email server login is missing. Add SMTP_USERNAME and "
            "SMTP_PASSWORD to .env, or alerts cannot be sent.</div>"
        )

    # Wrapped in a block element so Markdown does not auto-link the email.
    return (
        f'<div style="margin-bottom:.9rem">{head}<div class="pt-side-muted" style="margin-top:.5rem">'
        f"{esc(status.detail)}</div>{warning}</div>"
    )


def scheduler_card_html(interval_seconds, last_check, stale):
    last = (
        f"Last recorded check: <b>{esc(time_ago(last_check))}</b>."
        if last_check else "No checks recorded yet."
    )
    note = ""

    if stale:
        note = (
            '<div class="pt-side-muted" style="margin-top:.4rem">'
            "No check in a while. Is <code>scheduler.py</code> running?</div>"
        )

    return f"""
    <div class="pt-side-card">
      <span class="pt-badge pt-badge--accent">{icon("clock", 14)}Scheduler configured</span>
      <div style="margin-top:.55rem">Checks {esc(format_interval(interval_seconds))}
      while <code>scheduler.py</code> is running.</div>
      <div class="pt-side-muted" style="margin-top:.4rem">{last}</div>{note}
    </div>
    """


# --------------------------------------------------
# PRODUCT CARD
# --------------------------------------------------

def card_status(view: ProductView):
    """Return (spine, badge_class, badge_icon, badge_text) for a card."""

    target = view.target_status.kind
    change = view.change.kind

    if target == "reached":
        return "good", "good", "target", "Target hit"

    if target == "near":
        return "warn", "warn", "target", "Near target"

    if change == "drop":
        return "good", "good", "down", "Price dropped"

    if change == "rise":
        return "bad", "bad", "up", "Price increased"

    return "neutral", "neutral", "flat", "Tracking"


def card_head_html(view: ProductView):
    _, badge_class, badge_icon, badge_text = card_status(view)

    return f"""
    <div class="pt-card-head">
      <div style="min-width:0">
        <div class="pt-card-title">{esc(view.name)}</div>
        <div class="pt-url" title="{esc(view.url)}">{esc(view.url)}</div>
      </div>
      <span class="pt-badge pt-badge--{badge_class}">{icon(badge_icon, 14)}{badge_text}</span>
    </div>
    """


def card_stats_html(view: ProductView):
    at_low = view.current <= view.lowest + 0.005
    low_note = '<div class="pt-stat-note">Lowest so far</div>' if at_low else ""
    target = format_money(view.target) if view.target is not None else "Not set"

    return f"""
    <div class="pt-stats">
      <div>
        <div class="pt-stat-label">Current price</div>
        <div class="pt-stat-value pt-stat-value--hero">{format_money(view.current)}</div>
      </div>
      <div>
        <div class="pt-stat-label">Lowest</div>
        <div class="pt-stat-value">{format_money(view.lowest)}</div>{low_note}
      </div>
      <div>
        <div class="pt-stat-label">Target</div>
        <div class="pt-stat-value">{target}</div>
      </div>
    </div>
    """


def target_strip_html(view: ProductView):
    status = view.target_status

    if status.kind == "reached":
        return (
            f'<div class="pt-strip pt-strip--good">{icon("target", 20)}'
            "<div>Target price reached</div></div>"
        )

    if status.kind == "near":
        return (
            f'<div class="pt-strip pt-strip--warn">{icon("target", 20)}'
            f"<div>Only {format_money(status.gap)} above target</div></div>"
        )

    if status.kind == "above":
        return (
            f'<div class="pt-strip pt-strip--accent">{icon("target", 20)}'
            f"<div>{format_money(status.gap)} above target</div></div>"
        )

    return (
        f'<div class="pt-strip pt-strip--neutral">{icon("target", 20)}'
        "<div>No target price set</div></div>"
    )


def trend_strip_html(view: ProductView):
    change = view.change
    since = (
        f" since {format_timestamp(change.since)}" if change.since else ""
    )

    if change.kind == "drop":
        return (
            f'<div class="pt-strip pt-strip--good">{icon("down", 20)}<div>'
            f"Price dropped {format_pct(change.pct)}"
            f"<small>You saved {format_money(change.amount)}{esc(since)}</small>"
            "</div></div>"
        )

    if change.kind == "rise":
        return (
            f'<div class="pt-strip pt-strip--bad">{icon("up", 20)}<div>'
            f"Price increased {format_pct(change.pct)}"
            f"<small>{format_money(change.amount)} more{esc(since)}</small>"
            "</div></div>"
        )

    if change.kind == "flat":
        return (
            f'<div class="pt-strip pt-strip--neutral">{icon("flat", 20)}<div>'
            f"Price unchanged<small>Same price{esc(since)}</small></div></div>"
        )

    return (
        f'<div class="pt-strip pt-strip--neutral">{icon("flat", 20)}<div>'
        "Tracking started<small>Check again later to see price changes."
        "</small></div></div>"
    )


def checked_html(view: ProductView):
    return (
        f'<div class="pt-checked">{icon("clock", 15)}'
        f"Last checked {esc(time_ago(view.last_checked))}</div>"
    )


def chart_head_html(view: ProductView):
    count = len(view.history)
    meta = f"{count} check{'' if count == 1 else 's'}"

    return (
        '<div class="pt-chart-head"><span class="pt-chart-title">Price history</span>'
        f'<span class="pt-chart-meta">{meta}</span></div>'
    )


# --------------------------------------------------
# APP-LEVEL BUILDERS (used by app.py)
# --------------------------------------------------

def show_alert(kind, title, body=""):
    """Render a styled alert. kind: good | bad | warn | info."""

    render(alert_html(kind, title, body))


def app_header_html(interval_seconds, notifications: NotificationStatus):
    notif_class = "pt-pill--good" if notifications.enabled else ""

    return f"""
    <div class="pt-header pt-header--app">
      <div class="pt-brand">
        <span class="pt-logo">{icon("cart", 24)}</span>
        <div>
          <div class="pt-title" role="heading" aria-level="1">E-Commerce Price Intelligence</div>
          <div class="pt-tagline">Track prices • Predict trends • Buy smarter</div>
        </div>
      </div>
      <div class="pt-header-status">
        <span class="pt-pill pt-pill--accent"
              title="Run scheduler.py to check prices automatically.">
          <span class="pt-dot"></span>Scheduler: Configured
          ({esc(format_interval(interval_seconds))})
        </span>
        <span class="pt-pill {notif_class}" title="{esc(notifications.detail)}">
          <span class="pt-dot"></span>Notifications: {esc(notifications.headline)}
        </span>
      </div>
    </div>
    """


def kpi_grid_html(cards, cols=3):
    """cards: dicts with icon, label, value, sub and optional tone
    (accent | good | warn | ai | neutral)."""

    out = []

    for card in cards:
        tone = card.get("tone", "accent")
        out.append(
            f'<div class="pt-metric pt-metric--{tone}">'
            f'<div class="pt-metric-top"><span class="pt-icon-chip pt-icon-chip--{tone}">'
            f'{icon(card["icon"], 18)}</span>{esc(card["label"])}</div>'
            f'<div class="pt-metric-value">{esc(card["value"])}</div>'
            f'<div class="pt-metric-sub" title="{esc(card["sub"])}">{esc(card["sub"])}</div>'
            "</div>"
        )

    return f'<div class="pt-metrics pt-metrics--{cols}">{"".join(out)}</div>'


def badge_html(kind, icon_name, text):
    return (
        f'<span class="pt-badge pt-badge--{kind}">{icon(icon_name, 14)}{esc(text)}</span>'
    )


def _signed_money(value):
    sign = "\u2212" if value < 0 else ("+" if value > 0 else "")

    return f"{sign}\u20b9{abs(value):,.2f}"


def activity_table_html(rows):
    """Recent price activity table.

    `rows` is the unchanged `recent_activity` list built in app.py, so every
    number shown comes from the same calculation as before.
    """

    body = []

    for row in rows:
        diff = row["Change"]

        if diff < 0:
            tone, arrow, label = "good", "down", "Price Decreased"
        elif diff > 0:
            tone, arrow, label = "bad", "up", "Price Increased"
        else:
            tone, arrow, label = "neutral", "flat", "No Change"

        delta_class = {"good": "pt-neg", "bad": "pt-pos", "neutral": ""}[tone]

        body.append(
            "<tr>"
            f'<td class="pt-prod-cell" title="{esc(row["Product"])}">{esc(row["Product"])}</td>'
            f'<td class="num">\u20b9{row["Previous"]:,.2f}</td>'
            f'<td class="num"><b>\u20b9{row["Current"]:,.2f}</b></td>'
            f'<td class="num {delta_class}">{_signed_money(diff)}</td>'
            f'<td class="num {delta_class}">{row["% Change"]:+.2f}%</td>'
            f'<td>{badge_html(tone, arrow, label)}</td>'
            f'<td class="pt-date">{esc(row["Date"])}</td>'
            "</tr>"
        )

    head = "".join(
        f'<th class="{cls}">{name}</th>'
        for name, cls in [
            ("Product", ""), ("Previous", "num"), ("Current", "num"),
            ("Change", "num"), ("% Change", "num"), ("Status", ""), ("Date", ""),
        ]
    )

    return (
        '<div class="pt-table-wrap"><table class="pt-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def ai_banner_html():
    return f"""
    <div class="pt-ai-banner">
      <span class="pt-icon-chip pt-icon-chip--ai">{icon("bot", 20)}</span>
      <div>
        <div class="pt-ai-banner-title">AI Price Prediction</div>
        <div class="pt-ai-banner-sub">Statistical forecasts built from each
        product&rsquo;s recorded price history.</div>
      </div>
    </div>
    """


def _confidence_kind(confidence):
    return {"high": "good", "medium": "warn", "low": "neutral"}.get(
        str(confidence).strip().lower(), "accent"
    )


def prediction_cards_html(p):
    """Prediction cards from the stored prediction row `p` (a dict)."""

    prob = float(p["decrease_probability"]) * 100
    meter = max(0.0, min(100.0, prob))

    def card(label, value, extra=""):
        return (
            f'<div class="pt-ai-card"><div class="pt-ai-label">{esc(label)}</div>'
            f'<div class="pt-ai-value">{esc(value)}</div>{extra}</div>'
        )

    cards = [
        card("Predicted Range",
             f"\u20b9{p['predicted_price_low']:,.0f} \u2013 \u20b9{p['predicted_price_high']:,.0f}"),
        card("Drop Probability", f"{prob:.0f}%",
             f'<div class="pt-meter"><span style="width:{meter:.0f}%"></span></div>'),
        card("Expected Discount", f"{p['expected_discount_percent']}%"),
        card("Likely Window", f"Next {p['forecast_days']} days"),
    ]

    meta = (
        '<div class="pt-ai-meta">'
        f'{badge_html(_confidence_kind(p["confidence"]), "check", "Confidence: " + str(p["confidence"]))}'
        f'{badge_html("accent", "sparkles", "Status: " + str(p.get("status", "Unknown")))}'
        "</div>"
    )

    explain = (
        '<div class="pt-ai-explain"><b>Explanation</b>'
        f'<div>{esc(p.get("explanation", "Based on statistical analysis."))}</div></div>'
    )

    return f'<div class="pt-ai-grid">{"".join(cards)}</div>{meta}{explain}'


def product_head_html(name, url, badge_kind, badge_icon, badge_text):
    return f"""
    <div class="pt-card-head">
      <div style="min-width:0">
        <div class="pt-card-title">{esc(name)}</div>
        <div class="pt-url" title="{esc(url)}">{icon("link", 12)} {esc(url)}</div>
      </div>
      {badge_html(badge_kind, badge_icon, badge_text)}
    </div>
    """


def product_stats_html(current, lowest, avg, target):
    """Current price is the hero number. Strings match the old st.metric text."""

    at_low = current <= lowest + 0.005
    low_note = '<div class="pt-stat-note">Lowest so far</div>' if at_low else ""
    target_text = f"\u20b9{target:,.2f}" if target is not None else "Not set"

    return f"""
    <div class="pt-stats pt-stats--4">
      <div>
        <div class="pt-stat-label">Current price</div>
        <div class="pt-stat-value pt-stat-value--hero">\u20b9{current:,.2f}</div>
      </div>
      <div>
        <div class="pt-stat-label">Lowest price</div>
        <div class="pt-stat-value">\u20b9{lowest:,.2f}</div>{low_note}
      </div>
      <div>
        <div class="pt-stat-label">Average price</div>
        <div class="pt-stat-value">\u20b9{avg:,.2f}</div>
      </div>
      <div>
        <div class="pt-stat-label">Target price</div>
        <div class="pt-stat-value">{target_text}</div>
      </div>
    </div>
    """


def ai_status_html(text):
    return (
        '<div class="pt-ai-line">'
        f'<span class="pt-icon-chip pt-icon-chip--ai pt-icon-chip--sm">{icon("bot", 14)}</span>'
        f"<span>AI status</span><b>{esc(text)}</b></div>"
    )


def chart_title_html(title, meta=""):
    meta_html = f'<span class="pt-chart-meta">{esc(meta)}</span>' if meta else ""

    return (
        f'<div class="pt-chart-head"><span class="pt-chart-title">{esc(title)}</span>'
        f"{meta_html}</div>"
    )


def group_title_html(text):
    return f'<div class="pt-group-title">{esc(text)}</div>'


def panel_head_html(icon_name, title, sub=""):
    sub_html = f'<div class="pt-panel-sub">{esc(sub)}</div>' if sub else ""

    return (
        '<div class="pt-panel-head">'
        f'<span class="pt-icon-chip">{icon(icon_name, 18)}</span>'
        f'<div><div class="pt-panel-title">{esc(title)}</div>{sub_html}</div></div>'
    )
