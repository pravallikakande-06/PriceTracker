"""Tests for the price-intelligence logic (pure functions, no database)."""

from datetime import datetime, timedelta

import pytest

from deal_analyzer import (
    analyze_product,
    clean_target,
    compute_advice,
    compute_alert_level,
    compute_best_time,
    compute_deal_score,
    compute_health,
    compute_insights,
    compute_savings,
    compute_stats,
    compute_timeline,
    compute_volatility,
    deal_band,
    to_observations,
)

START = datetime(2026, 9, 1, 12, 0, 0)
NOW = datetime(2026, 10, 4, 12, 0, 0)


def rows(prices, step_hours=24, start=START):
    return [
        {"checked_at": (start + timedelta(hours=step_hours * i)).isoformat(sep=" "), "price": p}
        for i, p in enumerate(prices)
    ]


def build(prices, target=None, prediction=None, step_hours=24):
    obs = to_observations(rows(prices, step_hours))
    stats = compute_stats(obs)
    score = compute_deal_score(obs, stats, target, prediction)
    return obs, stats, score


# ---------- parsing / empty data ----------

def test_to_observations_skips_bad_rows_and_sorts():
    data = [
        {"checked_at": "2026-09-02 10:00:00", "price": "200"},
        {"checked_at": "not a date", "price": 150},
        {"checked_at": "2026-09-01 10:00:00", "price": 100},
        {"checked_at": "2026-09-03 10:00:00", "price": None},
    ]
    obs = to_observations(data)
    assert [p for _, p in obs] == [100.0, 200.0]


def test_clean_target_handles_missing_values():
    assert clean_target(None) is None
    assert clean_target(float("nan")) is None
    assert clean_target(0) is None
    assert clean_target("45000") == 45000.0


def test_empty_history_never_crashes_and_shows_not_enough_data():
    a = analyze_product("Thing", 1000, None, [], None, 3600, now=NOW)
    assert a.score.score is None
    assert a.advice.verdict == "NO_DATA"
    assert not a.best_time.available
    assert not a.volatility.available
    assert not a.savings.available
    assert not a.insights.available
    assert a.health.state == "unchecked"
    assert a.alert.level == 0


# ---------- deal score ----------

def test_deal_score_needs_three_checks():
    _, _, score = build([100, 90])
    assert score.score is None
    assert score.label == "Not enough data"


def test_deal_band_boundaries():
    assert deal_band(100)[0] == "Excellent Deal"
    assert deal_band(90)[0] == "Excellent Deal"
    assert deal_band(89)[0] == "Great Deal"
    assert deal_band(75)[0] == "Great Deal"
    assert deal_band(74)[0] == "Fair Price"
    assert deal_band(50)[0] == "Fair Price"
    assert deal_band(49)[0] == "Expensive"
    assert deal_band(25)[0] == "Expensive"
    assert deal_band(24)[0] == "Very Expensive"
    assert deal_band(0)[0] == "Very Expensive"


def test_price_at_historic_low_with_target_reached_is_excellent():
    _, _, score = build([120, 110, 100, 90], target=95)
    assert score.score >= 90
    assert score.label == "Excellent Deal"


def test_price_at_historic_high_is_very_expensive():
    _, _, score = build([90, 95, 100, 120], target=80)
    assert score.score < 25
    assert score.label == "Very Expensive"


def test_score_is_always_between_0_and_100():
    for prices in ([1, 1000, 1], [1000, 1, 1000], [5, 5, 5], [100, 99, 98, 97]):
        _, _, score = build(prices, target=50)
        assert 0 <= score.score <= 100


def test_missing_inputs_are_excluded_not_guessed():
    _, _, score = build([100, 120, 110, 105])  # no target, no prediction
    by_key = {c.key: c for c in score.components}
    assert by_key["target"].fraction is None
    assert by_key["prediction"].fraction is None
    assert by_key["position"].fraction is not None


def test_flat_history_has_no_position_component():
    _, _, score = build([100, 100, 100, 100])
    by_key = {c.key: c for c in score.components}
    assert by_key["position"].fraction is None
    assert score.score is not None


