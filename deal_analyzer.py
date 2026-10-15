"""Price intelligence: deal score, buy/wait advice, timing, volatility, savings.

Everything here is a pure function of data the app already stores (the
price history, the product row and the latest stored prediction). There is
no database access, no network access and no Streamlit import, so each
formula can be unit-tested on its own.

Honesty rules this module follows
---------------------------------
* No machine-learning model is involved. Every number comes from simple
  statistics over the recorded price checks, and the formulas are written
  out below.
* When there is not enough history, functions say so (they return a
  "not enough data" result) instead of inventing a value.
* "Confidence" for the advisor measures how much data there is and how
  much the individual signals agree. It is not a probability of being right.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

# --------------------------------------------------
# THRESHOLDS (documented in one place)
# --------------------------------------------------

MIN_OBS_SCORE = 3       # deal score needs at least this many checks
MIN_OBS_ADVICE = 5      # same minimum as prediction.py
MIN_OBS_VOLATILITY = 5
MIN_OBS_TIMING = 10     # same "full prediction" threshold as prediction.py
DROP_THRESHOLD_PCT = 1.5  # what prediction.py counts as a discount event
NEAR_TARGET_PCT = 5.0     # same as ui.models.NEAR_TARGET_PCT
RECENT_CHANGE_HOURS = 24  # "price changed" alerts look this far back
_EPS = 0.005


# --------------------------------------------------
# SMALL HELPERS
# --------------------------------------------------

def _clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def fmt_money(value):
    """₹ amount; whole rupees drop the '.00' (matches ui.models.format_money)."""

    if value is None:
        return "—"

    if abs(value - round(value)) < _EPS:
        return f"₹{round(value):,}"

    return f"₹{value:,.2f}"


def fmt_pct(value, digits=1):
    return f"{abs(value):.{digits}f}%"


def fmt_days(days):
    """Human wording for a span given in (fractional) days."""

    if days < 1:
        return "less than a day"

    if days < 2:
        return f"{round(days * 24)} hours"

    return f"{round(days)} days"


def fmt_span(low_days, high_days):
    """'3–5 days' style range ('up to 4 days' when it may be imminent)."""

    if low_days < 1 and high_days >= 1:
        return f"up to {fmt_days(high_days)}"

    if round(low_days) == round(high_days):
        return fmt_days(low_days)

    if low_days >= 2:
        return f"{round(low_days)}–{round(high_days)} days"

    return f"{fmt_days(low_days)} to {fmt_days(high_days)}"


def _percentile(sorted_values, q):
    """Linear-interpolated percentile (q in 0..1) of a sorted list."""

    if not sorted_values:
        raise ValueError("empty data")

    position = (len(sorted_values) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower

    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


Observation = tuple  # (datetime, float)


def to_observations(rows):
    """Turn history rows (mappings with checked_at, price) into a clean,
    time-ordered list of (datetime, price). Bad rows are skipped."""

    out = []

    for row in rows or []:
        row = dict(row)
        when = pd.to_datetime(row.get("checked_at"), errors="coerce")
        price = pd.to_numeric(row.get("price"), errors="coerce")

        if pd.isna(when) or pd.isna(price):
            continue

        out.append((when.to_pydatetime(), float(price)))

    out.sort(key=lambda item: item[0])  # stable: ties keep row order

    return out


def clean_target(value):
    """Target price as float, or None when unset / NaN / not positive."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if pd.isna(number) or number <= 0:
        return None

    return number


# --------------------------------------------------
# BASIC STATISTICS
# --------------------------------------------------

@dataclass(frozen=True)
class PriceStats:
    count: int
    current: float
    low: float
    high: float
    avg: float
    first: float
    drops: int       # number of recorded decreases
    rises: int       # number of recorded increases
    first_time: datetime
    last_time: datetime

    @property
    def pct_below_avg(self):
        """Positive when the current price is below the average."""

        return (self.avg - self.current) / self.avg * 100 if self.avg else 0.0

    @property
    def above_low(self):
        return self.current - self.low

    @property
    def span_days(self):
        return (self.last_time - self.first_time).total_seconds() / 86400


