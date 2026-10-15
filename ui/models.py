"""Presentation logic for the dashboard.

Everything here is a pure function or a small dataclass built from rows
the existing backend already returns. This module never imports Streamlit
and never writes to the database, which keeps it easy to test.
"""

from __future__ import annotations

import os
import re
import smtplib
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd

from scraper import ScraperError


# --------------------------------------------------
# CONSTANTS
# --------------------------------------------------

# A product is "near" its target when it is within this % of the target.
NEAR_TARGET_PCT = 5.0

# Mirrors scheduler.py, which defaults to one hour.
DEFAULT_CHECK_INTERVAL = 3600

# Prices closer than this are treated as equal (float safety).
_EPSILON = 0.005

SORT_RECENT = "Recently checked"
SORT_LOWEST = "Lowest price"
SORT_HIGHEST = "Highest price"
SORT_DROP = "Biggest price drop"
SORT_TARGET = "Target reached"

SORT_OPTIONS = (
    SORT_RECENT,
    SORT_LOWEST,
    SORT_HIGHEST,
    SORT_DROP,
    SORT_TARGET,
)

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --------------------------------------------------
# FORMATTING
# --------------------------------------------------

def format_money(value):
    """Format a price as rupees, hiding '.00' on whole amounts."""

    if value is None:
        return "—"

    if abs(value - round(value)) < _EPSILON:
        return f"₹{round(value):,}"

    return f"₹{value:,.2f}"


def format_pct(value):
    """Format a percentage with two decimals, e.g. '9.09%'."""

    return f"{abs(value):.2f}%"


def format_timestamp(when):
    """Return e.g. '30 Sep, 6:50 PM' (avoids platform-specific strftime)."""

    hour = when.hour % 12 or 12
    suffix = "AM" if when.hour < 12 else "PM"

    return f"{when.day} {when:%b}, {hour}:{when:%M} {suffix}"


def _plural(count, unit):
    return f"{count} {unit}{'' if count == 1 else 's'}"