def test_a_likely_further_drop_lowers_the_score():
    _, _, calm = build([120, 110, 100, 105], prediction={"decrease_probability": 0.05})
    _, _, falling = build([120, 110, 100, 105], prediction={"decrease_probability": 0.95})
    assert falling.score < calm.score


def test_explanation_matches_the_numbers():
    _, stats, score = build([100, 120, 110, 90])
    assert "below the historical average" in score.explanation
    assert "matches the historical low" in score.explanation


# ---------- advisor ----------

def test_advice_needs_five_checks():
    obs, stats, score = build([100, 90, 80, 70])
    assert compute_advice(obs, stats, score).verdict == "NO_DATA"


def test_buy_when_target_reached_and_no_drop_expected():
    obs, stats, score = build([120, 115, 110, 105, 100], target=102)
    advice = compute_advice(obs, stats, score, 102, {"decrease_probability": 0.1,
                            "predicted_price_low": 100, "predicted_price_high": 100})
    assert advice.verdict == "BUY"
    assert 0 <= advice.confidence <= 100
    assert any("Target price has been reached" in s.text for s in advice.signals)


def test_wait_with_expected_price_when_drop_is_likely():
    obs, stats, score = build([100, 110, 105, 120, 118])
    pred = {"decrease_probability": 0.8, "predicted_price_low": 100,
            "predicted_price_high": 108, "forecast_days": 14}
    advice = compute_advice(obs, stats, score, None, pred)
    assert advice.verdict == "WAIT"
    assert advice.expected_price == 104
    assert advice.expected_saving == pytest.approx(14)
    assert advice.wait_days == 14


def test_avoid_when_price_is_very_high_and_no_drop_expected():
    obs, stats, score = build([80, 85, 90, 95, 200])
    advice = compute_advice(obs, stats, score, None, None)
    assert score.score < 25
    assert advice.verdict == "AVOID"


def test_prediction_without_a_lower_range_gives_no_expected_price():
    obs, stats, score = build([100, 110, 105, 120, 118])
    pred = {"decrease_probability": 0.8, "predicted_price_low": 118,
            "predicted_price_high": 118, "forecast_days": 14}
    advice = compute_advice(obs, stats, score, None, pred)
    assert advice.expected_price is None


# ---------- savings ----------

def test_savings_numbers():
    obs, stats, _ = build([60, 50, 55, 45])
    sv = compute_savings(stats, target=40)
    assert sv.avg == pytest.approx(52.5)
    assert sv.vs_avg_amount == pytest.approx(7.5)
    assert sv.vs_avg_pct == pytest.approx(7.5 / 52.5 * 100)
    assert sv.vs_high_amount == 15
    assert sv.above_low == 0
    assert sv.target_gap == 5
    # started at 60, target 40, now 45 -> 15 of 20 closed
    assert sv.target_progress == pytest.approx(75)


def test_target_progress_is_100_when_reached_and_none_without_target():
    _, stats, _ = build([60, 50, 40])
    assert compute_savings(stats, 45).target_progress == 100
    assert compute_savings(stats, None).target_progress is None


def test_savings_unavailable_with_single_check():
    _, stats, _ = build([100])
    assert not compute_savings(stats).available


# ---------- volatility ----------

def test_volatility_needs_five_checks():
    obs, _, _ = build([100, 90, 100])
    assert not compute_volatility(obs).available


def test_flat_price_is_low_volatility():
    obs, _, _ = build([100] * 6)
    vol = compute_volatility(obs)
    assert vol.level == "LOW" and vol.score == 0 and vol.changes == 0


def test_big_frequent_swings_are_high_volatility():
    obs, _, _ = build([100, 80, 100, 80, 100, 80, 100], step_hours=48)
    vol = compute_volatility(obs)
    assert vol.level == "HIGH"
    assert vol.changes == 6
    assert vol.per_month == pytest.approx(6 / 12 * 30)  # 6 changes over 12 days


def test_per_month_not_extrapolated_from_a_short_window():
    obs, _, _ = build([100, 90, 100, 90, 100], step_hours=1)
    assert compute_volatility(obs).per_month is None


# ---------- best time ----------

