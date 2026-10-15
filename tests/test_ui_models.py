"""Tests for the dashboard's presentation logic (no Streamlit needed)."""

import sqlite3
from datetime import datetime, timedelta

from scraper import ScraperError
from ui import models
from ui.components import card_head_html, esc


def make_view(
    pid=1,
    name="Test Laptop",
    prices=(54999.0, 49999.0),
    target=None,
    last_checked=None,
):
    """Build a ProductView from a plain list of prices."""

    start = datetime(2026, 9, 30, 18, 0)
    rows = [
        {
            "id": index + 1,
            "product_id": pid,
            "price": price,
            "checked_at": (start + timedelta(minutes=index)).isoformat(),
        }
        for index, price in enumerate(prices)
    ]
    product = {
        "id": pid,
        "name": name,
        "url": f"http://shop.example/{pid}",
        "current_price": prices[-1],
        "lowest_price": min(prices),
        "target_price": target,
    }
    view = models.build_product_view(product, rows)

    if last_checked is not None:
        object.__setattr__(view, "last_checked", last_checked)

    return view


# ---------- price change ----------

def test_price_drop_reports_percentage_and_amount():
    change = make_view(prices=(54999.0, 49999.0)).change

    assert change.kind == "drop"
    assert change.amount == 5000
    assert round(change.pct, 2) == 9.09


def test_drop_is_still_shown_after_an_unchanged_recheck():
    change = make_view(prices=(54999.0, 49999.0, 49999.0)).change

    assert change.kind == "drop"
    assert change.amount == 5000


def test_rise_flat_and_new():
    assert make_view(prices=(100.0, 104.5)).change.kind == "rise"
    assert make_view(prices=(100.0, 100.0)).change.kind == "flat"
    assert make_view(prices=(100.0,)).change.kind == "new"


# ---------- target status ----------

def test_target_states():
    assert make_view(prices=(100.0,)).target_status.kind == "none"
    assert make_view(prices=(50000.0,), target=50000.0).target_status.kind == "reached"
    assert make_view(prices=(40000.0,), target=50000.0).target_status.kind == "reached"
    assert make_view(prices=(50500.0,), target=50000.0).target_status.kind == "near"
    assert make_view(prices=(60000.0,), target=50000.0).target_status.kind == "above"


# ---------- summary, filter, sort ----------

def test_summary_values():
    views = [
        make_view(1, "A", (200.0, 100.0), target=150.0),
        make_view(2, "B", (300.0,), target=200.0),
    ]
    summary = models.summarize(views)

    assert summary.count == 2
    assert summary.with_target == 2
    assert summary.reached == 1
    assert summary.lowest == 100.0
    assert summary.lowest_name == "A"
    assert summary.average == 200.0


def test_summary_of_nothing():
    assert models.summarize([]).count == 0


def test_search_is_case_insensitive():
    views = [make_view(1, "Gaming Mouse"), make_view(2, "Test Laptop")]

    assert [v.name for v in models.filter_products(views, "LAPTOP")] == ["Test Laptop"]
    assert len(models.filter_products(views, "  ")) == 2


def test_sorting_options():
    cheap = make_view(1, "Cheap", (500.0, 400.0))
    pricey = make_view(2, "Pricey", (900.0, 950.0), target=1000.0)
    flat = make_view(3, "Flat", (700.0, 700.0))
    views = [pricey, flat, cheap]

    def names(option):
        return [v.name for v in models.sort_products(views, option)]

    assert names(models.SORT_LOWEST) == ["Cheap", "Flat", "Pricey"]
    assert names(models.SORT_HIGHEST) == ["Pricey", "Flat", "Cheap"]
    assert names(models.SORT_DROP)[0] == "Cheap"
    assert names(models.SORT_TARGET)[0] == "Pricey"


def test_recently_checked_puts_latest_first():
    old = make_view(1, "Old", last_checked=datetime(2026, 1, 1))
    new = make_view(2, "New", last_checked=datetime(2026, 6, 1))

    result = models.sort_products([old, new], models.SORT_RECENT)

    assert [v.name for v in result] == ["New", "Old"]


# ---------- formatting ----------

def test_money_and_percentage_formatting():
    assert models.format_money(49999.0) == "₹49,999"
    assert models.format_money(1234.5) == "₹1,234.50"
    assert models.format_money(None) == "—"
    assert models.format_pct(-9.0909) == "9.09%"


def test_time_ago():
    now = datetime(2026, 9, 30, 12, 0)

    assert models.time_ago(None, now) == "never"
    assert models.time_ago(now - timedelta(seconds=10), now) == "just now"
    assert models.time_ago(now - timedelta(minutes=2), now) == "2 minutes ago"
    assert models.time_ago(now - timedelta(hours=1), now) == "1 hour ago"
    assert models.time_ago(now + timedelta(minutes=5), now) == "just now"


def test_interval_text():
    assert models.format_interval(3600) == "every hour"
    assert models.format_interval(1800) == "every 30 min"
    assert models.format_interval(7200) == "every 2 hours"


# ---------- notification status ----------

def test_notification_status():
    assert not models.notification_status(None).enabled

    off = {"email": "", "price_drop_enabled": 1, "target_alert_enabled": 1}
    both_off = {"email": "a@b.co", "price_drop_enabled": 0, "target_alert_enabled": 0}
    on = {"email": "a@b.co", "price_drop_enabled": 1, "target_alert_enabled": 0}

    assert not models.notification_status(off).enabled
    assert not models.notification_status(both_off).enabled
    assert models.notification_status(on).enabled


# ---------- friendly errors ----------

def test_scraper_errors_become_friendly_messages():
    blocked = models.explain_error(
        ScraperError("Could not access the website: 403 Client Error")
    )

    assert blocked.title == "Unable to access product page"
    assert "403" in blocked.detail

    no_price = models.explain_error(ScraperError("Product price could not be found."))

    assert "price" in no_price.title.lower()


def test_only_unique_violations_are_called_duplicates():
    duplicate = models.explain_error(
        sqlite3.IntegrityError("UNIQUE constraint failed: products.url")
    )
    other = models.explain_error(
        sqlite3.IntegrityError("NOT NULL constraint failed: products.created_at")
    )

    assert "already tracking" in duplicate.title
    assert "already tracking" not in other.title


def test_unknown_errors_keep_technical_detail():
    error = models.explain_error(RuntimeError("boom"))

    assert error.title == "Something went wrong"
    assert "boom" in error.detail


# ---------- HTML safety ----------

def test_untrusted_text_is_escaped():
    assert esc("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert "$" not in esc("$5 and $10")

    view = make_view(name="<img src=x onerror=alert(1)>")

    assert "<img" not in card_head_html(view)