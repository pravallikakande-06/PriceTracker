from database import (
    get_product,
    get_previous_price,
    get_notification_settings,
    update_product_price,
    mark_target_alert_sent,
    evaluate_predictions,
)

from scraper import scrape_product

from prediction import generate_price_forecast

from notifier import (
    send_price_drop_alert,
    send_target_price_alert,
    send_price_prediction_alert,
)


def calculate_percentage_change(previous_price, current_price):
    """Calculate percentage change between two prices."""

    if previous_price is None or previous_price == 0:
        return 0.0

    return (
        (current_price - previous_price)
        / previous_price
    ) * 100


def check_product(product_id):
    """
    Scrape the latest product price and update the database.
    """

    product = get_product(product_id)

    if not product:
        raise ValueError("Product not found.")

    result = scrape_product(product["url"])

    current_price = float(result["price"])

    previous_price = get_previous_price(product_id)

    percentage_change = calculate_percentage_change(
        previous_price,
        current_price,
    )

    price_decreased = (
        previous_price is not None
        and current_price < previous_price
    )

    target_reached = (
        product["target_price"] is not None
        and current_price <= float(product["target_price"])
    )

    update_product_price(
        product_id,
        current_price,
    )
    
    evaluate_predictions(product_id, current_price)

    prediction = generate_price_forecast(product_id)

    return {
        "product_id": product_id,
        "name": result["name"],
        "previous_price": previous_price,
        "current_price": current_price,
        "percentage_change": percentage_change,
        "price_decreased": price_decreased,
        "target_reached": target_reached,
        "prediction": prediction,
    }


def process_notifications(result):
    """
    Send email notifications based on the latest price result.

    Price-drop alerts are sent whenever the latest price is
    lower than the previous recorded price.

    Target-price alerts are sent only once while the product
    remains at or below its target price.
    """

    product = get_product(
        result["product_id"]
    )

    settings = get_notification_settings()

    if not product or not settings:
        return

    recipient = settings["email"]

    if not recipient:
        return

    # --------------------------------------------------
    # PRICE DROP ALERT
    # --------------------------------------------------

    if (
        result["price_decreased"]
        and settings["price_drop_enabled"]
        and result["previous_price"] is not None
    ):

        send_price_drop_alert(
            product_name=result["name"],
            product_url=product["url"],
            previous_price=result["previous_price"],
            current_price=result["current_price"],
            percentage_change=result["percentage_change"],
            recipient=recipient,
        )

    # --------------------------------------------------
    # TARGET PRICE ALERT
    # --------------------------------------------------

    if (
        result["target_reached"]
        and settings["target_alert_enabled"]
        and not product["target_alert_sent"]
    ):

        send_target_price_alert(
            product_name=result["name"],
            product_url=product["url"],
            current_price=result["current_price"],
            target_price=product["target_price"],
            recipient=recipient,
        )

        mark_target_alert_sent(
            product["id"]
        )
    # --------------------------------------------------
    # AI PREDICTION ALERT
    # --------------------------------------------------

    if (
        "prediction_enabled" in settings.keys() and settings["prediction_enabled"]
        and result.get("prediction") is not None
    ):
        pred = result["prediction"]
        
        # Check thresholds
        if (
            pred["decrease_probability"] >= settings["prediction_alert_probability"]
            and pred["expected_discount_percent"] >= settings["prediction_min_discount"]
        ):
            # Send prediction alert
            # To avoid spam on every check, let's only send if the price just decreased
            if result["price_decreased"]:
                send_price_prediction_alert(
                    product_name=result["name"],
                    product_url=product["url"],
                    current_price=result["current_price"],
                    prediction=pred,
                    recipient=recipient,
                )
