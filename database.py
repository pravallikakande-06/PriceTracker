import os
import sqlite3
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "prices.db")


def get_connection():
    """Create and return a SQLite database connection."""

    os.makedirs(DATA_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


def initialize_database():
    """Create all required database tables."""

    conn = get_connection()

    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                current_price REAL NOT NULL,
                target_price REAL,
                lowest_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                target_alert_sent INTEGER DEFAULT 0
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                price REAL NOT NULL,
                checked_at TIMESTAMP NOT NULL,
                FOREIGN KEY (product_id)
                    REFERENCES products(id)
                    ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                email TEXT,
                price_drop_enabled INTEGER DEFAULT 1,
                target_alert_enabled INTEGER DEFAULT 1,
                prediction_enabled INTEGER DEFAULT 0,
                prediction_alert_probability REAL DEFAULT 0.7,
                prediction_min_discount REAL DEFAULT 5.0,
                prediction_forecast_window INTEGER DEFAULT 14,
                prediction_alert_cooldown INTEGER DEFAULT 24,
                prediction_min_observations INTEGER DEFAULT 10
            )
            """
        )

        # Migrate existing table to add new AI prediction settings columns
        new_columns = [
            ("prediction_enabled", "INTEGER DEFAULT 0"),
            ("prediction_alert_probability", "REAL DEFAULT 0.7"),
            ("prediction_min_discount", "REAL DEFAULT 5.0"),
            ("prediction_forecast_window", "INTEGER DEFAULT 14"),
            ("prediction_alert_cooldown", "INTEGER DEFAULT 24"),
            ("prediction_min_observations", "INTEGER DEFAULT 10"),
        ]
        
        for col_name, col_type in new_columns:
            try:
                conn.execute(f"ALTER TABLE notification_settings ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass

        existing_settings = conn.execute(
            """
            SELECT id
            FROM notification_settings
            WHERE id = 1
            """
        ).fetchone()

        if not existing_settings:
            conn.execute(
                """
                INSERT INTO notification_settings (
                    id,
                    email,
                    price_drop_enabled,
                    target_alert_enabled,
                    prediction_enabled,
                    prediction_alert_probability,
                    prediction_min_discount,
                    prediction_forecast_window,
                    prediction_alert_cooldown,
                    prediction_min_observations
                )
                VALUES (1, '', 1, 1, 0, 0.7, 5.0, 14, 24, 10)
                """
            )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prediction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                predicted_price_low REAL,
                predicted_price_high REAL,
                decrease_probability REAL,
                expected_discount_percent REAL,
                forecast_days INTEGER,
                confidence TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                actual_future_price REAL,
                evaluated INTEGER DEFAULT 0,
                prediction_error REAL,
                direction_correct INTEGER,
                current_price REAL,
                explanation TEXT,
                status TEXT,
                FOREIGN KEY (product_id)
                    REFERENCES products(id)
                    ON DELETE CASCADE
            )
            """
        )

        pred_columns = [
            ("actual_future_price", "REAL"),
            ("evaluated", "INTEGER DEFAULT 0"),
            ("prediction_error", "REAL"),
            ("direction_correct", "INTEGER"),
            ("current_price", "REAL"),
            ("explanation", "TEXT"),
            ("status", "TEXT"),
        ]
        
        for col_name, col_type in pred_columns:
            try:
                conn.execute(f"ALTER TABLE prediction_history ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass

        # Wishlist flag: additive, defaults to 0, existing rows are untouched.
        try:
            conn.execute("ALTER TABLE products ADD COLUMN wishlist INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        conn.commit()

    finally:
        conn.close()


def add_product(
    url,
    name,
    price,
    target_price=None,
):
    """Add a new product to the database."""

    conn = get_connection()

    try:
        checked_at = datetime.now().isoformat(
            timespec="seconds"
        )

        cursor = conn.execute(
            """
            INSERT INTO products (
                url,
                name,
                current_price,
                target_price,
                lowest_price,
                target_alert_sent
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                url,
                name,
                price,
                target_price,
                price,
                0,
            ),
        )

        product_id = cursor.lastrowid

        conn.execute(
            """
            INSERT INTO price_history (
                product_id,
                price,
                checked_at
            )
            VALUES (?, ?, ?)
            """,
            (
                product_id,
                float(price),
                checked_at,
            ),
        )

        conn.commit()

        return product_id

    finally:
        conn.close()


def get_products():
    """Return all tracked products."""

    conn = get_connection()

    try:
        return conn.execute(
            """
            SELECT *
            FROM products
            ORDER BY created_at DESC
            """
        ).fetchall()

    finally:
        conn.close()


def get_product(product_id):
    """Return one product by ID."""

    conn = get_connection()

    try:
        return conn.execute(
            """
            SELECT *
            FROM products
            WHERE id = ?
            """,
            (product_id,),
        ).fetchone()

    finally:
        conn.close()


def get_previous_price(product_id):
    """Return the previous recorded price."""

    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT price
            FROM price_history
            WHERE product_id = ?
            ORDER BY checked_at DESC, id DESC
            LIMIT 2
            """,
            (product_id,),
        ).fetchall()

        if len(rows) < 2:
            return None

        return float(rows[1]["price"])

    finally:
        conn.close()


def update_product_price(
    product_id,
    new_price,
):
    """
    Update the current price, lowest price,
    target alert status and price history.
    """

    conn = get_connection()

    try:
        product = conn.execute(
            """
            SELECT
                current_price,
                lowest_price,
                target_price,
                target_alert_sent
            FROM products
            WHERE id = ?
            """,
            (product_id,),
        ).fetchone()

        if not product:
            raise ValueError(
                "Product not found."
            )

        current_lowest = product[
            "lowest_price"
        ]

        target_price = product[
            "target_price"
        ]

        if current_lowest is None:
            lowest_price = float(new_price)
        else:
            lowest_price = min(
                float(current_lowest),
                float(new_price),
            )

        target_alert_sent = product[
            "target_alert_sent"
        ]

        # Reset target alert if the price
        # rises above the target.
        if (
            target_price is not None
            and float(new_price)
            > float(target_price)
        ):
            target_alert_sent = 0

        conn.execute(
            """
            UPDATE products
            SET current_price = ?,
                lowest_price = ?,
                updated_at = CURRENT_TIMESTAMP,
                target_alert_sent = ?
            WHERE id = ?
            """,
            (
                float(new_price),
                lowest_price,
                target_alert_sent,
                product_id,
            ),
        )

        checked_at = datetime.now().isoformat(
            timespec="seconds"
        )

        conn.execute(
            """
            INSERT INTO price_history (
                product_id,
                price,
                checked_at
            )
            VALUES (?, ?, ?)
            """,
            (
                product_id,
                float(new_price),
                checked_at,
            ),
        )

        conn.commit()

    finally:
        conn.close()


def get_price_history(product_id):
    """Return price history for a product."""

    conn = get_connection()

    try:
        return conn.execute(
            """
            SELECT
                id,
                product_id,
                price,
                checked_at
            FROM price_history
            WHERE product_id = ?
            ORDER BY checked_at ASC, id ASC
            """,
            (product_id,),
        ).fetchall()

    finally:
        conn.close()


def update_notification_settings(
    email,
    price_drop_enabled,
    target_alert_enabled,
    prediction_enabled=0,
    prediction_alert_probability=0.7,
    prediction_min_discount=5.0,
    prediction_forecast_window=14,
    prediction_alert_cooldown=24,
    prediction_min_observations=10,
):
    """Save notification settings."""

    conn = get_connection()

    try:
        conn.execute(
            """
            UPDATE notification_settings
            SET email = ?,
                price_drop_enabled = ?,
                target_alert_enabled = ?,
                prediction_enabled = ?,
                prediction_alert_probability = ?,
                prediction_min_discount = ?,
                prediction_forecast_window = ?,
                prediction_alert_cooldown = ?,
                prediction_min_observations = ?
            WHERE id = 1
            """,
            (
                email,
                int(price_drop_enabled),
                int(target_alert_enabled),
                int(prediction_enabled),
                float(prediction_alert_probability),
                float(prediction_min_discount),
                int(prediction_forecast_window),
                int(prediction_alert_cooldown),
                int(prediction_min_observations),
            ),
        )

        conn.commit()

    finally:
        conn.close()


def get_notification_settings():
    """Return notification settings."""

    conn = get_connection()

    try:
        return conn.execute(
            """
            SELECT *
            FROM notification_settings
            WHERE id = 1
            """
        ).fetchone()

    finally:
        conn.close()


def mark_target_alert_sent(product_id):
    """Mark the target-price alert as already sent."""

    conn = get_connection()

    try:
        conn.execute(
            """
            UPDATE products
            SET target_alert_sent = 1
            WHERE id = ?
            """,
            (product_id,),
        )

        conn.commit()

    finally:
        conn.close()

def save_prediction(
    product_id,
    predicted_price_low,
    predicted_price_high,
    decrease_probability,
    expected_discount_percent,
    forecast_days,
    confidence,
    current_price=0.0,
    explanation="",
    status=""
):
    """Save a new prediction to the database."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO prediction_history (
                product_id,
                predicted_price_low,
                predicted_price_high,
                decrease_probability,
                expected_discount_percent,
                forecast_days,
                confidence,
                current_price,
                explanation,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                predicted_price_low,
                predicted_price_high,
                decrease_probability,
                expected_discount_percent,
                forecast_days,
                confidence,
                current_price,
                explanation,
                status,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_prediction(product_id):
    """Return the most recent prediction for a product."""
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT *
            FROM prediction_history
            WHERE product_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (product_id,),
        ).fetchone()
    finally:
        conn.close()


def get_prediction_history(product_id):
    """Return all predictions for a product."""
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT *
            FROM prediction_history
            WHERE product_id = ?
            ORDER BY created_at ASC
            """,
            (product_id,),
        ).fetchall()
    finally:
        conn.close()


def evaluate_predictions(product_id, current_price):
    """
    Evaluate past predictions for a product based on a newly fetched price.
    Mark evaluated = 1, compute error and direction_correct.
    """
    conn = get_connection()
    try:
        # Find all predictions for this product that have NOT been evaluated yet.
        # And where forecast_days have roughly passed (or any future price lower than predicted).
        # We will just evaluate any un-evaluated prediction that was made before today
        # by checking if current_price validates the prediction.
        preds = conn.execute(
            """
            SELECT id, current_price, decrease_probability, predicted_price_high, predicted_price_low
            FROM prediction_history
            WHERE product_id = ? AND evaluated = 0
            """,
            (product_id,)
        ).fetchall()

        for p in preds:
            pred_id = p["id"]
            old_price = p["current_price"]
            prob = p["decrease_probability"]
            predicted_high = p["predicted_price_high"]
            predicted_low = p["predicted_price_low"]
            
            # If current price is lower than old price, it's a decrease
            direction_correct = 1 if (prob >= 0.5 and current_price < old_price) or (prob < 0.5 and current_price >= old_price) else 0
            
            # Error calculation based on midpoint of prediction
            midpoint = (predicted_high + predicted_low) / 2
            error = abs(current_price - midpoint) if prob >= 0.5 else 0.0 # Only care about error if we predicted a decrease
            
            conn.execute(
                """
                UPDATE prediction_history
                SET evaluated = 1, actual_future_price = ?, prediction_error = ?, direction_correct = ?
                WHERE id = ?
                """,
                (current_price, error, direction_correct, pred_id)
            )
        conn.commit()
    finally:
        conn.close()

def get_prediction_evaluation_metrics():
    """Return metrics for all evaluated predictions."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COUNT(id) as total_evaluated,
                   AVG(prediction_error) as avg_error,
                   SUM(direction_correct) as correct_predictions
            FROM prediction_history
            WHERE evaluated = 1
            """
        ).fetchone()
        
        if not row or row["total_evaluated"] == 0:
            return None
            
        total = row["total_evaluated"]
        accuracy = (row["correct_predictions"] / total) * 100
        return {
            "total_evaluated": total,
            "avg_error": row["avg_error"],
            "direction_accuracy": accuracy
        }
    finally:
        conn.close()


def set_wishlist(product_id, in_wishlist):
    """Add or remove a product from the wishlist."""

    conn = get_connection()

    try:
        conn.execute(
            """
            UPDATE products
            SET wishlist = ?
            WHERE id = ?
            """,
            (1 if in_wishlist else 0, product_id),
        )

        conn.commit()

    finally:
        conn.close()