def compute_stats(obs, current=None):
    if not obs:
        return None

    prices = [price for _, price in obs]
    now_price = float(current) if current is not None else prices[-1]
    drops = sum(1 for a, b in zip(prices, prices[1:]) if b < a - _EPS)
    rises = sum(1 for a, b in zip(prices, prices[1:]) if b > a + _EPS)

    return PriceStats(
        count=len(prices),
        current=now_price,
        low=min(min(prices), now_price),
        high=max(max(prices), now_price),
        avg=sum(prices) / len(prices),
        first=prices[0],
        drops=drops,
        rises=rises,
        first_time=obs[0][0],
        last_time=obs[-1][0],
    )


def last_change(obs, current):
    """(previous_price, changed_at) for the last time the price differed
    from `current`, or None if it never changed. Same idea as
    ui.models.compute_price_change."""

    for index in range(len(obs) - 1, -1, -1):
        if abs(obs[index][1] - current) > _EPS:
            changed_at = obs[index + 1][0] if index + 1 < len(obs) else obs[index][0]
            return obs[index][1], changed_at

    return None


def price_context_sentence(stats):
    """One sentence comparing the price with its history (data-backed)."""

    if stats.count < 2:
        return "Not enough history to compare with past prices."

    pct = stats.pct_below_avg

    if abs(pct) < 0.05:
        first = "Current price is in line with the historical average"
    elif pct > 0:
        first = f"Current price is {fmt_pct(pct)} below the historical average"
    else:
        first = f"Current price is {fmt_pct(pct)} above the historical average"

    gap = stats.above_low

    if gap < _EPS:
        second = "and matches the historical low."
    elif stats.low and gap / stats.low * 100 <= 5:
        second = f"and only {fmt_money(gap)} above the historical low."
    else:
        second = f"and {fmt_money(gap)} above the historical low."

    return f"{first} {second}"


# --------------------------------------------------
# 1. DEAL SCORE
# --------------------------------------------------
#
#   Component                 Weight   What it measures
#   ------------------------  ------   ---------------------------------------
#   Position in price range     35     0 at the historical high, 1 at the low
#   Discount vs average         25     0 at 20% above average, 1 at 20% below
#   Target proximity            20     1 at/below target, 0 at 20% above it
#   Recent trend                10     last change: -5% => 1, +5% => 0
#   Prediction signal           10     1 - stored probability of a further drop
#
# Components that cannot be computed (no target set, no prediction yet, flat
# history) are left out and the score is rescaled over the remaining weights,
# so a missing input never lowers or raises the score by itself.

W_POSITION, W_AVERAGE, W_TARGET, W_TREND, W_PREDICTION = 35, 25, 20, 10, 10


@dataclass(frozen=True)
class ScoreComponent:
    key: str
    label: str
    weight: int
    fraction: float | None   # 0..1, None = not applicable
    detail: str

    @property
    def points(self):
        return None if self.fraction is None else self.weight * self.fraction


@dataclass(frozen=True)
class DealScore:
    score: int | None
    label: str
    tone: str
    explanation: str
    components: tuple = ()


def deal_band(score):
    """(label, tone) for a 0-100 score."""

    if score >= 90:
        return "Excellent Deal", "good"
    if score >= 75:
        return "Great Deal", "good"
    if score >= 50:
        return "Fair Price", "accent"
    if score >= 25:
        return "Expensive", "warn"
    return "Very Expensive", "bad"


