import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

from database import (
    initialize_database,
    add_product,
    get_products,
    get_price_history,
    get_notification_settings,
    update_notification_settings,
    get_latest_prediction,
    get_prediction_evaluation_metrics,
)

from scraper import scrape_product, ScraperError
from tracker import check_product, process_notifications
from prediction import generate_price_forecast

# UI-only imports (styling and HTML builders; no backend access).
from ui import components as ui
from ui.charts import style_price_figure
from ui.styles import inject_styles
from ui.models import (
    check_interval_seconds,
    compute_price_change,
    compute_target_status,
    history_to_frame,
    notification_status,
)
from types import SimpleNamespace

# Price-intelligence features (pure analysis + presentation).
from deal_analyzer import analyze_product
from ui import insight_components as ic
from ui import product_panels as panels

# ==================================================
# DATABASE INITIALIZATION
# ==================================================
initialize_database()

# ==================================================
# PAGE CONFIGURATION
# ==================================================
st.set_page_config(
    page_title="E-Commerce Price Intelligence",
    page_icon="🛒",
    layout="wide",
)

inject_styles()

# ==================================================
# HEADER
# ==================================================
ui.render(ui.app_header_html(
    check_interval_seconds(),
    notification_status(get_notification_settings()),
))

# ==================================================
# GLOBAL NAVIGATION
# ==================================================
tab_dashboard, tab_products, tab_settings = st.tabs([
    "📊 Dashboard", 
    "📦 Tracked Products", 
    "⚙️ Settings"
])

# ==================================================
# DATA LOADING HELPERS
# ==================================================
def analyze_row(row):
    """Run the price-intelligence analysis for one product row.

    Reads only data the app already stores (history + latest prediction).
    """
    pid = row["id"]
    return analyze_product(
        name=row["name"],
        current=row["current_price"],
        target=row.get("target_price"),
        history_rows=get_price_history(pid),
        prediction=get_latest_prediction(pid),
        interval_seconds=check_interval_seconds(),
        manual_check_failed=st.session_state.get(f"check_failed_{pid}", False),
    )


def load_products_df():
    products = get_products()
    if products:
        return pd.DataFrame([dict(p) for p in products])
    return pd.DataFrame()

