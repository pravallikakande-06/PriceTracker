# 🛒 E-Commerce Price Tracker

A Python-based E-Commerce Price Tracker with a sleek, modern UI. It monitors product prices, stores price history, detects price drops, and utilizes an AI-based system for Price Prediction and Forecasts to determine optimal buying times.

## ✨ Features

* 🔎 **Scrape** product names and prices via custom web scraper
* 💾 **Store** products and complete price history in SQLite
* 📊 **Dashboard Tab**: High-level metrics, total drops, predictions, and recent activity
* 📦 **Tracked Products Tab**: Responsive product cards containing Plotly history/forecast charts
* ⚙️ **Settings Tab**: Seamless configuration for Notifications and AI Prediction tuning
* 📉 **Detect** price decreases automatically with email alerts
* 🎯 **Target-price alerts** via SMTP
* 🤖 **AI Price Prediction**: Estimates the probability of a future drop, forecast range, and discount windows using actual historical SQLite data. Includes prediction evaluations and accuracy tracking!
* ⏰ **Scheduler** script for background monitoring
* 🧪 **Automated tests** using Pytest

---

## 🏗️ Architecture

- **`app.py`**: Streamlit 3-tab UI layout.
- **`database.py`**: SQLite models and safe schema migrations.
- **`prediction.py`**: Lightweight AI model for stats/trends forecasting.
- **`tracker.py`**: Main scraper loop, handles price changes, notifications, and evaluating old predictions.
- **`notifier.py`**: SMTP delivery logic.
- **`scheduler.py`**: Background loop for triggering `tracker.py`.

---

## 🚀 Installation

```powershell
# Create venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

---

## 🔐 Environment Variables

Create a `.env` file for email notification support:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-google-app-password
NOTIFICATION_EMAIL=your-email@gmail.com
CHECK_INTERVAL=3600
```

---

## 🤖 AI Price Prediction System

Our AI Prediction engine doesn't use random numbers or "black box" APIs. It analyzes your actual historical price data stored in `prices.db`.

### How it Works:
- **0–4 records**: Prediction unavailable (collecting more data).
- **5–9 records**: Basic linear trend forecasting.
- **10+ records**: Full historical discount frequency analysis, historical averages vs. current price comparison, time-since-last-drop modeling, and probabilistic confidence bounds.

### Prediction Output & Charts
Inside the **Tracked Products** tab, every item displays a Plotly graph combining its historical price trajectory with forward-projecting "forecast cone" dashed lines.

### Evaluation
The tracker actively checks its past predictions. When a new price is fetched, previous forecasts are evaluated. You can see the **Direction Accuracy** and **Average Error** directly in the Dashboard!

### Settings & Alerts
Under **Settings -> AI Predictions**, you can configure:
- Minimum Historical Observations required
- Probability Threshold (e.g. 70%) to trigger an alert
- Minimum Expected Discount (e.g. 5%)
- Cooldown hours

*Note: AI predictions are statistical estimates based on historical price data and are NOT guaranteed future prices.*

---

## 🧠 Price Intelligence

All of this is rule-based statistics over the price checks the app has recorded. No machine-learning model is used, and when there is not enough history the app says "Not enough data" instead of guessing.

| Feature | How it is calculated |
|---|---|
| **Deal Score (0-100)** | Weighted: position in the historical price range (35), discount vs historical average (25), target proximity (20), recent trend (10), stored drop probability (10). Inputs that are unavailable (e.g. no target) are left out and the score is rescaled. Needs 3+ checks. |
| **Buy / Wait / Avoid** | Rules over the deal score, target status and the stored prediction. "Signal confidence" reflects how much data exists and how many signals agree; it is not a probability. Needs 5+ checks. |
| **Best Time to Buy** | Gaps and sizes of past drops of 1.5% or more (same rule as the predictor). Needs 10+ checks and 2+ drops. |
| **Volatility** | 60% average size of price changes + 40% share of checks that changed. LOW < 30 <= MEDIUM < 60 <= HIGH. |
| **Savings / Target progress** | Current price vs historical average, high, low and target. |
| **Alert levels** | Price changed (last 24h), Good deal (score 75+), Target near (within 5%), Target reached. Shown in the app; e-mail alerts are unchanged. |
| **Price comparison** | Works from links you add for the same product on other stores. Only pages the scraper can read are supported. |
| **Tracking health** | Based on the last successful check vs the scheduler interval. Failed checks are not stored, so they are not counted. |
| **Price report** | Downloadable PDF (no extra dependency; amounts print as "Rs."). |
| **Wishlist** | A flag on the product (`products.wishlist`, added automatically, existing data untouched). |

The logic lives in `deal_analyzer.py` (pure functions), `price_comparison.py` and `report.py`.

## ▶️ Running the Application

**To start the UI:**
```powershell
python -m streamlit run app.py
```

**To run the background scheduler:**
```powershell
python scheduler.py
```

---

## 🧪 Testing

To run the automated tests covering the database migrations, scraping functionality, and prediction evaluation:

```powershell
python -m pytest
```

---