def compute_deal_score(obs, stats, target=None, prediction=None):
    if stats is None or stats.count < MIN_OBS_SCORE:
        return DealScore(
            None, "Not enough data", "neutral",
            f"Collect at least {MIN_OBS_SCORE} price checks to calculate a deal score.",
        )

    current = stats.current
    components = []

    # 1. Position within the historical range.
    if stats.high - stats.low > _EPS:
        frac = _clamp((stats.high - current) / (stats.high - stats.low))
        detail = f"{fmt_money(current)} within {fmt_money(stats.low)}–{fmt_money(stats.high)}"
    else:
        frac, detail = None, "Price has never changed"
    components.append(ScoreComponent("position", "Position in price range", W_POSITION, frac, detail))

    # 2. Discount versus the historical average (+/-20% maps to 1..0).
    frac = _clamp(0.5 + (stats.pct_below_avg / 100) / 0.4)
    below = stats.pct_below_avg
    detail = (f"{fmt_pct(below)} {'below' if below >= 0 else 'above'} average "
              f"({fmt_money(stats.avg)})")
    components.append(ScoreComponent("average", "Discount vs average", W_AVERAGE, frac, detail))

    # 3. Target proximity.
    if target is not None:
        gap_pct = (current - target) / target * 100
        frac = 1.0 if gap_pct <= 0 else _clamp(1 - gap_pct / 20)
        detail = ("Target reached" if gap_pct <= 0
                  else f"{fmt_pct(gap_pct)} above target ({fmt_money(target)})")
    else:
        frac, detail = None, "No target price set"
    components.append(ScoreComponent("target", "Target proximity", W_TARGET, frac, detail))

    # 4. Recent trend (versus the last different price).
    change = last_change(obs, current)
    if change is None:
        frac, detail = 0.5, "No price change recorded"
    else:
        previous, _ = change
        pct = (current - previous) / previous * 100 if previous else 0.0
        frac = _clamp(0.5 - pct / 10)
        detail = f"{'Dropped' if pct < 0 else 'Rose'} {fmt_pct(pct)} on the last change"
    components.append(ScoreComponent("trend", "Recent trend", W_TREND, frac, detail))

    # 5. Prediction signal: a likely further drop makes buying now less attractive.
    probability = _prediction_probability(prediction)
    if probability is not None:
        frac = 1 - _clamp(probability)
        detail = f"{probability * 100:.0f}% stored chance of a further drop"
    else:
        frac, detail = None, "No prediction available yet"
    components.append(ScoreComponent("prediction", "Prediction signal", W_PREDICTION, frac, detail))

    applicable = [c for c in components if c.fraction is not None]
    total_weight = sum(c.weight for c in applicable)
    earned = sum(c.points for c in applicable)
    score = int(round(earned / total_weight * 100)) if total_weight else None

    if score is None:
        return DealScore(None, "Not enough data", "neutral", "Score could not be calculated.")

    label, tone = deal_band(score)

    return DealScore(
        score=score,
        label=label,
        tone=tone,
        explanation=price_context_sentence(stats),
        components=tuple(components),
    )


def _prediction_probability(prediction):
    if not prediction:
        return None

    try:
        value = float(prediction["decrease_probability"])
    except (KeyError, TypeError, ValueError):
        return None

    return None if pd.isna(value) else value


# --------------------------------------------------
# 2. BUY / WAIT / AVOID ADVISOR
# --------------------------------------------------

@dataclass(frozen=True)
class Signal:
    direction: int   # +1 favours buying now, -1 favours waiting, 0 information
    text: str


@dataclass(frozen=True)
class Advice:
    verdict: str                 # BUY | WAIT | AVOID | NO_DATA
    label: str
    tone: str
    headline: str
    confidence: int | None
    signals: tuple = ()
    expected_price: float | None = None
    expected_saving: float | None = None
    wait_days: int | None = None


def _expected_price(prediction, current):
    """Midpoint of the stored forecast range, only if it is below current."""

    if not prediction:
        return None

    try:
        low = float(prediction["predicted_price_low"])
        high = float(prediction["predicted_price_high"])
    except (KeyError, TypeError, ValueError):
        return None

    if pd.isna(low) or pd.isna(high):
        return None

    mid = (low + high) / 2

    return mid if mid < current * 0.999 else None


def collect_signals(stats, target, prediction):
    signals = []
    pct = stats.pct_below_avg

    if pct >= 5:
        signals.append(Signal(1, f"Price is {fmt_pct(pct, 0)} below the historical average"))
    elif pct <= -5:
        signals.append(Signal(-1, f"Price is {fmt_pct(pct, 0)} above the historical average"))
    else:
        signals.append(Signal(0, "Price is close to the historical average"))

    if stats.high - stats.low > _EPS:
        if stats.low and stats.above_low / stats.low * 100 <= 3:
            text = ("Current price is at the historical low" if stats.above_low < _EPS
                    else "Current price is close to the historical low")
            signals.append(Signal(1, text))
        elif (stats.high - stats.current) / stats.high * 100 <= 5:
            signals.append(Signal(-1, "Current price is close to the historical high"))

    if target is not None:
        gap = stats.current - target

        if gap <= _EPS:
            signals.append(Signal(1, "Target price has been reached"))
        elif gap / target * 100 <= NEAR_TARGET_PCT:
            signals.append(Signal(0, f"Only {fmt_money(gap)} above your target price"))
        else:
            signals.append(Signal(-1, f"{fmt_money(gap)} above your target price"))

    probability = _prediction_probability(prediction)

    if probability is not None:
        expected = _expected_price(prediction, stats.current)
        saving_pct = (stats.current - expected) / stats.current * 100 if expected else 0.0

        if probability < 0.4:
            signals.append(Signal(1, f"Chance of a further drop is low ({probability * 100:.0f}%)"))
        elif probability >= 0.5 and saving_pct >= 2:
            signals.append(Signal(
                -1,
                f"Forecast shows a {probability * 100:.0f}% chance of a drop "
                f"of about {fmt_pct(saving_pct, 1)}",
            ))

    return signals


