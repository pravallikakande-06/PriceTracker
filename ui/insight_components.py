"""HTML builders for the price-intelligence features.

Pure string builders over `deal_analyzer` results: no Streamlit calls, no
database access. Every value shown comes from the analysis objects.
"""

from deal_analyzer import fmt_money, fmt_pct
from ui.components import badge_html, esc, icon

_BADGE_ICON = {"good": "check", "warn": "clock", "bad": "alert", "neutral": "info", "accent": "info"}


def _kv(label, value, extra_class=""):
    return (
        f'<div class="pt-kv {extra_class}"><div class="pt-kv-label">{esc(label)}</div>'
        f'<div class="pt-kv-value">{value}</div></div>'
    )


def _na(text="Not enough data"):
    return f'<div class="pt-na">{esc(text)}</div>'


def _panel(title, icon_name, body, tone="accent"):
    return (
        f'<div class="pt-intel pt-intel--{tone}"><div class="pt-intel-head">'
        f'<span class="pt-icon-chip pt-icon-chip--{tone} pt-icon-chip--sm">{icon(icon_name, 14)}</span>'
        f'<span>{esc(title)}</span></div>{body}</div>'
    )


# --------------------------------------------------
# DEAL SCORE + ADVISOR (top of each product card)
# --------------------------------------------------

def alert_level_badge(alert):
    if alert.level == 0:
        return ""

    icons = {1: "info", 2: "sparkles", 3: "target", 4: "check"}

    return badge_html(alert.tone, icons[alert.level], alert.label.title())


def deal_score_card_html(score):
    if score.score is None:
        body = f'<div class="pt-score-empty">{esc(score.explanation)}</div>'
        return _panel("Deal Score", "tag", body, "neutral")

    body = (
        '<div class="pt-score">'
        f'<div class="pt-ring pt-ring--{score.tone}" style="--p:{score.score}">'
        f'<span>{score.score}<small>/100</small></span></div>'
        f'<div><div class="pt-score-label pt-tone--{score.tone}">{esc(score.label)}</div>'
        f'<div class="pt-score-text">{esc(score.explanation)}</div></div></div>'
    )

    return _panel("Deal Score", "tag", body, score.tone)


def advisor_card_html(advice):
    if advice.verdict == "NO_DATA":
        body = (
            '<div class="pt-verdict pt-verdict--neutral">⚪ NOT ENOUGH DATA</div>'
            f'<div class="pt-score-text">{esc(advice.headline)}</div>'
        )
        return _panel("AI-assisted buying advice", "bot", body, "ai")

    dot = {"good": "🟢", "warn": "🟡", "bad": "🔴"}[advice.tone]
    marks = {1: ("✓", "pos"), -1: ("!", "neg"), 0: ("•", "neu")}
    reasons = "".join(
        f'<li class="pt-reason pt-reason--{marks[s.direction][1]}">'
        f'<b>{marks[s.direction][0]}</b>{esc(s.text)}</li>'
        for s in advice.signals
    )

    extra = ""
    if advice.expected_price is not None:
        wait = (f"Wait approximately {advice.wait_days} days." if advice.wait_days
                else "Wait for a lower price.")
        extra = (
            '<div class="pt-advice-grid">'
            + _kv("Expected price", esc(fmt_money(advice.expected_price)))
            + _kv("Expected saving", esc(fmt_money(advice.expected_saving)))
            + "</div>"
            f'<div class="pt-score-text">{esc(wait)}</div>'
        )

    body = (
        f'<div class="pt-verdict pt-verdict--{advice.tone}">{dot} {esc(advice.label.upper())}</div>'
        f'<div class="pt-score-text">{esc(advice.headline)}</div>'
        f'{extra}<ul class="pt-reasons">{reasons}</ul>'
        f'<div class="pt-confidence" title="Based on how much data exists and how many signals agree. '
        f'It is not a probability of being right.">Signal confidence '
        f'<b>{advice.confidence}%</b></div>'
    )

    return _panel("AI-assisted buying advice", "bot", body, "ai")


