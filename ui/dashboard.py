"""Dashboard page: layout plus user actions.

All data access goes through the existing backend functions
(database.py, scraper.py, tracker.py). This module only decides how
results are presented.
"""

from datetime import datetime

import streamlit as st

from database import (
    add_product,
    get_notification_settings,
    get_price_history,
    get_products,
    update_notification_settings,
)
from scraper import scrape_product
from tracker import check_product, process_notifications

from ui import components as ui
from ui.charts import build_price_chart
from ui.models import (
    SORT_OPTIONS,
    FriendlyError,
    build_product_view,
    check_interval_seconds,
    explain_error,
    filter_products,
    format_money,
    format_pct,
    is_valid_email,
    latest_check,
    notification_status,
    smtp_configured,
    sort_products,
    summarize,
)
from scraper import ScraperError


# --------------------------------------------------
# DATA
# --------------------------------------------------

def _load_views():
    """Build one ProductView per tracked product."""

    return [
        build_product_view(product, get_price_history(product["id"]))
        for product in get_products()
    ]


def _error_state(error: FriendlyError, **extra):
    """Convert a FriendlyError into a session-state friendly dict."""

    return {
        "title": error.title,
        "body": error.body,
        "detail": error.detail,
        **extra,
    }


def _show_technical_details(detail):
    """Keep raw error text available without shouting it."""

    if detail:
        with st.expander("Technical details"):
            st.code(detail, language=None)


# --------------------------------------------------
# ADD PRODUCT
# --------------------------------------------------

def _attempt_add(url, target_price):
    """Scrape and store a product. Returns True on success."""

    st.session_state.pop("add_error", None)

    if not url:
        error = explain_error(ScraperError("URL is required."))
        st.session_state["add_error"] = _error_state(error, retry=False)
        return False

    try:
        with st.spinner("Fetching product details…"):
            result = scrape_product(url)
            target = target_price if target_price > 0 else None

            add_product(
                url=result["url"],
                name=result["name"],
                price=float(result["price"]),
                target_price=target,
            )
    except Exception as exc:  # noqa: BLE001 - shown to the user
        st.session_state["add_error"] = _error_state(
            explain_error(exc), url=url, target=target_price, retry=True
        )
        return False

    price = float(result["price"])

    st.session_state["add_success"] = {
        "name": result["name"],
        "price": price,
        "target": target,
    }
    st.session_state["flash_toast"] = (
        f"Now tracking {result['name']}",
        ":material/check_circle:",
    )
    # A new widget key gives the next render empty inputs.
    st.session_state["add_nonce"] = st.session_state.get("add_nonce", 0) + 1

    return True


def _render_add_feedback():
    """Show the one-time success banner or the persistent error panel."""

    success = st.session_state.pop("add_success", None)

    if success:
        detail = f"Current price {format_money(success['price'])}"

        if success["target"] is not None:
            detail += f" · Target {format_money(success['target'])}"

        ui.render(ui.alert_html("good", f"Now tracking {success['name']}", detail))

    error = st.session_state.get("add_error")

    if not error:
        return

    ui.render(ui.alert_html("bad", error["title"], error["body"]))
    _show_technical_details(error["detail"])

    if error.get("retry") and st.button(
        "Try again", key="add_retry", icon=":material/refresh:"
    ):
        _attempt_add(error["url"], error["target"])
        st.rerun()