def compute_advice(obs, stats, score, target=None, prediction=None):
    """Statistical buying recommendation (rule-based, not machine learning)."""

    if stats is None or stats.count < MIN_OBS_ADVICE or score.score is None:
        return Advice(
            "NO_DATA", "Not enough data", "neutral",
            "Collect more price observations to generate a reliable recommendation.",
            None,
        )

    current = stats.current
    signals = collect_signals(stats, target, prediction)
    probability = _prediction_probability(prediction)
    expected = _expected_price(prediction, current)
    saving = (current - expected) if expected else None
    saving_pct = saving / current * 100 if saving else 0.0
    likely_drop = probability is not None and probability >= 0.5 and saving_pct >= 2
    reached = target is not None and current <= target + _EPS

    if reached and not likely_drop and score.score >= 50:
        verdict = "BUY"
        headline = "Your target price has been reached and no major drop is expected."
    elif likely_drop:
        verdict = "WAIT"
        headline = "A further price drop looks likely based on past price behaviour."
    elif score.score >= 75:
        verdict = "BUY"
        headline = "This is a strong price compared with its history."
    elif score.score < 25:
        verdict = "AVOID"
        headline = "This price is very high compared with its history."
    elif score.score >= 50:
        verdict = "BUY"
        headline = "A fair price, and no major drop is expected."
    else:
        verdict = "WAIT"
        headline = "The price is above its usual level; waiting may get a better one."

    label, tone = {
        "BUY": ("Buy now", "good"),
        "WAIT": ("Wait", "warn"),
        "AVOID": ("Avoid", "bad"),
    }[verdict]

    decisive = [s for s in signals if s.direction != 0]
    supporting = [s for s in decisive if (s.direction > 0) == (verdict == "BUY")]
    agreement = len(supporting) / len(decisive) if decisive else 0.5
    data_part = min(stats.count, 30) / 30
    confidence = int(round(50 * data_part + 50 * agreement))

    wait_days = None
    if verdict == "WAIT" and likely_drop:
        try:
            wait_days = int(prediction["forecast_days"])
        except (KeyError, TypeError, ValueError):
            wait_days = None

    return Advice(
        verdict=verdict, label=label, tone=tone, headline=headline,
        confidence=confidence, signals=tuple(signals),
        expected_price=expected if verdict == "WAIT" else None,
        expected_saving=saving if verdict == "WAIT" else None,
        wait_days=wait_days,
    )


# --------------------------------------------------
# 3. BEST TIME TO BUY
# --------------------------------------------------

@dataclass(frozen=True)
class BestTime:
    available: bool
    message: str
    drops: int = 0
    typical_gap: str = ""
    days_since_drop: str = ""
    recommendation: str = ""
    discount_range: str = ""
    saving_range: str = ""
    confidence: str = ""
    pattern: str = ""


def drop_events(obs):
    """[(time, drop_pct)] for each fall of at least DROP_THRESHOLD_PCT
    (same rule as prediction.py)."""

    events = []

    for (_, before), (when, after) in zip(obs, obs[1:]):
        if before > 0 and after < before:
            pct = (before - after) / before * 100
            if pct >= DROP_THRESHOLD_PCT:
                events.append((when, pct))

    return events


