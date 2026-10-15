"""Downloadable price report (PDF or plain text).

The PDF is written by a tiny built-in writer so the feature works with the
project's existing dependencies. It uses the standard Helvetica fonts, which
have no rupee glyph, so amounts appear as "Rs." in the PDF.

The report contains only the product name, prices and analysis results.
It never includes e-mail addresses, settings, URLs or credentials.
"""

from __future__ import annotations

from datetime import datetime

from deal_analyzer import ProductAnalysis, fmt_money, fmt_pct

DISCLAIMER = (
    "Estimates are statistical, based on the price checks recorded by this "
    "application. They are not guarantees of future prices."
)


def _money(value):
    return fmt_money(value) if value is not None else "Not available"


def build_sections(analysis: ProductAnalysis, generated_at=None):
    """Return [(heading, [(label, value), ...]), ...] for the report."""

    generated_at = generated_at or datetime.now()
    stats = analysis.stats
    advice = analysis.advice
    score = analysis.score

    product = [
        ("Product", analysis.name),
        ("Current Price", _money(analysis.current)),
        ("Target Price", _money(analysis.target) if analysis.target else "Not set"),
    ]

    history = []
    if stats and stats.count >= 2:
        history = [
            ("Historical Lowest", _money(stats.low)),
            ("Historical Highest", _money(stats.high)),
            ("Historical Average", _money(stats.avg)),
            ("Price Checks Recorded", str(stats.count)),
            ("Price Trend", analysis.insights.trend),
            ("Price Drops / Increases", f"{stats.drops} / {stats.rises}"),
        ]
    else:
        history = [("Historical Data", "Not enough data")]

    assessment = [
        ("Deal Score",
         f"{score.score} / 100 ({score.label})" if score.score is not None else "Not enough data"),
        ("AI-assisted Recommendation", advice.label.upper() if advice.verdict != "NO_DATA"
         else "Not enough data"),
    ]
    if advice.confidence is not None:
        assessment.append(("Signal Confidence", f"{advice.confidence}%"))
    if advice.expected_price is not None:
        assessment.append(("Expected Price", _money(advice.expected_price)))
        assessment.append(("Potential Saving", _money(advice.expected_saving)))
    if analysis.volatility.available:
        assessment.append(("Price Volatility",
                           f"{analysis.volatility.level} ({analysis.volatility.score} / 100)"))

    savings = analysis.savings
    if savings.available:
        word = "below" if savings.vs_avg_pct >= 0 else "above"
        assessment.append((
            "Versus Historical Average",
            f"{fmt_pct(savings.vs_avg_pct)} {word} average "
            f"({_money(abs(savings.vs_avg_amount))})",
        ))

    best = analysis.best_time
    timing = []
    if best.available:
        timing = [
            ("Timing Recommendation", best.recommendation),
            ("Typical Discount During Drops", best.discount_range),
            ("Typical Saving", best.saving_range),
            ("Confidence", best.confidence),
        ]
    else:
        timing = [("Best Time to Buy", "Not enough historical observations")]

    meta = [("Report Generated", generated_at.strftime("%d %b %Y, %I:%M %p"))]

    return [
        ("Product", product),
        ("Price History", history),
        ("Assessment", assessment),
        ("Best Time to Buy", timing),
        ("About This Report", meta),
    ]


def build_text_report(analysis: ProductAnalysis, generated_at=None):
    lines = ["E-COMMERCE PRICE REPORT", "=" * 23, ""]

    for heading, rows in build_sections(analysis, generated_at):
        lines.append(heading.upper())
        for label, value in rows:
            lines.append(f"{label}:")
            lines.append(f"  {value}")
        lines.append("")

    lines.append(DISCLAIMER)

    return "\n".join(lines) + "\n"


# --------------------------------------------------
# MINIMAL PDF WRITER (text only)
# --------------------------------------------------

_PAGE_W, _PAGE_H = 595, 842
_MARGIN = 56


def _pdf_text(value):
    """Latin-1 safe text for the built-in fonts, escaped for a PDF string."""

    text = str(value).replace("\u20b9", "Rs. ").replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u2212", "-").replace("\u2019", "'")
    text = text.encode("latin-1", "ignore").decode("latin-1")

    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap(text, width_chars):
    words = str(text).split()
    lines, line = [], ""

    for word in words:
        candidate = f"{line} {word}".strip()
        if len(candidate) <= width_chars:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word

    if line:
        lines.append(line)

    return lines or [""]


def build_pdf_report(analysis: ProductAnalysis, generated_at=None) -> bytes:
    """Return the report as PDF bytes."""

    # ---- lay the content out as drawing commands, paginating as needed ----
    pages, cmds, y = [], [], _PAGE_H - _MARGIN

    def new_page():
        nonlocal cmds, y
        if cmds:
            pages.append(cmds)
        cmds, y = [], _PAGE_H - _MARGIN

    def text(x, size, font, value, gray=0.1):
        nonlocal y
        cmds.append(f"{gray} g BT /{font} {size} Tf {x} {y:.1f} Td ({_pdf_text(value)}) Tj ET")

    def advance(amount):
        nonlocal y
        y -= amount
        if y < _MARGIN + 30:
            new_page()

    # Title band
    cmds.append(f"0.26 0.22 0.79 rg {_MARGIN} {y - 8:.1f} {_PAGE_W - 2 * _MARGIN} 3 re f")
    text(_MARGIN, 20, "F2", "E-COMMERCE PRICE REPORT", 0.09)
    advance(34)

    for heading, rows in build_sections(analysis, generated_at):
        advance(8)
        text(_MARGIN, 12, "F2", heading.upper(), 0.26)
        advance(18)
        for label, value in rows:
            wrapped = _wrap(value, 52)
            text(_MARGIN, 10, "F1", label, 0.4)
            for index, piece in enumerate(wrapped):
                text(_MARGIN + 190, 10, "F2" if index == 0 else "F1", piece, 0.1)
                if index < len(wrapped) - 1:
                    advance(14)
            advance(18)

    advance(10)
    for piece in _wrap(DISCLAIMER, 95):
        text(_MARGIN, 8.5, "F1", piece, 0.45)
        advance(12)

    pages.append(cmds)

    # ---- serialise: catalog, pages tree, fonts, then page + stream pairs ----
    objects = []  # index i holds object number i + 1

    def add(body):
        objects.append(body)
        return len(objects)

    catalog = add(None)
    pages_obj = add(None)
    font_regular = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    font_bold = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")

    kids = []
    for page_cmds in pages:
        stream = "\n".join(page_cmds).encode("latin-1", "replace")
        content = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        page = add(
            f"<< /Type /Page /Parent {pages_obj} 0 R "
            f"/MediaBox [0 0 {_PAGE_W} {_PAGE_H}] "
            f"/Resources << /Font << /F1 {font_regular} 0 R /F2 {font_bold} 0 R >> >> "
            f"/Contents {content} 0 R >>"
        )
        kids.append(page)

    objects[catalog - 1] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>"
    objects[pages_obj - 1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>"
    )

    out = bytearray(b"%PDF-1.4\n")
    offsets = []

    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        data = body if isinstance(body, bytes) else body.encode("latin-1")
        out += f"{number} 0 obj\n".encode() + data + b"\nendobj\n"

    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode()

    return bytes(out)
