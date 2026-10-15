import re
from decimal import Decimal, InvalidOperation

import requests
import cloudscraper
from bs4 import BeautifulSoup


class ScraperError(Exception):
    """Custom exception for scraping-related errors."""
    pass


def validate_url(url):
    """Validate that the URL uses HTTP or HTTPS."""
    if not url or not isinstance(url, str):
        raise ScraperError("URL is required.")

    if not url.startswith(("http://", "https://")):
        raise ScraperError("URL must start with http:// or https://.")


def fetch_page(url):
    """Fetch a webpage and return a BeautifulSoup object."""
    validate_url(url)

    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "desktop": True
        }
    )

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }

    html = ""
    try:
        response = scraper.get(
            url,
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        html = response.text
    except Exception as exc:
        # If it's a 403 or 401, fallback to playwright
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
                page.goto(url, timeout=30000)
                page.wait_for_timeout(3000)  # Wait for JS to load
                html = page.content()
                browser.close()
        except ImportError:
            if "403" in str(exc) or "Forbidden" in str(exc) or "401" in str(exc):
                raise ScraperError(
                    f"Could not access the website (403 Forbidden). "
                    f"The website actively blocks automated requests. "
                    f"Please install playwright to bypass this: pip install playwright && playwright install chromium"
                )
            raise ScraperError(
                f"Could not access the website: {exc}"
            )
        except Exception as pw_exc:
            raise ScraperError(
                f"Could not access the website even with Playwright: {pw_exc}"
            )

    return BeautifulSoup(html, "lxml")


def extract_product_name(soup):
    """Extract the product name from common HTML locations."""

    # Amazon
    element = soup.select_one('#productTitle')
    if element:
        text = element.get_text(" ", strip=True)
        if text:
            return text
            
    # Flipkart
    element = soup.select_one('span.B_NuCI')
    if element:
        text = element.get_text(" ", strip=True)
        if text:
            return text

    # OpenGraph title
    element = soup.select_one('meta[property="og:title"]')

    if element:
        content = element.get("content")

        if content:
            return content.strip()

    # Twitter title
    element = soup.select_one('meta[name="twitter:title"]')

    if element:
        content = element.get("content")

        if content:
            return content.strip()

    # Product itemprop
    element = soup.select_one('[itemprop="name"]')

    if element:
        text = element.get_text(" ", strip=True)

        if text:
            return text

    # H1
    element = soup.find("h1")

    if element:
        text = element.get_text(" ", strip=True)

        if text:
            return text

    # Title
    if soup.title:
        title = soup.title.get_text(" ", strip=True)

        if title:
            return title

    return None


def clean_price(price_text):
    """
    Convert a price string such as:

        ₹54,999
        ₹54,999.00
        $1,299.99
        EUR 999.50

    into a Decimal.
    """

    if not price_text:
        return None

    text = str(price_text).strip()

    # Remove currency symbols and letters.
    text = re.sub(r"[^\d.,]", "", text)

    if not text:
        return None

    # Handle numbers such as:
    # 54,999
    # 54,999.99
    # 54.999,99
    # 54999.99

    if "," in text and "." in text:
        # Whichever separator occurs last is assumed
        # to be the decimal separator.
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "")
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")

    elif "," in text:
        parts = text.split(",")

        # 54,999 -> 54999
        if len(parts[-1]) == 3:
            text = "".join(parts)

        # 999,99 -> 999.99
        else:
            text = ".".join(parts)

    elif text.count(".") > 1:
        # Example: 54.999.00
        parts = text.split(".")

        if len(parts[-1]) == 2:
            text = "".join(parts[:-1]) + "." + parts[-1]
        else:
            text = "".join(parts)

    try:
        value = Decimal(text)

        if value <= 0:
            return None

        return value

    except InvalidOperation:
        return None


def extract_price_from_element(element):
    """Try to extract a price from one HTML element."""

    # Meta tags usually store the price in content=""
    if element.name == "meta":
        values = [
            element.get("content"),
            element.get("value"),
        ]
    else:
        values = [
            element.get_text(" ", strip=True),
            element.get("content"),
            element.get("value"),
            element.get("data-price"),
            element.get("data-price-amount"),
        ]

    for value in values:
        if not value:
            continue

        price = clean_price(value)

        if price is not None:
            return price

    return None