def compute_best_time(obs, stats, now=None):
    now = now or datetime.now()

    if stats is None or stats.count < MIN_OBS_TIMING:
        return BestTime(
            False,
            "Not enough historical observations to estimate the best buying period "
            f"(need {MIN_OBS_TIMING}, have {0 if stats is None else stats.count}).",
        )

    events = drop_events(obs)

    if len(events) < 2:
        return BestTime(
            False,
            f"Only {len(events)} price drop recorded so far, which is not enough "
            "to estimate a buying period.",
            drops=len(events),
        )

    gaps = sorted(
        (b[0] - a[0]).total_seconds() / 86400 for a, b in zip(events, events[1:])
    )
    pcts = sorted(pct for _, pct in events)

    if len(gaps) >= 3:
        gap_lo, gap_hi = _percentile(gaps, 0.25), _percentile(gaps, 0.75)
        pct_lo, pct_hi = _percentile(pcts, 0.25), _percentile(pcts, 0.75)
    else:
        gap_lo, gap_hi = gaps[0], gaps[-1]
        pct_lo, pct_hi = pcts[0], pcts[-1]

    median_gap = _percentile(gaps, 0.5)
    since = max((now - events[-1][0]).total_seconds() / 86400, 0.0)
    count = len(events)
    confidence = "Low" if count < 4 else ("Medium" if count < 7 else "High")

    near_low = stats.low and stats.above_low / stats.low * 100 <= 2

    if near_low:
        recommendation = ("The current price is already near its historical low. "
                          "Typical drop timing is shown for reference.")
    elif since > gap_hi:
        recommendation = ("A drop is overdue compared with the usual pattern. "
                          "Keep watching; it is not guaranteed.")
    elif since >= gap_lo:
        remaining = max(gap_hi - since, 0)
        recommendation = (f"A drop is within its usual window now "
                          f"(typically within {fmt_days(remaining)} more).")
    else:
        span = fmt_span(gap_lo - since, gap_hi - since)
        recommendation = f"Wait {span}." if span.startswith("up to") else f"Wait about {span}."

    low_saving = stats.current * pct_lo / 100
    high_saving = stats.current * pct_hi / 100

    return BestTime(
        available=True,
        message="",
        drops=count,
        typical_gap=f"every {fmt_span(gap_lo, gap_hi)}" if round(gap_lo) != round(gap_hi)
        else f"about every {fmt_days(median_gap)}",
        days_since_drop=fmt_days(since),
        recommendation=recommendation,
        discount_range=(f"{pct_lo:.1f}–{pct_hi:.1f}%" if abs(pct_lo - pct_hi) >= 0.05
                        else f"about {pct_lo:.1f}%"),
        saving_range=(f"{fmt_money(low_saving)}–{fmt_money(high_saving)}"
                      if abs(high_saving - low_saving) >= 1 else f"about {fmt_money(low_saving)}"),
        confidence=confidence,
        pattern=(f"Based on {count} recorded price drops of at least "
                 f"{DROP_THRESHOLD_PCT:g}% over {fmt_days(stats.span_days)}. "
                 "Past patterns do not guarantee future prices."),
    )


# --------------------------------------------------
# 4. VOLATILITY
# --------------------------------------------------
#
#   score = 60% * min(average |change| / 10%, 1)
#         + 40% * min(share of checks that changed / 50%, 1)       (x 100)
#   LOW < 30 <= MEDIUM < 60 <= HIGH

@dataclass(frozen=True)
class Volatility:
    available: bool
    level: str
    tone: str
    score: int | None
    avg_change_pct: float | None
    changes: int
    checks: int
    per_month: float | None
    interpretation: str


def compute_volatility(obs):
    if len(obs) < MIN_OBS_VOLATILITY:
        return Volatility(
            False, "Not enough data", "neutral", None, None, 0, len(obs), None,
            f"Needs at least {MIN_OBS_VOLATILITY} price checks to measure price behaviour.",
        )

    pairs = list(zip(obs, obs[1:]))
    moves = [
        abs(b[1] - a[1]) / a[1] * 100
        for a, b in pairs
        if a[1] > 0 and abs(b[1] - a[1]) > _EPS
    ]
    changes = len(moves)
    share = changes / len(pairs)
    avg_move = sum(moves) / changes if changes else 0.0
    score = int(round(100 * (0.6 * min(avg_move / 10, 1) + 0.4 * min(share / 0.5, 1))))

    level, tone = (("LOW", "good") if score < 30
                   else ("MEDIUM", "warn") if score < 60 else ("HIGH", "bad"))

    span_days = (obs[-1][0] - obs[0][0]).total_seconds() / 86400
    per_month = changes / span_days * 30 if span_days >= 7 else None

    if changes == 0:
        text = "The price has not changed across the recorded checks."
    elif level == "HIGH":
        text = ("This product changes price often and by noticeable amounts. "
                "A lower price may appear, but that is not guaranteed.")
    elif level == "MEDIUM":
        text = "This product changes price now and then, by moderate amounts."
    else:
        text = "This product's price is fairly steady, so waiting is less likely to help."

    return Volatility(True, level, tone, score, avg_move, changes, len(obs), per_month, text)