def intel_row_html(analysis):
    return (
        '<div class="pt-intel-row">'
        + deal_score_card_html(analysis.score)
        + advisor_card_html(analysis.advice)
        + "</div>"
    )


def score_breakdown_html(score):
    if score.score is None:
        return _na(score.explanation)

    rows = []
    for c in score.components:
        if c.fraction is None:
            points, weight = "n/a", "—"
        else:
            points, weight = f"{c.points:.1f}", str(c.weight)
        rows.append(
            f"<tr><td>{esc(c.label)}</td><td class='num'>{weight}</td>"
            f"<td class='num'>{points}</td><td class='pt-date'>{esc(c.detail)}</td></tr>"
        )

    return (
        '<div class="pt-table-wrap"><table class="pt-table" style="min-width:520px">'
        "<thead><tr><th>Component</th><th class='num'>Weight</th><th class='num'>Points</th>"
        f"<th>Detail</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        '<div class="pt-note">Score = points earned ÷ weight available × 100. Components '
        "that cannot be measured (for example no target set) are left out rather than guessed.</div>"
    )


# --------------------------------------------------
# SAVINGS, TARGET, INSIGHTS
# --------------------------------------------------

def savings_html(savings):
    if not savings.available:
        return _panel("Savings Analysis", "tag", _na("Needs at least 2 price checks."), "good")

    if savings.vs_avg_amount >= 0:
        verdict = (f"You are currently paying <b>{esc(fmt_pct(savings.vs_avg_pct))} less</b> "
                   "than the historical average.")
        potential = esc(fmt_money(savings.vs_avg_amount))
    else:
        verdict = (f"You are currently paying <b>{esc(fmt_pct(savings.vs_avg_pct))} more</b> "
                   "than the historical average.")
        potential = "None"

    grid = (
        '<div class="pt-kv-grid">'
        + _kv("Current price", esc(fmt_money(savings.current)))
        + _kv("Historical average", esc(fmt_money(savings.avg)))
        + _kv("Potential saving vs average", potential)
        + _kv("Below historical high", esc(fmt_money(savings.vs_high_amount))
              + f" <small>({esc(fmt_pct(savings.vs_high_pct))})</small>")
        + _kv("Historical low", esc(fmt_money(savings.low))
              + f" <small>(+{esc(fmt_money(savings.above_low))})</small>")
        + "</div>"
    )

    return _panel("Savings Analysis", "tag", f'<div class="pt-score-text">{verdict}</div>{grid}', "good")


def target_progress_html(savings):
    if savings.target is None:
        return _panel("Target Progress", "target", _na("No target price set."), "warn")

    if savings.target_gap is not None and savings.target_gap <= 0.005:
        remaining = "Target reached"
    else:
        remaining = esc(fmt_money(savings.target_gap))

    if savings.target_progress is not None:
        percent = savings.target_progress
        bar = (f'<div class="pt-meter pt-meter--warn"><span style="width:{percent:.0f}%"></span></div>'
               f'<div class="pt-note">Progress from the first tracked price to your target: '
               f'{percent:.0f}%</div>')
    else:
        bar = '<div class="pt-note">Progress cannot be measured because tracking started below the target.</div>'

    body = (
        '<div class="pt-kv-grid">'
        + _kv("Target", esc(fmt_money(savings.target)))
        + _kv("Current", esc(fmt_money(savings.current)))
        + _kv("Remaining", remaining)
        + "</div>" + bar
    )

    return _panel("Target Progress", "target", body, "warn")