def extract_price(soup):
    """
    Extract product price using multiple common
    e-commerce HTML patterns.
    """

    # --------------------------------------------------
    # 1. Schema.org / structured data
    # --------------------------------------------------

    structured_selectors = [
        '[itemprop="price"]',
        '[itemprop="lowPrice"]',
        '[itemprop="highPrice"]',
    ]

    for selector in structured_selectors:
        elements = soup.select(selector)

        for element in elements:
            price = extract_price_from_element(element)

            if price is not None:
                return price

    # --------------------------------------------------
    # 2. Meta tags
    # --------------------------------------------------

    meta_selectors = [
        'meta[property="product:price:amount"]',
        'meta[property="og:price:amount"]',
        'meta[itemprop="price"]',
        'meta[name="price"]',
        'meta[name="product-price"]',
        'meta[property="product:price"]',
    ]

    for selector in meta_selectors:
        element = soup.select_one(selector)

        if element:
            price = extract_price_from_element(element)

            if price is not None:
                return price

    # --------------------------------------------------
    # 3. Common price classes / IDs
    # --------------------------------------------------

    price_selectors = [
        ".a-price-whole",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        ".a-offscreen",
        "._30jeq3",
        ".Nx9bqj",
        ".CxhGGd",
        "._1vC4OE",
        "div._30jeq3._16Jk6d",
        "div.Nx9bqj.CxhGGd",

        ".price",
        ".product-price",
        ".sale-price",
        ".current-price",
        ".final-price",
        ".selling-price",
        ".offer-price",
        ".discounted-price",
        ".special-price",
        ".regular-price",
        ".actual-price",
        ".mrp",
        ".product__price",
        ".product-price-value",
        ".price-current",
        ".price-value",
        "#price",
        "#product-price",
        "#current-price",
        "#sale-price",
        '[class*="price"]',
        '[id*="price"]',
    ]

    for selector in price_selectors:
        elements = soup.select(selector)

        for element in elements:
            price = extract_price_from_element(element)

            if price is not None:
                return price

    # --------------------------------------------------
    # 4. Data attributes
    # --------------------------------------------------

    data_selectors = [
        "[data-price]",
        "[data-price-amount]",
        "[data-product-price]",
        "[data-sale-price]",
        "[data-current-price]",
    ]

    for selector in data_selectors:
        elements = soup.select(selector)

        for element in elements:
            price = extract_price_from_element(element)

            if price is not None:
                return price

    # --------------------------------------------------
    # 5. JSON-LD structured data
    # --------------------------------------------------

    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )

    for script in scripts:
        if not script.string:
            continue

        text = script.string

        # Look for common JSON-LD price patterns.
        patterns = [
            r'"price"\s*:\s*"([^"]+)"',
            r'"price"\s*:\s*([0-9]+(?:[.,][0-9]+)?)',
            r'"lowPrice"\s*:\s*"([^"]+)"',
            r'"lowPrice"\s*:\s*([0-9]+(?:[.,][0-9]+)?)',
        ]

        for pattern in patterns:
            matches = re.findall(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            for match in matches:
                price = clean_price(match)

                if price is not None:
                    return price

    # --------------------------------------------------
    # 6. Search visible text for currency + price
    # --------------------------------------------------

    text = soup.get_text(" ", strip=True)

    currency_patterns = [
        r"₹\s*[\d,]+(?:\.\d{1,2})?",
        r"\$\s*[\d,]+(?:\.\d{1,2})?",
        r"€\s*[\d,.]+",
        r"£\s*[\d,.]+",
        r"INR\s*[\d,]+(?:\.\d{1,2})?",
        r"USD\s*[\d,]+(?:\.\d{1,2})?",
        r"EUR\s*[\d,.]+",
        r"GBP\s*[\d,.]+",
    ]

    for pattern in currency_patterns:
        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        for match in matches:
            price = clean_price(match)

            if price is not None:
                return price

    return None


def scrape_product(url):
    """
    Scrape a product page and return:

    {
        "name": product name,
        "price": Decimal price,
        "url": product URL
    }
    """

    validate_url(url)

    soup = fetch_page(url)

    name = extract_product_name(soup)
    price = extract_price(soup)

    if not name:
        raise ScraperError(
            "Product name could not be found."
        )

    if price is None:
        raise ScraperError(
            "Product price could not be found. "
            "The website may load its price using JavaScript "
            "or may use an unsupported page structure."
        )

    return {
        "name": name,
        "price": price,
        "url": url,
    }