# --------------------------------------------------
# 5. SAVINGS ANALYSIS
# --------------------------------------------------

@dataclass(frozen=True)
class Savings:
    available: bool
    current: float
    avg: float | None = None
    high: float | None = None
    low: float | None = None
    target: float | None = None
    vs_avg_amount: float | None = None   # avg - current (positive = saving)
    vs_avg_pct: float | None = None
    vs_high_amount: float | None = None
    vs_high_pct: float | None = None
    above_low: float | None = None
    target_gap: float | None = None      # current - target
    target_progress: float | None = None  # 0..100


def compute_savings(stats, target=None):
    if stats is None:
        return Savings(False, 0.0)

    current = stats.current

    if stats.count < 2:
        return Savings(False, current, target=target)

    progress = None
    gap = None

    if target is not None:
        gap = current - target

        if gap <= _EPS:
            progress = 100.0
        elif stats.first > target:
            progress = _clamp((stats.first - current) / (stats.first - target), 0, 1) * 100

    return Savings(
        available=True, current=current, avg=stats.avg, high=stats.high,
        low=stats.low, target=target,
        vs_avg_amount=stats.avg - current,
        vs_avg_pct=stats.pct_below_avg,
        vs_high_amount=stats.high - current,
        vs_high_pct=(stats.high - current) / stats.high * 100 if stats.high else 0.0,
        above_low=stats.above_low,
        target_gap=gap,
        target_progress=progress,
    )


# --------------------------------------------------
# 6. INSIGHTS, 10. TIMELINE
# --------------------------------------------------

@dataclass(frozen=True)
class Insights:
    available: bool
    low: float = 0.0
    high: float = 0.0
    avg: float = 0.0
    current: float = 0.0
    trend: str = "Not enough data"
    total_drops: int = 0
    total_increases: int = 0
    sentences: tuple = ()


def compute_insights(obs, stats):
    if stats is None or stats.count < 2:
        return Insights(False)

    prices = [p for _, p in obs]
    trend = "Not enough data"

    if len(prices) >= 3:
        prior = prices[max(0, len(prices) - 6):-1]
        baseline = sum(prior) / len(prior)
        pct = (stats.current - baseline) / baseline * 100 if baseline else 0.0
        trend = "Decreasing" if pct <= -1 else ("Increasing" if pct >= 1 else "Stable")

    sentences = []
    context = price_context_sentence(stats)
    if stats.count >= MIN_OBS_SCORE:
        sentences.append(context)

    if stats.high - stats.low > _EPS:
        if stats.above_low < _EPS:
            sentences.append("This is the lowest price recorded so far.")
        elif stats.high - stats.current < _EPS:
            sentences.append("This is the highest price recorded so far.")

    if trend == "Decreasing":
        sentences.append("The price has been trending down over the last few checks.")
    elif trend == "Increasing":
        sentences.append("The price has been trending up over the last few checks.")

    return Insights(
        True, stats.low, stats.high, stats.avg, stats.current, trend,
        stats.drops, stats.rises, tuple(sentences),
    )


@dataclass(frozen=True)
class TimelineEntry:
    when: datetime
    price: float
    change: str | None   # "drop" | "rise" | None (first record)
    pct: float = 0.0


def compute_timeline(obs, limit=8):
    """Newest-first list of recorded price *changes* (plus the first record).
    Repeated checks at an unchanged price are skipped to keep it compact."""

    entries = []
    previous = None

    for when, price in obs:
        if previous is None:
            entries.append(TimelineEntry(when, price, None))
        elif abs(price - previous) > _EPS:
            pct = abs(price - previous) / previous * 100 if previous else 0.0
            entries.append(TimelineEntry(when, price, "drop" if price < previous else "rise", pct))
        previous = price

    return list(reversed(entries))[:limit]


# --------------------------------------------------
# 7. ALERT LEVELS
# --------------------------------------------------