def insights_html(insights):
    if not insights.available:
        return _panel("Price Insights", "chart", _na("Needs at least 2 price checks."), "accent")

    arrow = {"Decreasing": "↓", "Increasing": "↑", "Stable": "→"}.get(insights.trend, "")
    grid = (
        '<div class="pt-kv-grid">'
        + _kv("Lowest price", esc(fmt_money(insights.low)))
        + _kv("Highest price", esc(fmt_money(insights.high)))
        + _kv("Average price", esc(fmt_money(insights.avg)))
        + _kv("Current price", esc(fmt_money(insights.current)))
        + _kv("Price trend", f"{arrow} {esc(insights.trend)}")
        + _kv("Total drops / increases", f"{insights.total_drops} / {insights.total_increases}")
        + "</div>"
    )
    tips = "".join(f"<li>{esc(s)}</li>" for s in insights.sentences)
    insight = f'<ul class="pt-insight-list">{tips}</ul>' if tips else ""

    return _panel("Price Insights", "chart", grid + insight, "accent")


# --------------------------------------------------
# TIMING, VOLATILITY
# --------------------------------------------------

def best_time_html(bt):
    if not bt.available:
        return _panel("Best Time to Buy", "clock", _na(bt.message), "ai")

    body = (
        f'<div class="pt-score-text"><b>{esc(bt.recommendation)}</b></div>'
        '<div class="pt-kv-grid">'
        + _kv("Price drops recorded", str(bt.drops))
        + _kv("Drops usually come", esc(bt.typical_gap))
        + _kv("Since last drop", esc(bt.days_since_drop))
        + _kv("Typical discount", esc(bt.discount_range))
        + _kv("Typical saving", esc(bt.saving_range))
        + _kv("Confidence", esc(bt.confidence))
        + "</div>" + f'<div class="pt-note">{esc(bt.pattern)}</div>'
    )

    return _panel("Best Time to Buy", "clock", body, "ai")


def volatility_html(vol):
    if not vol.available:
        return _panel("Price Volatility", "chart", _na(vol.interpretation), "accent")

    month = (f"{vol.per_month:.1f} / month" if vol.per_month is not None
             else f"{vol.changes} in {vol.checks} checks")
    body = (
        f'<div class="pt-verdict pt-verdict--{vol.tone}" style="font-size:1.15rem">'
        f'{esc(vol.level)} <small>{vol.score} / 100</small></div>'
        '<div class="pt-kv-grid">'
        + _kv("Average change", esc(fmt_pct(vol.avg_change_pct)))
        + _kv("Price changes", esc(month))
        + "</div>" + f'<div class="pt-score-text">{esc(vol.interpretation)}</div>'
    )

    return _panel("Price Volatility", "chart", body, vol.tone)


# --------------------------------------------------
# TIMELINE, HEALTH, COMPARISON
# --------------------------------------------------

def timeline_html(entries):
    if not entries:
        return _na("No price records yet.")

    items = []
    for e in entries:
        if e.change == "drop":
            tag = badge_html("good", "down", f"Price drop {e.pct:.1f}%")
        elif e.change == "rise":
            tag = badge_html("bad", "up", f"Price rise {e.pct:.1f}%")
        else:
            tag = badge_html("neutral", "flat", "First record")
        items.append(
            f'<li class="pt-tl-item pt-tl-item--{e.change or "first"}">'
            f'<div class="pt-tl-date">{esc(e.when.strftime("%b %d, %H:%M"))}</div>'
            f'<div class="pt-tl-price">{esc(fmt_money(e.price))}</div>{tag}</li>'
        )

    return (
        f'<ul class="pt-timeline">{"".join(items)}</ul>'
        '<div class="pt-note">Shows recorded price changes; repeated checks at the same price are skipped.</div>'
    )


def health_html(health, ago_text):
    last = ago_text if health.last_checked else "—"
    body = (
        f'<div class="pt-verdict pt-verdict--{health.tone}" style="font-size:1.05rem">'
        f'{ {"good": "🟢", "warn": "🟡", "bad": "🔴", "neutral": "⚪"}[health.tone] } '
        f'{esc(health.label.upper())}</div>'
        f'<div class="pt-score-text">{esc(health.detail)}</div>'
        '<div class="pt-kv-grid">'
        + _kv("Last checked", esc(last))
        + _kv("Successful checks recorded", str(health.recorded_checks))
        + _kv("Last successful price",
              esc(fmt_money(health.last_price)) if health.last_price is not None else "—")
        + "</div>"
        '<div class="pt-note">Only successful checks are stored, so failed attempts are not counted.</div>'
    )

    return _panel("Tracking Health", "clock", body, health.tone if health.tone != "neutral" else "accent")


