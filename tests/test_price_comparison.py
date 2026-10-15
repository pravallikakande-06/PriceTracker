"""Tests for multi-store comparison and the wishlist (temporary database)."""

import sqlite3

import pytest

import database
import price_comparison as pc
from scraper import ScraperError


@pytest.fixture(autouse=True)
def temp_db(monkeypatch, tmp_path):
    path = tmp_path / "test.db"

    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    monkeypatch.setattr("database.get_connection", connect)
    database.initialize_database()
    database.add_product("https://shop-a.example/p", "Phone", 69999.0, 65000.0)


def fake_scrape(price, url="https://www.flipkart.com/p"):
    return lambda u: {"url": url, "name": "Phone 128GB", "price": price}


def test_store_label():
    assert pc.store_label("https://www.amazon.in/dp/1") == "Amazon"
    assert pc.store_label("https://flipkart.com/x") == "Flipkart"
    assert pc.store_label("https://www.shop.co.uk/x") == "Shop"
    assert pc.store_label("http://localhost:8000/p.html") == "Localhost"
    assert pc.store_label("") == "Store"


def test_add_list_and_remove_offer():
    pc.add_offer(1, "https://www.flipkart.com/p", scrape=fake_scrape(67499.0))
    offers = pc.list_offers(1)
    assert len(offers) == 1 and offers[0]["store"] == "Flipkart" and offers[0]["price"] == 67499.0
    pc.remove_offer(offers[0]["id"])
    assert pc.list_offers(1) == []


def test_refresh_updates_price_and_failure_keeps_old_price():
    pc.add_offer(1, "https://www.flipkart.com/p", scrape=fake_scrape(67499.0))
    offer = pc.list_offers(1)[0]
    pc.refresh_offer(offer, scrape=fake_scrape(66000.0))
    assert pc.list_offers(1)[0]["price"] == 66000.0

    def broken(_):
        raise ScraperError("blocked")

    with pytest.raises(ScraperError):
        pc.refresh_offer(pc.list_offers(1)[0], scrape=broken)
    assert pc.list_offers(1)[0]["price"] == 66000.0
    assert len(pc.list_offers(1)) == 1  # no duplicate row


def test_failed_add_stores_nothing():
    def broken(_):
        raise ScraperError("blocked")

    with pytest.raises(ScraperError):
        pc.add_offer(1, "https://x.example/p", scrape=broken)
    assert pc.list_offers(1) == []


def test_comparison_best_price_and_saving():
    pc.add_offer(1, "https://www.flipkart.com/p", scrape=fake_scrape(67499.0))
    pc.add_offer(1, "https://www.croma.com/p", scrape=fake_scrape(71999.0, "https://www.croma.com/p"))
    comp = pc.build_comparison("Shop A", 69999.0, pc.list_offers(1))
    assert comp.best.store == "Flipkart" and comp.best.is_best
    assert comp.max_saving == pytest.approx(4500)
    diffs = {r.store: r.difference for r in comp.rows}
    assert diffs["Shop A"] == pytest.approx(2500) and diffs["Croma"] == pytest.approx(4500)
    assert sum(r.is_tracked for r in comp.rows) == 1


def test_comparison_is_none_without_offers():
    assert pc.build_comparison("Shop A", 100.0, []) is None


def test_offers_are_deleted_with_their_product():
    pc.add_offer(1, "https://www.flipkart.com/p", scrape=fake_scrape(67499.0))
    conn = database.get_connection()
    conn.execute("DELETE FROM products WHERE id = 1")
    conn.commit()
    conn.close()
    assert pc.list_offers(1) == []


# ---------- wishlist ----------

def test_wishlist_toggle_persists_and_defaults_off():
    assert not database.get_product(1)["wishlist"]
    database.set_wishlist(1, True)
    assert database.get_product(1)["wishlist"] == 1
    database.set_wishlist(1, False)
    assert database.get_product(1)["wishlist"] == 0


def test_wishlist_migration_keeps_existing_data(monkeypatch, tmp_path):
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE products (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL, current_price REAL NOT NULL, target_price REAL, lowest_price REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        target_alert_sent INTEGER DEFAULT 0)""")
    conn.execute("INSERT INTO products (url, name, current_price) VALUES ('u', 'Old Product', 123.0)")
    conn.commit()
    conn.close()

    def connect():
        c = sqlite3.connect(path)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr("database.get_connection", connect)
    database.initialize_database()
    database.initialize_database()  # idempotent
    row = database.get_product(1)
    assert row["name"] == "Old Product" and row["current_price"] == 123.0
    assert row["wishlist"] == 0