@dataclass(frozen=True)
class AlertLevel:
    level: int          # 0 none, 1 changed, 2 good deal, 3 target near, 4 reached
    key: str
    label: str
    tone: str


_NO_ALERT = AlertLevel(0, "none", "", "neutral")


def compute_alert_level(obs, stats, score, target=None, now=None):
    """Highest applicable level. Level 1 needs a change in the last 24 hours."""

    if stats is None:
        return _NO_ALERT

    now = now or datetime.now()
    current = stats.current

    if target is not None:
        gap = current - target

        if gap <= _EPS:
            return AlertLevel(4, "target_reached", "TARGET REACHED", "good")

        if gap / target * 100 <= NEAR_TARGET_PCT:
            return AlertLevel(3, "target_near", "TARGET NEAR", "warn")

    if score.score is not None and score.score >= 75:
        return AlertLevel(2, "good_deal", "GOOD DEAL", "good")

    change = last_change(obs, current)

    if change and now - change[1] <= timedelta(hours=RECENT_CHANGE_HOURS):
        return AlertLevel(1, "price_changed", "PRICE CHANGED", "accent")

    return _NO_ALERT


# --------------------------------------------------
# 9. TRACKING HEALTH
# --------------------------------------------------
#
# Only successful checks are stored (failures are not written anywhere), so
# this reports what the data can support: when the last successful check was,
# how many have been recorded, and whether that is recent compared with the
# scheduler interval. A red state is shown only when a manual check made from
# this app has just failed.

@dataclass(frozen=True)
class Health:
    state: str       # active | issue | unavailable | unchecked
    label: str
    tone: str
    detail: str
    last_checked: datetime | None
    recorded_checks: int
    last_price: float | None


def compute_health(obs, interval_seconds, now=None, manual_check_failed=False):
    now = now or datetime.now()
    count = len(obs)
    last_time = obs[-1][0] if obs else None
    last_price = obs[-1][1] if obs else None

    def build(state, label, tone, detail):
        return Health(state, label, tone, detail, last_time, count, last_price)

    if manual_check_failed:
        return build(
            "unavailable", "Scraping unavailable", "bad",
            "The latest manual check could not read the product page. "
            "The last successful price is still shown.",
        )

    if count <= 1:
        return build(
            "unchecked", "Not checked yet", "neutral",
            "No re-check has been recorded since the product was added.",
        )

    age = now - last_time

    if age <= timedelta(seconds=2 * interval_seconds):
        return build("active", "Tracking active", "good",
                     "The last successful check is within the expected interval.")

    return build(
        "issue", "Temporary issue", "warn",
        "No successful check recently. The scheduler may not be running, "
        "or the website may be blocking requests.",
    )


# --------------------------------------------------
# BUNDLE
# --------------------------------------------------

@dataclass(frozen=True)
class ProductAnalysis:
    name: str
    current: float
    target: float | None
    stats: PriceStats | None
    score: DealScore
    advice: Advice
    best_time: BestTime
    volatility: Volatility
    savings: Savings
    insights: Insights
    timeline: list = field(default_factory=list)
    health: Health | None = None
    alert: AlertLevel = _NO_ALERT
    prediction: dict | None = None
    previous_price: float | None = None


def analyze_product(name, current, target, history_rows, prediction,
                    interval_seconds, now=None, manual_check_failed=False):
    """Run every analysis for one product. `prediction` is the latest stored
    prediction row (dict-like) or None."""

    now = now or datetime.now()
    current = float(current)
    target = clean_target(target)
    prediction = dict(prediction) if prediction else None

    obs = to_observations(history_rows)
    stats = compute_stats(obs, current) if obs else None

    score = compute_deal_score(obs, stats, target, prediction)
    advice = compute_advice(obs, stats, score, target, prediction)
    change = last_change(obs, current) if obs else None

    return ProductAnalysis(
        name=name,
        current=current,
        target=target,
        stats=stats,
        score=score,
        advice=advice,
        best_time=compute_best_time(obs, stats, now),
        volatility=compute_volatility(obs),
        savings=compute_savings(stats, target),
        insights=compute_insights(obs, stats),
        timeline=compute_timeline(obs),
        health=compute_health(obs, interval_seconds, now, manual_check_failed),
        alert=compute_alert_level(obs, stats, score, target, now),
        prediction=prediction,
        previous_price=change[0] if change else None,
    )