def time_ago(when, now=None):
    """Describe how long ago `when` was, in plain language."""

    if when is None:
        return "never"

    now = now or datetime.now()
    seconds = (now - when).total_seconds()

    # Clock skew or future timestamps should not look broken.
    if seconds < 60:
        return "just now"

    minutes = int(seconds // 60)

    if minutes < 60:
        return f"{_plural(minutes, 'minute')} ago"

    hours = minutes // 60

    if hours < 24:
        return f"{_plural(hours, 'hour')} ago"

    days = hours // 24

    if days < 7:
        return f"{_plural(days, 'day')} ago"

    return f"on {when.day} {when:%b %Y}"


def check_interval_seconds():
    """Return the configured scheduler interval (CHECK_INTERVAL)."""

    try:
        value = int(
            os.getenv("CHECK_INTERVAL", str(DEFAULT_CHECK_INTERVAL))
        )
    except ValueError:
        return DEFAULT_CHECK_INTERVAL

    return value if value > 0 else DEFAULT_CHECK_INTERVAL


def format_interval(seconds):
    """Return e.g. 'every hour', 'every 30 min', 'every 2 hours'."""

    if seconds < 60:
        return f"every {seconds} sec"

    if seconds == 3600:
        return "every hour"

    if seconds % 3600 == 0:
        return f"every {seconds // 3600} hours"

    return f"every {round(seconds / 60)} min"


def is_valid_email(value):
    """Loose sanity check; the SMTP server has the final say."""

    return bool(_EMAIL_PATTERN.match(value.strip()))


# --------------------------------------------------
# PRODUCT VIEW MODEL
# --------------------------------------------------

@dataclass(frozen=True)
class PriceChange:
    """How the price moved the last time it actually changed.

    kind is one of: "drop", "rise", "flat", "new".
    `amount` and `pct` are always positive magnitudes.
    """

    kind: str
    amount: float = 0.0
    pct: float = 0.0
    since: datetime | None = None


@dataclass(frozen=True)
class TargetStatus:
    """Where the current price sits relative to the target.

    kind is one of: "none", "reached", "near", "above".
    `gap` is current - target (positive means above target).
    """

    kind: str
    gap: float = 0.0


@dataclass(frozen=True)
class ProductView:
    """Everything a product card needs, derived from existing data."""

    id: int
    name: str
    url: str
    current: float
    lowest: float
    target: float | None
    first_price: float
    last_checked: datetime | None
    history: pd.DataFrame
    change: PriceChange
    target_status: TargetStatus

    @property
    def domain(self):
        return urlparse(self.url).netloc or self.url


def history_to_frame(rows):
    """Convert get_price_history() rows into a clean DataFrame."""

    frame = pd.DataFrame(
        [dict(row) for row in rows],
        columns=["id", "product_id", "price", "checked_at"],
    )

    # Old rows contain microseconds, newer ones do not.
    frame["checked_at"] = pd.to_datetime(
        frame["checked_at"],
        format="mixed",
        errors="coerce",
    )
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")

    frame = (
        frame.dropna(subset=["checked_at", "price"])
        .sort_values(["checked_at", "id"])
        .reset_index(drop=True)
    )

    return frame[["checked_at", "price"]]


def compute_price_change(current, prices, times):
    """Compare `current` with the last *different* recorded price.

    Comparing with the last different price (rather than only the previous
    row) keeps a "Price dropped" message visible after a re-check that
    found the same price, instead of flipping to "unchanged".
    """

    index = len(prices) - 1

    while index >= 0 and abs(prices[index] - current) < _EPSILON:
        index -= 1

    if index < 0:
        kind = "flat" if len(prices) >= 2 else "new"
        since = times[0] if times else None

        return PriceChange(kind=kind, since=since)

    previous = prices[index]
    amount = abs(current - previous)
    pct = (amount / previous * 100) if previous else 0.0
    since = times[index + 1] if index + 1 < len(times) else None

    return PriceChange(
        kind="drop" if current < previous else "rise",
        amount=amount,
        pct=pct,
        since=since,
    )


def compute_target_status(current, target):
    """Classify the current price against the optional target."""

    if target is None:
        return TargetStatus("none")

    gap = current - target

    if gap <= _EPSILON:
        return TargetStatus("reached", gap)

    if target > 0 and gap / target * 100 <= NEAR_TARGET_PCT:
        return TargetStatus("near", gap)

    return TargetStatus("above", gap)


def build_product_view(product, history_rows):
    """Build a ProductView from a products row and its history rows."""

    product = dict(product)

    current = float(product["current_price"])
    history = history_to_frame(history_rows)

    prices = history["price"].tolist()
    times = [ts.to_pydatetime() for ts in history["checked_at"]]

    raw_lowest = product.get("lowest_price")

    if raw_lowest is not None:
        lowest = float(raw_lowest)
    elif prices:
        lowest = min(prices)
    else:
        lowest = current

    raw_target = product.get("target_price")
    target = float(raw_target) if raw_target is not None else None

    return ProductView(
        id=product["id"],
        name=product["name"],
        url=product["url"],
        current=current,
        lowest=min(lowest, current),
        target=target,
        first_price=prices[0] if prices else current,
        last_checked=times[-1] if times else None,
        history=history,
        change=compute_price_change(current, prices, times),
        target_status=compute_target_status(current, target),
    )


# --------------------------------------------------
# DASHBOARD SUMMARY
# --------------------------------------------------

@dataclass(frozen=True)
class Summary:
    count: int
    with_target: int
    reached: int
    lowest: float | None
    lowest_name: str | None
    average: float | None
    average_change_pct: float | None


def summarize(views):
    """Compute the four headline metrics from the product views."""

    if not views:
        return Summary(0, 0, 0, None, None, None, None)

    cheapest = min(views, key=lambda view: view.current)

    average = sum(view.current for view in views) / len(views)
    average_first = sum(view.first_price for view in views) / len(views)

    change_pct = (
        (average - average_first) / average_first * 100
        if average_first
        else None
    )

    return Summary(
        count=len(views),
        with_target=sum(view.target is not None for view in views),
        reached=sum(
            view.target_status.kind == "reached" for view in views
        ),
        lowest=cheapest.current,
        lowest_name=cheapest.name,
        average=average,
        average_change_pct=change_pct,
    )


# --------------------------------------------------
# SEARCH AND SORT
# --------------------------------------------------

def filter_products(views, query):
    """Case-insensitive product-name search."""

    needle = (query or "").strip().casefold()

    if not needle:
        return list(views)

    return [view for view in views if needle in view.name.casefold()]


def sort_products(views, option):
    """Sort product views using one of SORT_OPTIONS."""

    if option == SORT_LOWEST:
        return sorted(views, key=lambda view: view.current)

    if option == SORT_HIGHEST:
        return sorted(views, key=lambda view: -view.current)

    if option == SORT_DROP:
        return sorted(
            views,
            # Only real drops are ranked; everything else keeps its order.
            key=lambda view: (
                view.change.kind != "drop",
                -view.change.pct if view.change.kind == "drop" else 0.0,
            ),
        )

    if option == SORT_TARGET:
        rank = {"reached": 0, "near": 1, "above": 2, "none": 3}

        def distance(view):
            if view.target:
                return view.target_status.gap / view.target

            return 0.0

        return sorted(
            views,
            key=lambda view: (
                rank[view.target_status.kind],
                distance(view),
            ),
        )

    # Default: most recently checked first.
    return sorted(
        views,
        key=lambda view: view.last_checked or datetime.min,
        reverse=True,
    )


# --------------------------------------------------
# NOTIFICATION AND SCHEDULER STATUS
# --------------------------------------------------

@dataclass(frozen=True)
class NotificationStatus:
    enabled: bool
    headline: str
    detail: str
    email: str
    price_drop: bool
    target_alert: bool


def notification_status(settings):
    """Summarise the saved notification settings row."""

    if not settings:
        return NotificationStatus(
            False, "Off", "No email address saved yet.", "", True, True
        )

    email = (settings["email"] or "").strip()
    price_drop = bool(settings["price_drop_enabled"])
    target_alert = bool(settings["target_alert_enabled"])

    if not email:
        return NotificationStatus(
            False,
            "Off",
            "Add an email address to receive alerts.",
            email,
            price_drop,
            target_alert,
        )

    if not (price_drop or target_alert):
        return NotificationStatus(
            False,
            "Off",
            "Both alert types are switched off.",
            email,
            price_drop,
            target_alert,
        )

    return NotificationStatus(
        True,
        "On",
        f"Alerts go to {email}.",
        email,
        price_drop,
        target_alert,
    )


def smtp_configured():
    """True when SMTP credentials are present in the environment."""

    return bool(
        os.getenv("SMTP_USERNAME") and os.getenv("SMTP_PASSWORD")
    )


def latest_check(views):
    """Most recent check recorded across all products (or None)."""

    times = [view.last_checked for view in views if view.last_checked]

    return max(times) if times else None


# --------------------------------------------------
# FRIENDLY ERRORS
# --------------------------------------------------

@dataclass(frozen=True)
class FriendlyError:
    """A user-facing explanation plus the raw technical detail."""

    title: str
    body: str
    detail: str | None = None


def explain_error(exc):
    """Translate an exception into a message people can act on.

    The scraper raises ScraperError with plain-English strings but no
    error codes, so known messages are matched by their wording. Anything
    unrecognised falls back to a generic message and the raw detail.
    """

    raw = str(exc)
    text = raw.lower()
    detail = f"{type(exc).__name__}: {raw}"

    if isinstance(exc, sqlite3.IntegrityError):
        # Only a UNIQUE violation means the link is already tracked.
        if "unique" in text:
            return FriendlyError(
                "You're already tracking this product",
                "That link is already in your list. Check its card "
                "below for the latest price.",
                detail,
            )

        return FriendlyError(
            "Couldn't save this product",
            "The database rejected the new product. If data/prices.db "
            "was created by an older version of the app, back it up and "
            "delete it so a fresh one is created on the next run.",
            detail,
        )

    if isinstance(exc, ScraperError):
        if "url is required" in text or "must start with" in text:
            return FriendlyError(
                "That doesn't look like a product link",
                "Paste the full address, starting with http:// or "
                "https://.",
            )

        if "took too long" in text:
            return FriendlyError(
                "The website didn't respond in time",
                "The page may be slow or temporarily down. "
                "Try again in a moment.",
                detail,
            )

        if "could not access" in text:
            return FriendlyError(
                "Unable to access product page",
                "The website may be blocking automated requests "
                "or may require JavaScript.",
                detail,
            )

        if "price could not be found" in text:
            return FriendlyError(
                "We couldn't find a price on that page",
                "The site may load prices with JavaScript or use a "
                "layout we don't recognise. Try a direct product page.",
                detail,
            )

        if "name could not be found" in text:
            return FriendlyError(
                "We couldn't read the product name",
                "Make sure the link opens a single product page.",
                detail,
            )

        return FriendlyError(
            "We couldn't read that page",
            "The product details could not be extracted.",
            detail,
        )

    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return FriendlyError(
            "The email server rejected the login",
            "Check SMTP_USERNAME and SMTP_PASSWORD in your .env file. "
            "Gmail needs an app password.",
            detail,
        )

    if "smtp credentials" in text:
        return FriendlyError(
            "Email alerts aren't set up yet",
            "Add SMTP_USERNAME and SMTP_PASSWORD to your .env file.",
            detail,
        )

    if isinstance(exc, (smtplib.SMTPException, OSError)):
        return FriendlyError(
            "Couldn't reach the email server",
            "Check SMTP_HOST, SMTP_PORT and your internet connection.",
            detail,
        )

    if "product not found" in text:
        return FriendlyError(
            "That product no longer exists",
            "Refresh the page to see your current list.",
            detail,
        )

    return FriendlyError(
        "Something went wrong",
        "The action didn't complete. Technical details are below.",
        detail,
    )