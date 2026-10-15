"""Streamlit panels for the per-product intelligence tabs.

Thin glue: each function renders analysis results that `deal_analyzer`
already computed. The only writes are the comparison-link actions, which go
through `price_comparison`, and the wishlist toggle, which goes through
`database.set_wishlist`.
"""

import streamlit as st

import price_comparison
from database import set_wishlist
from report import build_pdf_report
from scraper import ScraperError
from ui import components as ui
from ui import insight_components as ic
from ui.models import time_ago


def alert_level_message(analysis):
    """Smart alert card shown after a manual price check."""

    alert = analysis.alert
    a = analysis

    if alert.level == 0:
        return

    savings = a.savings
    avg_saving = savings.vs_avg_amount if savings.available and savings.vs_avg_amount > 0 else None

    if alert.key == "target_reached":
        body = (f"{a.name}. Your target: {ic.fmt_money(a.target)}. "
                f"Current price: {ic.fmt_money(a.current)}.")
        if avg_saving:
            body += f" You can save {ic.fmt_money(avg_saving)} compared with the historical average."
        ui.show_alert("good", "🎯 TARGET REACHED", body)
    elif alert.key == "target_near":
        ui.show_alert("warn", "TARGET NEAR",
                      f"{a.name} is {ic.fmt_money(a.current - a.target)} above your target "
                      f"of {ic.fmt_money(a.target)}.")
    elif alert.key == "good_deal":
        ui.show_alert("good", "GOOD DEAL",
                      f"{a.name} has a deal score of {a.score.score}/100 ({a.score.label}).")
    else:
        ui.show_alert("info", "PRICE CHANGED",
                      f"{a.name} changed from {ic.fmt_money(a.previous_price)} "
                      f"to {ic.fmt_money(a.current)}.")


def wishlist_button(pid, in_wishlist):
    def toggle():
        set_wishlist(pid, not in_wishlist)

    label = "❤️ In wishlist" if in_wishlist else "🤍 Add to wishlist"
    st.button(label, key=f"wish_{pid}", on_click=toggle)


def history_extras(analysis):
    """Insights and timeline shown under the price chart."""

    ui.render(ic.insights_html(analysis.insights))

    with st.expander("📅 Price timeline"):
        ui.render(ic.timeline_html(analysis.timeline))


def savings_tab(analysis):
    ui.render(ic.savings_html(analysis.savings))
    ui.render(ic.target_progress_html(analysis.savings))

    with st.expander("How is the deal score calculated?"):
        ui.render(ic.score_breakdown_html(analysis.score))


def timing_tab(analysis):
    ui.render(ic.best_time_html(analysis.best_time))
    ui.render(ic.volatility_html(analysis.volatility))


def compare_tab(pid, analysis, own_url):
    own_store = price_comparison.store_label(own_url)
    offers = price_comparison.list_offers(pid)
    comparison = price_comparison.build_comparison(own_store, analysis.current, offers)

    if comparison:
        ui.render(ic.comparison_html(comparison))
    else:
        ui.render(ic._na("No other stores added yet. Add a link to the same product on another store to compare."))

    ui.render(ui.group_title_html("Add a store link"))
    url = st.text_input("Product link on another store", key=f"cmp_url_{pid}",
                        placeholder="https://other-store.example/product")

    if st.button("➕ Add to comparison", key=f"cmp_add_{pid}"):
        if not url.strip():
            ui.show_alert("bad", "Please paste a product link.")
        else:
            try:
                with st.spinner("Reading the product page..."):
                    price_comparison.add_offer(pid, url)
                st.rerun()
            except ScraperError as exc:
                ui.show_alert("bad", "Unable to read that page", str(exc))
            except Exception as exc:
                ui.show_alert("bad", "Could not add the link", str(exc))

    for offer in offers:
        name = (offer.get("name") or "")[:60]
        left, refresh, remove = st.columns([4, 1, 1])
        left.caption(f"**{offer['store']}** · {name}")
        if refresh.button("🔄", key=f"cmp_ref_{offer['id']}", help="Refresh this price"):
            try:
                price_comparison.refresh_offer(offer)
                st.rerun()
            except ScraperError as exc:
                ui.show_alert("bad", "Unable to refresh", str(exc))
        if remove.button("🗑️", key=f"cmp_del_{offer['id']}", help="Remove this link"):
            price_comparison.remove_offer(offer["id"])
            st.rerun()

    st.caption(
        "Only pages the scraper can read are supported, and you choose which links count as "
        "the same product. Comparison prices are fetched when you add or refresh a link; they "
        "do not affect price history, predictions or alerts."
    )


def tracking_tab(pid, analysis):
    health = analysis.health
    ui.render(ic.health_html(health, time_ago(health.last_checked)))

    ui.render(ui.group_title_html("Price report"))
    try:
        pdf = build_pdf_report(analysis)
    except Exception as exc:  # never let the report break the page
        ui.show_alert("bad", "Report could not be generated", str(exc))
        return

    safe = "".join(c if c.isalnum() else "_" for c in analysis.name)[:40].strip("_") or "product"
    st.download_button("📄 Generate Price Report (PDF)", data=pdf,
                       file_name=f"price_report_{safe}.pdf", mime="application/pdf",
                       key=f"report_{pid}")
