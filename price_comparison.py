"""Multi-store price comparison.

How it works, and its limits
----------------------------
The scraper can only read a page it is given a URL for; it cannot search
stores for a product. So comparison works from *links the user adds* for the
same product on other stores. Each link is scraped with the existing
`scraper.scrape_product`, and the price it returns is stored.

* Only pages the scraper can actually read are supported. If a store blocks
  the scraper, the link is rejected with the scraper's own error.
* The app cannot verify two links are the same item; the user decides.
* Prices are fetched when a link is added or refreshed, not continuously,
  and do not feed the price history, predictions or notifications.

The data lives in one extra table (`comparison_offers`) created on demand.
Existing tables are not touched.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

import database
from scraper import scrape_product

_SECOND_LEVEL = {"co", "com", "org", "net", "gov", "ac", "edu"}


def store_label(url):
    """'https://www.amazon.in/x' -> 'Amazon'; 'flipkart.com' -> 'Flipkart'."""

    host = (urlparse(url).netloc or "").lower().split(":")[0]
    parts = [p for p in host.split(".") if p and p != "www"]

    if not parts:
        return "Store"

    if len(parts) >= 3 and parts[-2] in _SECOND_LEVEL:
        name = parts[-3]
    elif len(parts) >= 2:
        name = parts[-2]
    else:
        name = parts[0]

    return name.replace("-", " ").title()


# --------------------------------------------------
# STORAGE
# --------------------------------------------------

def ensure_table():
    conn = database.get_connection()

    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS comparison_offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                store TEXT NOT NULL,
                name TEXT,
                price REAL NOT NULL,
                checked_at TIMESTAMP NOT NULL,
                UNIQUE (product_id, url),
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def list_offers(product_id):
    ensure_table()
    conn = database.get_connection()

    try:
        rows = conn.execute(
            "SELECT * FROM comparison_offers WHERE product_id = ? ORDER BY price ASC",
            (product_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _save_offer(product_id, url, store, name, price):
    ensure_table()
    conn = database.get_connection()

    try:
        conn.execute(
            """
            INSERT INTO comparison_offers (product_id, url, store, name, price, checked_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (product_id, url) DO UPDATE SET
                store = excluded.store,
                name = excluded.name,
                price = excluded.price,
                checked_at = excluded.checked_at
            """,
            (product_id, url, store, name, price, datetime.now().isoformat(sep=" ", timespec="seconds")),
        )
        conn.commit()
    finally:
        conn.close()


def add_offer(product_id, url, scrape=scrape_product):
    """Scrape `url` and store the price. Raises ScraperError on failure
    (nothing is stored in that case)."""

    result = scrape(url.strip())
    _save_offer(
        product_id,
        result["url"],
        store_label(result["url"]),
        result.get("name"),
        float(result["price"]),
    )


def refresh_offer(offer, scrape=scrape_product):
    """Re-scrape an existing offer. A failure leaves the stored price alone."""

    add_offer(offer["product_id"], offer["url"], scrape=scrape)


def remove_offer(offer_id):
    ensure_table()
    conn = database.get_connection()

    try:
        conn.execute("DELETE FROM comparison_offers WHERE id = ?", (offer_id,))
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------
# COMPARISON (pure)
# --------------------------------------------------

@dataclass(frozen=True)
class StoreRow:
    store: str
    price: float
    difference: float      # price - best price (0 for the best)
    is_best: bool
    is_tracked: bool       # the product's own tracked link
    checked_at: str | None = None
    offer_id: int | None = None


@dataclass(frozen=True)
class Comparison:
    rows: tuple
    best: StoreRow
    max_saving: float      # highest price - best price


def build_comparison(own_store, own_price, offers):
    """Combine the tracked product's own price with the stored offers.

    Returns None when there is nothing to compare against (no offers).
    """

    if not offers:
        return None

    entries = [(own_store, float(own_price), True, None, None)]
    entries += [
        (o["store"], float(o["price"]), False, o.get("checked_at"), o.get("id"))
        for o in offers
    ]
    entries.sort(key=lambda e: e[1])

    best_price = entries[0][1]
    rows = tuple(
        StoreRow(
            store=store, price=price, difference=price - best_price,
            is_best=abs(price - best_price) < 0.005, is_tracked=tracked,
            checked_at=checked, offer_id=offer_id,
        )
        for store, price, tracked, checked, offer_id in entries
    )
    highest = max(e[1] for e in entries)

    return Comparison(rows=rows, best=rows[0], max_saving=highest - best_price)