# ==================================================
# 1. DASHBOARD TAB
# ==================================================
with tab_dashboard:
    product_df = load_products_df()
    
    if product_df.empty:
        ui.render(ui.empty_state_html(
            cta=False,
            body="Open the 📦 Tracked Products tab to add your first product and start monitoring price changes.",
        ))
    else:
        # ---- A. Summary Metrics ----
        ui.render(ui.section_heading("Overview", "Your watchlist at a glance"))
        
        total_products = len(product_df)
        
        product_df["current_price"] = pd.to_numeric(product_df["current_price"], errors="coerce")
        lowest_price_overall = product_df["current_price"].min()
        avg_price_overall = product_df["current_price"].mean()
        
        if "target_price" in product_df.columns:
            target_data = product_df[product_df["target_price"].notna()].copy()
            target_data["target_price"] = pd.to_numeric(target_data["target_price"], errors="coerce")
            targets_reached = len(target_data[target_data["current_price"] <= target_data["target_price"]])
            with_target = len(target_data)
        else:
            targets_reached = 0
            with_target = 0
            
        # We also need to count total price drops and predicted drops
        total_drops = 0
        predicted_drops = 0
        recent_activity = []
        
        for idx, row in product_df.iterrows():
            pid = row['id']
            hist = get_price_history(pid)
            pred = get_latest_prediction(pid)
            if pred and dict(pred).get('decrease_probability', 0) > 0.4:
                predicted_drops += 1
            if hist and len(hist) > 1:
                hist_df = pd.DataFrame([dict(h) for h in hist])
                hist_df['price'] = pd.to_numeric(hist_df['price'])
                # Count drops
                prices = hist_df['price'].values
                for i in range(1, len(prices)):
                    if prices[i] < prices[i-1]:
                        total_drops += 1
                # Recent activity (last change)
                if len(prices) >= 2:
                    prev_p = prices[-2]
                    curr_p = prices[-1]
                    diff = curr_p - prev_p
                    pct = (diff / prev_p) * 100 if prev_p > 0 else 0
                    status = "📉 Price Decreased" if diff < 0 else ("📈 Price Increased" if diff > 0 else "➡️ No Change")
                    date = hist_df.iloc[-1]['checked_at']
                    recent_activity.append({
                        "Product": row['name'],
                        "Previous": prev_p,
                        "Current": curr_p,
                        "Change": diff,
                        "% Change": pct,
                        "Status": status,
                        "Date": date
                    })
                    
        plural = "" if total_products == 1 else "s"
        analyses = {r["id"]: analyze_row(r) for _, r in product_df.iterrows()}
        scored = [(r["name"], analyses[r["id"]]) for _, r in product_df.iterrows()
                  if analyses[r["id"]].score.score is not None]
        good_deals = sum(1 for _, a in scored if a.score.score >= 75)
        total_savings = sum(
            a.savings.vs_avg_amount for a in analyses.values()
            if a.savings.available and a.savings.vs_avg_amount > 0
        )
        ui.render(ui.kpi_grid_html([
            dict(icon="package", label="Tracked Products", value=str(total_products),
                 sub="In your watchlist", tone="accent"),
            dict(icon="down", label="Price Drops", value=str(total_drops),
                 sub="Recorded across price history", tone="good"),
            dict(icon="sparkles", label="Good Deals", value=str(good_deals),
                 sub="Deal score of 75 or more", tone="good"),
            dict(icon="tag", label="Savings", value=f"₹{total_savings:,.2f}",
                 sub="Below historical averages, combined", tone="good"),
            dict(icon="target", label="Targets Reached", value=str(targets_reached),
                 sub=f"Of {with_target} with a target price" if with_target else "No target prices set",
                 tone="warn"),
            dict(icon="bot", label="Predicted Drops", value=str(predicted_drops),
                 sub="Drop probability above 40%", tone="ai"),
            dict(icon="tag", label="Lowest Price", value=f"₹{lowest_price_overall:,.2f}",
                 sub="Across tracked products", tone="neutral"),
            dict(icon="chart", label="Average Price", value=f"₹{avg_price_overall:,.2f}",
                 sub=f"Across {total_products} product{plural}", tone="neutral"),
        ], cols=4))

        # ---- A2. Top deals, advisor, wishlist ----
        ui.render(ui.section_heading("Top Deals", "Ranked by deal score (0-100)"))
        top = sorted(scored, key=lambda item: item[1].score.score, reverse=True)[:5]
        ui.render(ic.top_deals_html(top))

        ui.render(ui.section_heading("AI-assisted Buying Advisor",
                                     "Statistical recommendation from each product's price history"))
        ui.render(ic.advisor_list_html([(r["name"], analyses[r["id"]]) for _, r in product_df.iterrows()]))

        wish_rows = [r for _, r in product_df.iterrows() if r.get("wishlist") == 1]
        if wish_rows:
            wl = [analyses[r["id"]] for r in wish_rows]
            ui.render(ui.section_heading("My Wishlist", f"{len(wl)} product{'' if len(wl) == 1 else 's'}"))
            ui.render(ic.wishlist_summary_html(
                len(wl),
                sum(1 for a in wl if a.alert.level == 4),
                sum(1 for a in wl if a.score.score is not None and a.score.score >= 75),
                sum(1 for a in wl if a.advice.verdict == "WAIT"),
            ))
        
        # ---- B. Recent Price Activity ----
        ui.render(ui.section_heading("Recent Price Activity", "Latest change per product"))
        if recent_activity:
            ui.render(ui.activity_table_html(recent_activity))
        else:
            ui.show_alert("info", "No recent price changes detected")
            
        # ---- C. AI Prediction Overview ----
        ui.render(ui.section_heading("AI Prediction Overview"))
        ui.render(ui.ai_banner_html())
        for ai_pos, (idx, row) in enumerate(product_df.iterrows()):
            pid = row['id']
            pred = get_latest_prediction(pid)
            hist = get_price_history(pid)
            
            with st.expander(f"🔮 {row['name']} - Current: ₹{row['current_price']:,.2f}", expanded=(ai_pos == 0)):
                if not hist or len(hist) < 5:
                    ui.show_alert("warn", "More historical data required",
                                  "Not enough historical data for a reliable prediction. Collect at least 10 observations.")
                else:
                    if not pred:
                        pred = generate_price_forecast(pid)
                    
                    if pred:
                        p = dict(pred)
                        ui.render(ui.prediction_cards_html(p))
                        
                        # Data Quality
                        obs = p.get('historical_observations', len(hist))
                        if obs >= 10:
                            ui.show_alert("good", f"Prediction readiness: Sufficient data ({obs} observations)")
                        else:
                            ui.show_alert("warn", f"Prediction readiness: Collecting more data ({obs} observations, need 10+)")
                    else:
                        ui.show_alert("info", "Prediction generating...")
                        
        # ---- G. Prediction Accuracy ----
        ui.render(ui.section_heading("Prediction Accuracy", "How past forecasts compared with real prices"))
        metrics = get_prediction_evaluation_metrics()
        if metrics:
            ui.render(ui.kpi_grid_html([
                dict(icon="check", label="Predictions Evaluated", value=str(metrics["total_evaluated"]),
                     sub="Forecasts checked against real prices", tone="ai"),
                dict(icon="target", label="Direction Accuracy", value=f"{metrics['direction_accuracy']:.1f}%",
                     sub="Up/down movement predicted correctly", tone="good"),
                dict(icon="chart", label="Average Error", value=f"₹{metrics['avg_error']:,.2f}",
                     sub="Average gap from the actual price", tone="accent"),
            ]))
        else:
            ui.show_alert("info", "No predictions evaluated yet",
                          "Check back when more future prices are recorded.")


