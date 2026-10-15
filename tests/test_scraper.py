from decimal import Decimal

from bs4 import BeautifulSoup

from scraper import (
    extract_product_name,
    extract_price,
)


def test_product_extraction():

    html = """
    <html>

        <head>
            <title>Test Laptop</title>
        </head>

        <body>

            <h1>Test Laptop</h1>

            <div class="price">
                ₹54,999
            </div>

        </body>

    </html>
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    name = extract_product_name(
        soup
    )

    price = extract_price(
        soup
    )

    assert name == "Test Laptop"

    assert price == Decimal(
        "54999"
    )