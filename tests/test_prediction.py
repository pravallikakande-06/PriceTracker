import os
import sqlite3
import pytest
from datetime import datetime, timedelta

from database import (
    initialize_database,
    add_product,
    get_connection,
    evaluate_predictions,
    get_prediction_evaluation_metrics,
    get_latest_prediction
)
from prediction import generate_price_forecast

# Ensure we use an in-memory DB or temporary file for testing
@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test_prices.db"
    
    # Mock get_connection to use our test db
    def mock_get_connection():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    monkeypatch.setattr('database.get_connection', mock_get_connection)
    
    # Initialize schema
    import database
    database.get_connection = mock_get_connection
    initialize_database()

def test_insufficient_data():
    product_id = add_product("http://test", "Test Product", 60000)
    # Only 1 record exists
    forecast = generate_price_forecast(product_id)
    assert forecast is None

def test_generate_price_forecast():
    product_id = add_product("http://test2", "Test Product 2", 60000)
    
    import database
    conn = database.get_connection()
    
    prices = [60000, 59500, 58000, 57500, 56000, 55000, 54500, 53500, 54000, 55000]
    base_date = datetime.now() - timedelta(days=25)
    
    try:
        # Clear existing
        conn.execute("DELETE FROM price_history WHERE product_id = ?", (product_id,))
        
        # Insert test data
        for i, price in enumerate(prices):
            date = base_date + timedelta(days=i*2)
            conn.execute(
                "INSERT INTO price_history (product_id, price, checked_at) VALUES (?, ?, ?)",
                (product_id, price, date.isoformat())
            )
        conn.commit()
    finally:
        conn.close()
        
    forecast = generate_price_forecast(product_id)
    
    assert forecast is not None
    assert forecast["current_price"] == 55000
    assert forecast["historical_max"] == 60000
    assert forecast["historical_min"] == 53500
    assert forecast["decrease_probability"] > 0
    assert "confidence" in forecast

def test_prediction_evaluation():
    product_id = add_product("http://test3", "Test Product 3", 1000)
    
    import database
    conn = database.get_connection()
    try:
        prices = [1000, 950, 900, 850, 800, 800, 800, 800, 800, 800]
        base_date = datetime.now() - timedelta(days=20)
        conn.execute("DELETE FROM price_history WHERE product_id = ?", (product_id,))
        for i, price in enumerate(prices):
            date = base_date + timedelta(days=i)
            conn.execute(
                "INSERT INTO price_history (product_id, price, checked_at) VALUES (?, ?, ?)",
                (product_id, price, date.isoformat())
            )
        conn.commit()
    finally:
        conn.close()
        
    forecast = generate_price_forecast(product_id)
    assert forecast is not None
    
    latest_pred = get_latest_prediction(product_id)
    assert latest_pred is not None
    assert latest_pred['evaluated'] == 0
    
    evaluate_predictions(product_id, 750)
    
    latest_pred = get_latest_prediction(product_id)
    assert latest_pred['evaluated'] == 1
    
    metrics = get_prediction_evaluation_metrics()
    assert metrics is not None
    assert metrics['total_evaluated'] > 0