# ==================================================
# 2. TRACKED PRODUCTS TAB
# ==================================================
with tab_products:
    ui.render(ui.section_heading("Track a New Product", "Paste a product link and optionally set a target price", anchor="track-product"))
    with st.container(border=True, key="panel_add"):
        with st.form("add_product_form"):
            col_url, col_target = st.columns([3, 1])
            with col_url:
                product_url = st.text_input("Product URL", placeholder="https://example.com/product")
            with col_target:
                target_price = st.number_input("Target Price (₹, optional)", min_value=0.0, value=0.0, step=100.0)
            submitted = st.form_submit_button("➕ Track Product", type="primary")
            
            if submitted:
                if not product_url.strip():
                    ui.show_alert("bad", "Please enter a product URL.")
                else:
                    try:
                        with st.spinner("Fetching product information..."):
                            result = scrape_product(product_url.strip())
                        target = target_price if target_price > 0 else None
                        add_product(
                            url=result["url"],
                            name=result["name"],
                            price=float(result["price"]),
                            target_price=target,
                        )
                        ui.show_alert("good", f"Added {result['name']} at ₹{float(result['price']):,.2f}")
                        st.rerun()
                    except ScraperError as exc:
                        ui.show_alert("bad", "Unable to access the product page", str(exc))
                    except Exception as exc:
                        ui.show_alert("bad", "Something went wrong", str(exc))

    ui.render(ui.section_heading("Product List", "Prices, history and forecasts for everything you track"))
    product_df = load_products_df()
    
    if product_df.empty:
        ui.render(ui.empty_state_html())
    else:
        for idx, row in product_df.iterrows():
            pid = row['id']
            current_price = float(row["current_price"])
            
            # Fetch history to compute actual min/avg if not in DB correctly
            hist = get_price_history(pid)
            hist_df = pd.DataFrame([dict(h) for h in hist]) if hist else pd.DataFrame()
            if not hist_df.empty:
                hist_df['price'] = pd.to_numeric(hist_df['price'])
                lowest = hist_df['price'].min()
                avg = hist_df['price'].mean()
            else:
                lowest = current_price
                avg = current_price
                
            pred = get_latest_prediction(pid)
            pred_status = dict(pred).get('status', 'N/A') if pred else "No prediction yet"
            
            # ---- presentation-only status (same data, no new queries) ----
            raw_target = row.get("target_price")
            target = float(raw_target) if pd.notna(raw_target) and raw_target else None
            clean_hist = history_to_frame(hist) if hist else None
            if clean_hist is not None and not clean_hist.empty:
                change = compute_price_change(
                    current_price,
                    clean_hist["price"].tolist(),
                    [t.to_pydatetime() for t in clean_hist["checked_at"]],
                )
            else:
                change = compute_price_change(current_price, [], [])
            view = SimpleNamespace(change=change, target_status=compute_target_status(current_price, target))
            spine, badge_kind, badge_icon, badge_text = ui.card_status(view)
            
            # ---- price-intelligence analysis (read-only) ----
            analysis = analyze_row(row)
            in_wishlist = row.get("wishlist") == 1
            flash = st.session_state.pop(f"flash_{pid}", None)
            
            with st.container(border=True, key=f"card_{spine}_{pid}"):
                ui.render(ui.product_head_html(row['name'], row['url'], badge_kind, badge_icon, badge_text))
                ui.render(ui.product_stats_html(current_price, lowest, avg, target))
                ui.render(ui.trend_strip_html(view))
                ui.render(ui.target_strip_html(view))
                ui.render(ui.ai_status_html(pred_status))
                level_badge = ic.alert_level_badge(analysis.alert)
                if level_badge:
                    ui.render(f'<div class="pt-ai-meta">{level_badge}</div>')
                ui.render(ic.intel_row_html(analysis))
                
                btn_check, btn_view, btn_wish, _spacer = st.columns([1, 1, 1, 1])
                with btn_check:
                    check_clicked = st.button("🔄 Check Latest Price", key=f"check_{pid}", type="primary")
                with btn_view:
                    st.link_button("🔗 View Product", row['url'])
                with btn_wish:
                    panels.wishlist_button(pid, in_wishlist)
                
                if check_clicked:
                    try:
                        with st.spinner("Checking latest price..."):
                            result = check_product(pid)
                            process_notifications(result)
                        st.session_state.pop(f"check_failed_{pid}", None)
                        # Keep the result so it survives the rerun below.
                        st.session_state[f"flash_{pid}"] = dict(
                            decreased=result["price_decreased"],
                            pct=result["percentage_change"],
                        )
                        st.rerun()
                    except ScraperError as exc:
                        st.session_state[f"check_failed_{pid}"] = True
                        st.session_state[f"flash_{pid}"] = dict(error="Unable to access the product page", detail=str(exc))
                        st.rerun()
                    except Exception as exc:
                        st.session_state[f"flash_{pid}"] = dict(error="Could not update price", detail=str(exc))
                        st.rerun()
                
                if flash:
                    if "error" in flash:
                        ui.show_alert("bad", flash["error"], flash["detail"])
                    else:
                        if flash["decreased"]:
                            ui.show_alert("good", f"Price decreased by {abs(flash['pct']):.2f}%")
                        elif flash["pct"] > 0:
                            ui.show_alert("warn", f"Price increased by {flash['pct']:.2f}%")
                        else:
                            ui.show_alert("info", "Price has not changed.")
                        panels.alert_level_message(analysis)
                
                tab_hist, tab_save, tab_time, tab_cmp, tab_track = st.tabs([
                    "📈 Price history", "💰 Savings", "📅 Timing", "🏪 Compare", "🩺 Tracking & report",
                ])
                with tab_save:
                    panels.savings_tab(analysis)
                with tab_time:
                    panels.timing_tab(analysis)
                with tab_cmp:
                    panels.compare_tab(pid, analysis, row['url'])
                with tab_track:
                    panels.tracking_tab(pid, analysis)
                
                # History Chart
                with tab_hist:
                  if not hist_df.empty:
                      hist_df["checked_at"] = pd.to_datetime(hist_df["checked_at"], format="mixed", errors="coerce")
                      hist_df = hist_df.dropna(subset=["checked_at", "price"])
                    
                      fig = px.line(
                          hist_df,
                          x="checked_at", y="price",
                          markers=True,
                          labels={"checked_at": "Date", "price": "Price (₹)"},
                      )
                    
                      if pred:
                          p = dict(pred)
                          last_date = hist_df['checked_at'].max()
                          forecast_date = last_date + timedelta(days=p.get('forecast_days', 14))
                        
                          fig.add_scatter(
                              x=[last_date, forecast_date],
                              y=[current_price, p['predicted_price_low']],
                              mode='lines', line=dict(dash='dash', color='green'), name='Forecast (Low)'
                          )
                          fig.add_scatter(
                              x=[last_date, forecast_date],
                              y=[current_price, p['predicted_price_high']],
                              mode='lines', line=dict(dash='dash', color='orange'), name='Forecast (High)'
                          )
                          fig.add_vrect(
                              x0=last_date, x1=forecast_date,
                              fillcolor="LightSalmon", opacity=0.1, layer="below", line_width=0,
                          )
                        
                      fig.update_layout(hovermode="x unified", height=350)
                      style_price_figure(fig, hist_df.reset_index(drop=True), current_price, lowest, target)
                      with st.container(key=f"chart_{pid}"):
                          ui.render(ui.chart_title_html("Price history & forecast", f"{len(hist_df)} checks"))
                          st.plotly_chart(fig, use_container_width=True)
                  panels.history_extras(analysis)