def test_best_time_not_enough_observations():
    obs, stats, _ = build([100, 95, 100, 95, 100])
    bt = compute_best_time(obs, stats, NOW)
    assert not bt.available
    assert "Not enough historical observations" in bt.message


def test_best_time_needs_two_drops():
    obs, stats, _ = build([100] * 6 + [90] + [90] * 5)
    bt = compute_best_time(obs, stats, NOW)
    assert not bt.available
    assert bt.drops == 1


def test_best_time_from_real_drop_pattern():
    # a 10% drop every 5 days, price recovers in between
    prices = []
    for _ in range(5):
        prices += [100, 100, 100, 100, 90, 100][:5]
    obs, stats, _ = build(prices, step_hours=24)
    bt = compute_best_time(obs, stats, START + timedelta(days=24))
    assert bt.available
    assert bt.drops >= 2
    assert "10.0%" in bt.discount_range or "10" in bt.discount_range
    assert bt.confidence in ("Low", "Medium", "High")


# ---------- insights / timeline ----------

def test_insights_counts_and_trend():
    obs, stats, _ = build([100, 110, 105, 95, 90])
    ins = compute_insights(obs, stats)
    assert ins.total_drops == 3 and ins.total_increases == 1
    assert ins.low == 90 and ins.high == 110
    assert ins.trend == "Decreasing"
    assert any("lowest price recorded" in s for s in ins.sentences)


def test_timeline_skips_unchanged_repeats_newest_first():
    obs, _, _ = build([100, 100, 90, 90, 95])
    tl = compute_timeline(obs)
    assert [e.price for e in tl] == [95, 90, 100]
    assert [e.change for e in tl] == ["rise", "drop", None]


def test_timeline_limit():
    obs, _, _ = build(list(range(100, 130)))
    assert len(compute_timeline(obs, limit=8)) == 8


# ---------- alert levels ----------

def test_alert_levels():
    obs, stats, score = build([120, 115, 110, 100], target=100)
    assert compute_alert_level(obs, stats, score, 100, NOW).level == 4

    obs, stats, score = build([120, 115, 110, 103], target=100)
    assert compute_alert_level(obs, stats, score, 100, NOW).level == 3

    obs, stats, score = build([130, 120, 110, 100])  # no target, great deal
    assert score.score >= 75
    assert compute_alert_level(obs, stats, score, None, NOW).level == 2

    recent = START + timedelta(days=3)  # just after the last change
    obs, stats, score = build([100, 100, 100, 101])
    assert compute_alert_level(obs, stats, score, None, recent + timedelta(hours=1)).level in (1, 2)
    old = compute_alert_level(obs, stats, score, None, NOW)
    assert old.level in (0, 2)


def test_no_alert_when_nothing_notable():
    obs, stats, score = build([100, 100, 100, 100])
    assert compute_alert_level(obs, stats, score, None, NOW).level == 0


# ---------- tracking health ----------

def test_health_states():
    obs = to_observations(rows([100, 100], step_hours=1))
    last = obs[-1][0]
    assert compute_health([], 3600, NOW).state == "unchecked"
    assert compute_health(obs[:1], 3600, NOW).state == "unchecked"
    assert compute_health(obs, 3600, last + timedelta(minutes=30)).state == "active"
    assert compute_health(obs, 3600, last + timedelta(hours=5)).state == "issue"
    failed = compute_health(obs, 3600, last, manual_check_failed=True)
    assert failed.state == "unavailable" and failed.last_price == 100


def test_health_reports_only_recorded_data():
    obs = to_observations(rows([100, 90, 80]))
    h = compute_health(obs, 86400, obs[-1][0])
    assert h.recorded_checks == 3 and h.last_price == 80


def test_target_reached_does_not_override_a_poor_deal_score():
    # price is far above its history even though a loose target was met
    obs, stats, score = build([80, 85, 90, 95, 200], target=250)
    assert score.score < 50
    advice = compute_advice(obs, stats, score, 250, None)
    assert advice.verdict != "BUY"


def test_wait_wording_when_drop_may_be_imminent():
    from deal_analyzer import fmt_span
    assert fmt_span(0.2, 4) == "up to 4 days"
    assert fmt_span(3, 5) == "3–5 days"