def _render_add_section():
    ui.render(
        ui.section_heading(
            "Track a new product",
            "Paste a product link. A target price is optional.",
            anchor="track-product",
        )
    )

    # Inputs are keyed by a counter that increases after each successful
    # add, which resets them without wiping the URL after a failed add.
    nonce = st.session_state.get("add_nonce", 0)

    with st.container(border=True, key="panel_add"):
        with st.form("add_product_form"):
            url = st.text_input(
                "Product URL",
                placeholder="https://example.com/product",
                key=f"add_url_{nonce}",
            )

            left, _gap, right = st.columns([2, 3, 2], vertical_alignment="bottom")

            with left:
                target_price = st.number_input(
                    "Target price in ₹ (optional)",
                    min_value=0.0,
                    value=0.0,
                    step=100.0,
                    key=f"add_target_{nonce}",
                    help=(
                        "You'll get an email when the price reaches or "
                        "drops below this. Leave at 0 to skip."
                    ),
                )

            with right:
                submitted = st.form_submit_button(
                    "Track product",
                    type="primary",
                    icon=":material/add:",
                    width="stretch",
                )

        if submitted and _attempt_add(url.strip(), target_price):
            st.rerun()

        _render_add_feedback()


# --------------------------------------------------
# PRODUCT CARDS
# --------------------------------------------------

def _check_message(before, result):
    """Toast text for a manual check, based on the real price change."""

    after = float(result["current_price"])
    diff = after - before

    if abs(diff) < 0.005:
        text, icon = f"No change. Still {format_money(after)}.", ":material/trending_flat:"
    elif diff < 0:
        pct = format_pct(abs(diff) / before * 100)
        text = (
            f"Price dropped {pct} to {format_money(after)}. "
            f"You saved {format_money(-diff)}."
        )
        icon = ":material/trending_down:"
    else:
        pct = format_pct(diff / before * 100)
        text = f"Price increased {pct} to {format_money(after)}."
        icon = ":material/trending_up:"

    if result["target_reached"]:
        text += " Target price reached."

    return text, icon


def _check_price(view):
    """Run the existing check + notification flow for one product."""

    notices = st.session_state.setdefault("card_notices", {})
    notices.pop(view.id, None)

    result = None

    try:
        with st.spinner("Checking the latest price…"):
            result = check_product(view.id)
    except Exception as exc:  # noqa: BLE001 - shown to the user
        notices[view.id] = _error_state(explain_error(exc), kind="bad")

    if result is not None:
        try:
            with st.spinner("Sending alerts…"):
                process_notifications(result)
        except Exception as exc:  # noqa: BLE001 - shown to the user
            # The price is already saved; only the email failed.
            error = explain_error(exc)
            notices[view.id] = _error_state(
                FriendlyError(
                    "Price updated, but the alert email wasn't sent",
                    f"{error.title}. {error.body}",
                    error.detail,
                ),
                kind="warn",
            )

        st.session_state["flash_toast"] = _check_message(view.current, result)

    st.rerun()


def _render_card(view):
    spine = ui.card_status(view)[0]

    with st.container(border=True, key=f"card_{spine}_{view.id}"):
        left, right = st.columns([5, 6], gap="large")

        with left:
            ui.render(
                ui.card_head_html(view)
                + ui.card_stats_html(view)
                + ui.target_strip_html(view)
                + ui.trend_strip_html(view)
            )

            notice = st.session_state.get("card_notices", {}).get(view.id)

            if notice:
                ui.render(ui.alert_html(notice["kind"], notice["title"], notice["body"]))
                _show_technical_details(notice["detail"])

            ui.render(ui.checked_html(view))

            check_col, view_col = st.columns(2)

            with check_col:
                clicked = st.button(
                    "Check price",
                    key=f"check_{view.id}",
                    icon=":material/refresh:",
                    help=f"Check the latest price of {view.name}",
                    width="stretch",
                )

            with view_col:
                st.link_button(
                    "View product",
                    view.url,
                    icon=":material/open_in_new:",
                    help=f"Open {view.name} in a new tab",
                    width="stretch",
                )

        with right:
            ui.render(ui.chart_head_html(view))

            if view.history.empty:
                ui.render('<div class="pt-hint">No price history yet.</div>')
            else:
                figure = build_price_chart(
                    view.history, view.current, view.lowest, view.target
                )
                st.plotly_chart(
                    figure,
                    width="stretch",
                    theme=None,
                    key=f"chart_{view.id}",
                    config={"displayModeBar": False},
                )

                if len(view.history) < 2:
                    ui.render(
                        '<div class="pt-hint">Only one price so far. '
                        "Check again later to build a trend.</div>"
                    )

        if clicked:
            _check_price(view)


