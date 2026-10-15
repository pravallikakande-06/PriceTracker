"""Tests for the downloadable price report."""

from datetime import datetime, timedelta

from deal_analyzer import analyze_product
from report import build_pdf_report, build_text_report

NOW = datetime(2026, 10, 4, 12, 0, 0)


def make_analysis(prices, target=30000):
    start = NOW - timedelta(days=len(prices))
    hist = [{"checked_at": (start + timedelta(days=i)).isoformat(sep=" "), "price": p}
            for i, p in enumerate(prices)]
    return analyze_product("Sony WH-1000XM5", prices[-1], target, hist, None, 3600, now=NOW)


def test_text_report_has_the_required_fields():
    text = build_text_report(make_analysis([34000, 32000, 31000, 29999]), NOW)
    for expected in ("E-COMMERCE PRICE REPORT", "Sony WH-1000XM5", "Current Price",
                     "Historical Lowest", "Historical Average", "Target Price",
                     "Deal Score", "Price Trend", "Report Generated"):
        assert expected in text
    assert "₹29,999" in text


def test_report_shows_not_enough_data_instead_of_inventing_values():
    text = build_text_report(make_analysis([30000]), NOW)
    assert "Not enough data" in text
    assert "Deal Score" in text


def test_report_never_contains_secrets_or_urls():
    text = build_text_report(make_analysis([34000, 32000, 31000, 29999]), NOW).lower()
    for forbidden in ("http", "password", "smtp", "@"):
        assert forbidden not in text


def test_pdf_is_a_valid_pdf_with_the_content():
    pdf = build_pdf_report(make_analysis([34000, 32000, 31000, 29999]), NOW)
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    assert b"Sony WH-1000XM5" in pdf
    try:
        from io import BytesIO
        from pypdf import PdfReader
    except ImportError:
        return
    reader = PdfReader(BytesIO(pdf))
    text = "".join(page.extract_text() for page in reader.pages)
    assert "PRICE REPORT" in text and "Rs. 29,999" in text


def test_pdf_handles_odd_product_names():
    a = make_analysis([34000, 32000, 31000, 29999])
    a = a.__class__(**{**a.__dict__, "name": "Phone (128GB) \\ café ₹ 😀"})
    assert build_pdf_report(a, NOW).startswith(b"%PDF")
