import logging
import os
import time

from database import (
    initialize_database,
    get_products,
)

from tracker import (
    check_product,
    process_notifications,
)


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

CHECK_INTERVAL = int(
    os.getenv(
        "CHECK_INTERVAL",
        "3600",
    )
)


# --------------------------------------------------
# LOGGING
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "price_tracker_scheduler"
)


# --------------------------------------------------
# CHECK ALL PRODUCTS
# --------------------------------------------------

def check_all_products():
    """Check the latest price of every tracked product."""

    products = get_products()

    if not products:
        logger.info(
            "No products are currently being tracked."
        )
        return

    logger.info(
        "Checking %d tracked product(s)...",
        len(products),
    )

    for product in products:

        product_id = product["id"]
        product_name = product["name"]

        try:

            logger.info(
                "Checking: %s",
                product_name,
            )

            result = check_product(
                product_id
            )

            logger.info(
                "Current price: ₹%.2f",
                result["current_price"],
            )

            if result["previous_price"] is not None:

                logger.info(
                    "Previous price: ₹%.2f",
                    result["previous_price"],
                )

                if result["price_decreased"]:

                    logger.info(
                        "Price decreased by %.2f%%",
                        abs(
                            result[
                                "percentage_change"
                            ]
                        ),
                    )

                elif (
                    result["percentage_change"]
                    > 0
                ):

                    logger.info(
                        "Price increased by %.2f%%",
                        result[
                            "percentage_change"
                        ],
                    )

                else:

                    logger.info(
                        "Price did not change."
                    )

            if result["target_reached"]:

                logger.info(
                    "Target price reached for: %s",
                    product_name,
                )

            # Send configured email notifications.
            process_notifications(
                result
            )

            logger.info(
                "Finished: %s",
                product_name,
            )

        except Exception as exc:

            logger.exception(
                "Failed to check '%s': %s",
                product_name,
                exc,
            )


# --------------------------------------------------
# MAIN SCHEDULER
# --------------------------------------------------

def run_scheduler():
    """Run the price-checking scheduler continuously."""

    initialize_database()

    logger.info(
        "========================================"
    )

    logger.info(
        "E-Commerce Price Tracker Scheduler"
    )

    logger.info(
        "========================================"
    )

    logger.info(
        "Check interval: %d seconds",
        CHECK_INTERVAL,
    )

    logger.info(
        "Check interval: %.2f minutes",
        CHECK_INTERVAL / 60,
    )

    logger.info(
        "Scheduler started."
    )

    while True:

        try:

            start_time = time.time()

            check_all_products()

            elapsed_time = (
                time.time()
                - start_time
            )

            sleep_time = max(
                0,
                CHECK_INTERVAL - elapsed_time,
            )

            logger.info(
                "Next check in %.2f minutes.",
                sleep_time / 60,
            )

            time.sleep(
                sleep_time
            )

        except KeyboardInterrupt:

            logger.info(
                "Scheduler stopped by user."
            )

            break

        except Exception as exc:

            logger.exception(
                "Unexpected scheduler error: %s",
                exc,
            )

            logger.info(
                "Retrying in 60 seconds."
            )

            time.sleep(60)


# --------------------------------------------------
# APPLICATION ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    run_scheduler()