def _render_products(views):
    meta = f"{len(views)} tracked" if views else ""
    ui.render(ui.section_heading("Your products", meta))

    if not views:
        ui.render(ui.empty_state_html())
        return

    search_col, sort_col = st.columns([3, 1.4])

    with search_col:
        query = st.text_input(
            "Search tracked products",
            placeholder="Search tracked products...",
            label_visibility="collapsed",
            key="search_query",
        )

    with sort_col:
        sort_option = st.selectbox(
            "Sort products",
            SORT_OPTIONS,
            format_func=lambda option: f"Sort by: {option}",
            label_visibility="collapsed",
            key="sort_option",
        )

    shown = sort_products(filter_products(views, query), sort_option)

    if not shown:
        ui.render(ui.no_results_html(query.strip()))
        return

    if len(shown) != len(views):
        ui.render(
            f'<div class="pt-hint">Showing {len(shown)} of {len(views)} products</div>'
        )

    for view in shown:
        _render_card(view)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

def _save_settings(email, price_drop, target_alert):
    """Validate and persist the notification settings."""

    email = email.strip()

    if email and not is_valid_email(email):
        ui.render(
            ui.alert_html(
                "bad",
                "That email address doesn't look right",
                "Use the format name@example.com.",
            )
        )
        return

    try:
        with st.spinner("Saving settings…"):
            update_notification_settings(
                email=email,
                price_drop_enabled=price_drop,
                target_alert_enabled=target_alert,
            )
    except Exception as exc:  # noqa: BLE001 - shown to the user
        error = explain_error(exc)
        ui.render(ui.alert_html("bad", "Settings weren't saved", error.body))
        _show_technical_details(error.detail)
        return

    st.session_state["flash_toast"] = (
        "Notification settings saved",
        ":material/check_circle:",
    )
    st.rerun()


def _render_sidebar(status, interval, last_check, has_products):
    with st.sidebar:
        ui.render(ui.side_title("bell", "Notifications"))
        ui.render(ui.notification_card_html(status, smtp_configured()))

        with st.form("notification_settings", border=False):
            email = st.text_input(
                "Notification email",
                value=status.email,
                placeholder="email@example.com",
            )
            price_drop = st.checkbox("Price drop alerts", value=status.price_drop)
            target_alert = st.checkbox("Target price alerts", value=status.target_alert)
            saved = st.form_submit_button(
                "Save settings",
                type="primary",
                icon=":material/save:",
                width="stretch",
            )

        if saved:
            _save_settings(email, price_drop, target_alert)

        st.divider()
        ui.render(ui.side_title("clock", "Automatic monitoring"))

        stale = bool(
            has_products
            and last_check
            and (datetime.now() - last_check).total_seconds() > 2 * interval
        )
        ui.render(ui.scheduler_card_html(interval, last_check, stale))
        ui.render(
            '<div class="pt-side-muted" style="margin-top:.5rem">'
            "Start it in a separate terminal with "
            "<code>python scheduler.py</code>.</div>"
        )

        st.divider()
        ui.render(
            '<div class="pt-side-muted"><b>E-Commerce Price Tracker</b><br>'
            "Prices are stored locally in SQLite. Amounts are shown in ₹.</div>"
        )


# --------------------------------------------------
# PAGE
# --------------------------------------------------

def render_dashboard():
    """Render the full dashboard."""

    flash = st.session_state.pop("flash_toast", None)

    if flash:
        st.toast(flash[0], icon=flash[1])

    status = notification_status(get_notification_settings())
    interval = check_interval_seconds()
    views = _load_views()

    _render_sidebar(status, interval, latest_check(views), bool(views))

    ui.render(ui.header_html(interval, status))
    ui.render(ui.metrics_html(summarize(views)))

    _render_add_section()
    _render_products(views)

    ui.render(ui.footer_html())