# ==================================================
# 3. SETTINGS TAB
# ==================================================
with tab_settings:
    set_notif, set_ai = st.tabs(["🔔 Notifications", "🤖 AI Predictions"])
    
    settings = get_notification_settings()
    if settings:
        settings = dict(settings)
        default_email = settings["email"] or ""
        default_price_drop = bool(settings["price_drop_enabled"])
        default_target_alert = bool(settings["target_alert_enabled"])
        default_pred_enabled = bool(settings.get("prediction_enabled", 0))
        default_pred_prob = float(settings.get("prediction_alert_probability", 0.7))
        default_pred_disc = float(settings.get("prediction_min_discount", 5.0))
        default_pred_window = int(settings.get("prediction_forecast_window", 14))
        default_pred_cooldown = int(settings.get("prediction_alert_cooldown", 24))
        default_pred_obs = int(settings.get("prediction_min_observations", 10))
    else:
        default_email = ""
        default_price_drop = True
        default_target_alert = True
        default_pred_enabled = False
        default_pred_prob = 0.7
        default_pred_disc = 5.0
        default_pred_window = 14
        default_pred_cooldown = 24
        default_pred_obs = 10

    with set_notif:
        with st.container(border=True, key="panel_notif"):
            ui.render(ui.panel_head_html("bell", "Notification Settings", "Choose where deal alerts are sent and which ones you want"))
            with st.form("notif_form"):
                ui.render(ui.group_title_html("Email"))
                notif_email = st.text_input("Notification Email", value=default_email)
                ui.render(ui.group_title_html("Alert types"))
                drop_enabled = st.checkbox("Enable Price Drop Alerts", value=default_price_drop)
                target_enabled = st.checkbox("Enable Target Price Alerts", value=default_target_alert)
                if st.form_submit_button("💾 Save Notification Settings", type="primary"):
                    update_notification_settings(
                        email=notif_email,
                        price_drop_enabled=drop_enabled,
                        target_alert_enabled=target_enabled,
                        prediction_enabled=default_pred_enabled,
                        prediction_alert_probability=default_pred_prob,
                        prediction_min_discount=default_pred_disc,
                        prediction_forecast_window=default_pred_window,
                        prediction_alert_cooldown=default_pred_cooldown,
                        prediction_min_observations=default_pred_obs,
                    )
                    ui.show_alert("good", "Notification settings saved!")

    with set_ai:
        with st.container(border=True, key="panel_ai"):
            ui.render(ui.panel_head_html("bot", "AI Prediction Settings", "Tune when predictions trigger alerts and how far ahead they look"))
            with st.form("ai_form"):
                ui.render(ui.group_title_html("Predictions"))
                pred_enabled = st.checkbox("Enable AI Predictions", value=default_pred_enabled)
                ui.render(ui.group_title_html("Alert thresholds"))
                pred_prob = st.slider("Alert Probability Threshold", 0.0, 1.0, default_pred_prob, 0.05)
                pred_disc = st.slider("Minimum Expected Discount (%)", 0.0, 50.0, default_pred_disc, 0.5)
                ui.render(ui.group_title_html("Forecast and data"))
                pred_window = st.slider("Forecast Window (days)", 1, 30, default_pred_window, 1)
                obs_col, cooldown_col = st.columns(2)
                with obs_col:
                    pred_obs = st.number_input("Minimum Historical Observations", min_value=1, value=default_pred_obs)
                with cooldown_col:
                    pred_cooldown = st.number_input("Prediction Alert Cooldown (hours)", min_value=1, value=default_pred_cooldown)
                
                if st.form_submit_button("💾 Save AI Settings", type="primary"):
                    update_notification_settings(
                        email=default_email,
                        price_drop_enabled=default_price_drop,
                        target_alert_enabled=default_target_alert,
                        prediction_enabled=int(pred_enabled),
                        prediction_alert_probability=pred_prob,
                        prediction_min_discount=pred_disc,
                        prediction_forecast_window=pred_window,
                        prediction_alert_cooldown=pred_cooldown,
                        prediction_min_observations=pred_obs,
                    )
                    ui.show_alert("good", "AI prediction settings saved!")

ui.render(ui.footer_html())