def comparison_html(comp):
    rows = []
    for r in comp.rows:
        diff = ('<span class="pt-badge pt-badge--good">Best</span>' if r.is_best
                else f'<span class="pt-pos">+{esc(fmt_money(r.difference))}</span>')
        label = esc(r.store) + (' <small class="pt-date">(tracked)</small>' if r.is_tracked else "")
        rows.append(
            f'<tr><td class="pt-prod-cell">{label}</td>'
            f'<td class="num"><b>{esc(fmt_money(r.price))}</b></td><td class="num">{diff}</td>'
            f'<td class="pt-date">{esc((r.checked_at or "tracked price")[:16])}</td></tr>'
        )

    best = comp.best
    summary = (
        f'<div class="pt-alert pt-alert--good" style="margin-top:.7rem"><span>{icon("check", 18)}</span>'
        f'<div><b>Best price: {esc(fmt_money(best.price))}</b> at {esc(best.store)}.'
    )
    if comp.max_saving > 0.005:
        summary += f" You save {esc(fmt_money(comp.max_saving))} compared with the highest listed price."
    summary += "</div></div>"

    return (
        '<div class="pt-table-wrap"><table class="pt-table" style="min-width:460px"><thead><tr>'
        "<th>Store</th><th class='num'>Price</th><th class='num'>Difference</th><th>Checked</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>{summary}"
    )


# --------------------------------------------------
# DASHBOARD SECTIONS
# --------------------------------------------------

def top_deals_html(items):
    """items: [(name, ProductAnalysis)] already sorted best-first."""

    if not items:
        return _na("Deal scores appear once a product has at least 3 price checks.")

    rows = []
    for rank, (name, a) in enumerate(items, start=1):
        rows.append(
            f'<div class="pt-rank-row"><span class="pt-rank">{rank}</span>'
            f'<div class="pt-rank-name" title="{esc(name)}">{esc(name)}</div>'
            f'<span class="pt-badge pt-badge--{a.score.tone}">{esc(a.score.label)}</span>'
            f'<div class="pt-rank-score">{a.score.score}<small>/100</small></div>'
            f'<div class="pt-rank-price">{esc(fmt_money(a.current))}</div></div>'
        )

    return f'<div class="pt-rank-list">{"".join(rows)}</div>'


def advisor_list_html(items):
    rows = []
    for name, a in items:
        adv = a.advice
        if adv.verdict == "NO_DATA":
            badge = badge_html("neutral", "info", "Not enough data")
            detail = "Needs more price checks"
        else:
            badge = badge_html(adv.tone, _BADGE_ICON[adv.tone], adv.label)
            detail = f"Signal confidence {adv.confidence}%"
            if adv.expected_price is not None:
                detail += f" · expected {fmt_money(adv.expected_price)}"
        rows.append(
            f'<div class="pt-rank-row"><div class="pt-rank-name" title="{esc(name)}">{esc(name)}</div>'
            f'{badge}<div class="pt-rank-detail">{esc(detail)}</div></div>'
        )

    return f'<div class="pt-rank-list">{"".join(rows)}</div>'


def wishlist_summary_html(count, reached, good, waiting):
    def cell(label, value, tone):
        return (f'<div class="pt-wl-cell pt-wl-cell--{tone}"><div class="pt-wl-num">{value}</div>'
                f'<div class="pt-wl-label">{esc(label)}</div></div>')

    return (
        '<div class="pt-wl">'
        + cell("In wishlist", count, "accent")
        + cell("Target reached", reached, "good")
        + cell("Good deals", good, "good")
        + cell("Waiting", waiting, "warn")
        + "</div>"
    )
