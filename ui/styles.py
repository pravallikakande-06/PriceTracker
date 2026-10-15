"""Global CSS for the dashboard.

All custom rules use a `pt-` prefix or target keyed containers
(`st-key-*`), so they stay scoped to this app and do not depend on
Streamlit's generated emotion class names.
"""

import streamlit as st

# Design tokens, shared with the Plotly chart.
INK = "#181B34"
MUTED = "#5A6079"
LINE = "#E4E7F0"
GRID = "#EEF0F6"
ACCENT = "#4338CA"
GOOD = "#0B7A4B"
BAD = "#B93815"
WARN = "#9A5B00"
FONT = "Manrope, system-ui, -apple-system, 'Segoe UI', sans-serif"

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

:root {
  --pt-bg: #F5F6FA;
  --pt-surface: #FFFFFF;
  --pt-ink: #181B34;
  --pt-muted: #5A6079;
  --pt-line: #E4E7F0;
  --pt-accent: #4338CA;
  --pt-accent-strong: #3730A3;
  --pt-accent-soft: #EEEDFC;
  --pt-good: #0B7A4B;
  --pt-good-soft: #E3F5EC;
  --pt-bad: #B93815;
  --pt-bad-soft: #FDEEE8;
  --pt-warn: #9A5B00;
  --pt-warn-soft: #FFF3D6;
  --pt-neutral-soft: #F0F2F8;
  --pt-ai: #6D3FD9;
  --pt-ai-soft: #F2EDFE;
  --pt-ai-line: #DDD2FA;
  --pt-shadow: 0 1px 2px rgba(24,27,52,.04), 0 8px 20px -14px rgba(24,27,52,.16);
  --pt-shadow-lift: 0 2px 4px rgba(24,27,52,.05), 0 16px 30px -16px rgba(24,27,52,.24);
}

/* ---------- Base ---------- */
html, body, [data-testid="stAppViewContainer"], .stApp {
  font-family: Manrope, system-ui, -apple-system, 'Segoe UI', sans-serif;
  color: var(--pt-ink);
}
[data-testid="stAppViewContainer"], .stApp { background: var(--pt-bg); }
[data-testid="stMainBlockContainer"], .block-container {
  max-width: 1180px;
  padding: 1.5rem 1.5rem 3rem;
}
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer, [data-testid="stDecoration"],
[data-testid="stAppDeployButton"] { visibility: hidden; display: none; }
.pt-num { font-variant-numeric: tabular-nums; }
:focus-visible { outline: 2px solid var(--pt-accent); outline-offset: 2px; }

/* ---------- Header ---------- */
.pt-header {
  display: flex; flex-wrap: wrap; align-items: center;
  justify-content: space-between; gap: 1rem;
  padding: .25rem 0 1.25rem;
}
.pt-brand { display: flex; align-items: center; gap: .85rem; }
.pt-logo {
  width: 44px; height: 44px; border-radius: 12px;
  display: grid; place-items: center;
  background: var(--pt-accent); color: #fff;
}
.pt-title { font-size: 1.5rem; font-weight: 800; letter-spacing: -.02em; line-height: 1.15; }
.pt-tagline { color: var(--pt-muted); font-size: .92rem; margin-top: .1rem; }
.pt-header-status { display: flex; flex-wrap: wrap; gap: .5rem; }
.pt-pill {
  display: inline-flex; align-items: center; gap: .45rem;
  padding: .4rem .8rem; border-radius: 999px;
  font-size: .82rem; font-weight: 600;
  background: var(--pt-surface); border: 1px solid var(--pt-line);
}
.pt-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--pt-muted); }
.pt-pill--good .pt-dot { background: var(--pt-good); }
.pt-pill--accent .pt-dot { background: var(--pt-accent); }

/* ---------- Section headings ---------- */
.pt-section {
  display: flex; align-items: baseline; justify-content: space-between;
  flex-wrap: wrap; gap: .25rem 1rem; margin: 1.5rem 0 .25rem; scroll-margin-top: 1rem;
}
.pt-section-title { font-size: 1.1rem; font-weight: 800; letter-spacing: -.01em; }
.pt-section-meta { color: var(--pt-muted); font-size: .86rem; }

/* ---------- Metric cards ---------- */
.pt-metrics {
  display: grid; gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
}
.pt-metric {
  background: var(--pt-surface); border: 1px solid var(--pt-line);
  border-radius: 16px; padding: 1.1rem 1.2rem;
  box-shadow: 0 1px 2px rgba(24,27,52,.04);
}
.pt-metric-top { display: flex; align-items: center; gap: .6rem; color: var(--pt-muted); font-size: .86rem; font-weight: 600; }
.pt-icon-chip {
  width: 32px; height: 32px; border-radius: 9px; flex: none;
  display: grid; place-items: center;
  background: var(--pt-accent-soft); color: var(--pt-accent);
}
.pt-icon-chip--good { background: var(--pt-good-soft); color: var(--pt-good); }
.pt-metric-value {
  font-size: 1.85rem; font-weight: 800; letter-spacing: -.02em;
  margin-top: .65rem; line-height: 1.1; font-variant-numeric: tabular-nums;
}
.pt-metric-sub {
  color: var(--pt-muted); font-size: .84rem; margin-top: .3rem;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.pt-trend {
  display: inline-flex; align-items: center; gap: .3rem;
  margin-top: .55rem; padding: .15rem .55rem; border-radius: 999px;
  font-size: .78rem; font-weight: 700;
}
.pt-trend--good { background: var(--pt-good-soft); color: var(--pt-good); }
.pt-trend--bad { background: var(--pt-bad-soft); color: var(--pt-bad); }
.pt-trend--neutral { background: var(--pt-neutral-soft); color: var(--pt-muted); }

/* ---------- Panels (add product) ---------- */
[class*="st-key-panel_"] {
  background: var(--pt-surface);
  border: 1px solid var(--pt-line) !important;
  border-radius: 16px !important;
  padding: 1.25rem 1.4rem !important;
  box-shadow: 0 1px 2px rgba(24,27,52,.04);
}
[class*="st-key-panel_"] [data-testid="stForm"] {
  border: 0 !important; padding: 0 !important; background: transparent;
}

/* ---------- Product cards ---------- */
[class*="st-key-card_"] {
  --spine: var(--pt-line);
  background: var(--pt-surface);
  border: 1px solid var(--pt-line) !important;
  border-left: 5px solid var(--spine) !important;
  border-radius: 16px !important;
  padding: 1.25rem 1.4rem !important;
  box-shadow: 0 1px 2px rgba(24,27,52,.04), 0 10px 24px -14px rgba(24,27,52,.14);
}
[class*="st-key-card_good_"] { --spine: var(--pt-good); }
[class*="st-key-card_warn_"] { --spine: #E0861A; }
[class*="st-key-card_bad_"] { --spine: var(--pt-bad); }
[class*="st-key-card_neutral_"] { --spine: var(--pt-accent); }

.pt-card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: .75rem; }
.pt-card-title { font-size: 1.12rem; font-weight: 800; letter-spacing: -.01em; line-height: 1.3; overflow-wrap: anywhere; }
.pt-url {
  color: var(--pt-muted); font-size: .8rem; margin-top: .15rem;
  max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.pt-badge {
  display: inline-flex; align-items: center; gap: .35rem; flex: none;
  padding: .3rem .65rem; border-radius: 999px;
  font-size: .78rem; font-weight: 700; white-space: nowrap;
}
.pt-badge--good { background: var(--pt-good-soft); color: var(--pt-good); }
.pt-badge--warn { background: var(--pt-warn-soft); color: var(--pt-warn); }
.pt-badge--bad { background: var(--pt-bad-soft); color: var(--pt-bad); }
.pt-badge--neutral { background: var(--pt-neutral-soft); color: var(--pt-muted); }
.pt-badge--accent { background: var(--pt-accent-soft); color: var(--pt-accent); }

.pt-stats { display: grid; grid-template-columns: 1.4fr 1fr 1fr; gap: .75rem; margin: 1rem 0 .85rem; }
.pt-stat-label { color: var(--pt-muted); font-size: .78rem; font-weight: 600; }
.pt-stat-value { font-size: 1.02rem; font-weight: 700; margin-top: .15rem; font-variant-numeric: tabular-nums; }
.pt-stat-value--hero { font-size: 1.7rem; font-weight: 800; letter-spacing: -.02em; line-height: 1.15; }
.pt-stat-note { color: var(--pt-muted); font-size: .76rem; margin-top: .1rem; }

.pt-strip {
  display: flex; align-items: center; gap: .55rem;
  padding: .6rem .8rem; border-radius: 12px;
  font-size: .9rem; font-weight: 700; margin-bottom: .6rem;
}
.pt-strip--good { background: var(--pt-good-soft); color: var(--pt-good); }
.pt-strip--warn { background: var(--pt-warn-soft); color: var(--pt-warn); }
.pt-strip--neutral { background: var(--pt-neutral-soft); color: var(--pt-muted); }
.pt-strip--accent { background: var(--pt-accent-soft); color: var(--pt-accent); }
.pt-strip--bad { background: var(--pt-bad-soft); color: var(--pt-bad); }
.pt-strip small { display: block; font-weight: 500; color: var(--pt-muted); font-size: .8rem; margin-top: .1rem; }
.pt-strip svg { flex: none; }

.pt-checked { display: flex; align-items: center; gap: .4rem; color: var(--pt-muted); font-size: .82rem; margin: .5rem 0 .6rem; }
.pt-chart-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: .1rem; }
.pt-chart-title { font-weight: 700; font-size: .92rem; }
.pt-chart-meta, .pt-hint { color: var(--pt-muted); font-size: .8rem; }

/* ---------- Alerts ---------- */
.pt-alert {
  display: flex; gap: .7rem; align-items: flex-start;
  padding: .8rem 1rem; border-radius: 12px; margin: .75rem 0 .25rem;
  border: 1px solid transparent;
}
.pt-alert-title { font-weight: 700; font-size: .93rem; }
.pt-alert-body { font-size: .86rem; margin-top: .1rem; color: var(--pt-ink); }
.pt-alert svg { flex: none; margin-top: .1rem; }
.pt-alert--good { background: var(--pt-good-soft); color: var(--pt-good); border-color: #BFE6D1; }
.pt-alert--bad { background: var(--pt-bad-soft); color: var(--pt-bad); border-color: #F4C9BA; }
.pt-alert--warn { background: var(--pt-warn-soft); color: var(--pt-warn); border-color: #F1DBA3; }
.pt-alert--info { background: var(--pt-accent-soft); color: var(--pt-accent); border-color: #D4D1F7; }

/* ---------- Empty states ---------- */
.pt-empty {
  background: var(--pt-surface); border: 1px dashed #CBD0E1;
  border-radius: 16px; padding: 2.75rem 1.5rem; text-align: center; margin-top: .75rem;
}
.pt-empty-icon {
  width: 68px; height: 68px; border-radius: 50%; margin: 0 auto 1rem;
  display: grid; place-items: center;
  background: var(--pt-accent-soft); color: var(--pt-accent);
}
.pt-empty-title { font-size: 1.2rem; font-weight: 800; }
.pt-empty-body { color: var(--pt-muted); max-width: 420px; margin: .4rem auto 1.1rem; font-size: .95rem; line-height: 1.5; }
.pt-cta {
  display: inline-flex; align-items: center; gap: .4rem;
  background: var(--pt-accent); color: #fff !important; text-decoration: none !important;
  font-weight: 700; font-size: .92rem; padding: .6rem 1.1rem; border-radius: 10px;
}
.pt-cta:hover { background: var(--pt-accent-strong); }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] { background: var(--pt-surface); border-right: 1px solid var(--pt-line); }
[data-testid="stSidebarContent"] { padding-top: .5rem; }
.pt-side-title { display: flex; align-items: center; gap: .5rem; font-weight: 800; font-size: 1rem; margin: .25rem 0 .6rem; }
.pt-side-title svg { color: var(--pt-accent); }
.pt-side-card {
  background: var(--pt-bg); border: 1px solid var(--pt-line);
  border-radius: 12px; padding: .8rem .9rem; font-size: .85rem; line-height: 1.5;
}
.pt-side-card b { font-weight: 700; }
.pt-side-muted { color: var(--pt-muted); font-size: .8rem; line-height: 1.5; }
.pt-side-muted code { font-size: .78rem; }

/* ---------- Footer ---------- */
.pt-footer {
  display: flex; flex-wrap: wrap; justify-content: space-between; gap: .5rem;
  margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid var(--pt-line);
  color: var(--pt-muted); font-size: .82rem;
}
.pt-footer b { color: var(--pt-ink); display: inline-flex; align-items: center; gap: .4rem; }

/* ---------- Streamlit widgets ---------- */
[data-testid="stWidgetLabel"] p { font-weight: 600; font-size: .85rem; color: var(--pt-ink); }
[data-testid="stTextInputRootElement"], [data-testid="stNumberInputContainer"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  border: 1px solid #CBD0E1 !important; border-radius: 10px !important;
  background: #fff !important;
}
[data-testid="stTextInputRootElement"]:focus-within,
[data-testid="stNumberInputContainer"]:focus-within,
[data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {
  border-color: var(--pt-accent) !important; box-shadow: 0 0 0 3px rgba(67,56,202,.18);
}
[data-testid^="stBaseButton"], [data-testid^="stBaseLinkButton"] {
  border-radius: 10px; font-weight: 700; min-height: 2.5rem;
  transition: background-color .15s, border-color .15s;
}
[data-testid="stBaseButton-secondary"], [data-testid="stBaseLinkButton-secondary"] {
  background: #fff; border: 1px solid #CBD0E1; color: var(--pt-ink);
}
[data-testid="stBaseButton-secondary"]:hover, [data-testid="stBaseLinkButton-secondary"]:hover {
  border-color: var(--pt-accent); color: var(--pt-accent); background: var(--pt-accent-soft);
}
[data-testid^="stBaseButton-primary"] { background: var(--pt-accent); border: 1px solid var(--pt-accent); color: #fff; }
[data-testid^="stBaseButton-primary"]:hover { background: var(--pt-accent-strong); border-color: var(--pt-accent-strong); color: #fff; }
[data-testid="stExpander"] { border-radius: 10px; border-color: var(--pt-line); background: #fff; }

@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"], .block-container { padding: 1rem .9rem 2.5rem; }
  .pt-stats { grid-template-columns: 1fr 1fr; }
  .pt-stats > :first-child { grid-column: 1 / -1; }
  .pt-title { font-size: 1.3rem; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }

/* =====================================================================
   APP LAYER: styles for the widgets app.py renders
   ===================================================================== */

[data-testid="stAppViewContainer"], .stApp {
  background: radial-gradient(900px 320px at 12% -80px, #E9E8FB 0%, rgba(245,246,250,0) 70%), var(--pt-bg);
}
[data-testid="stMainBlockContainer"] { overflow-x: clip; }
[data-testid="stMarkdownContainer"] { overflow-wrap: anywhere; }

/* ---------- Header (app variant) ---------- */
.pt-header--app {
  background: var(--pt-surface); border: 1px solid var(--pt-line);
  border-radius: 18px; padding: 1.1rem 1.35rem; margin-bottom: 1.1rem;
  box-shadow: var(--pt-shadow);
  background-image: linear-gradient(100deg, rgba(67,56,202,.07), rgba(67,56,202,0) 45%);
}
.pt-header--app .pt-logo {
  width: 48px; height: 48px; border-radius: 14px;
  background: linear-gradient(135deg, #5B50E6, #3730A3);
  box-shadow: 0 8px 16px -8px rgba(67,56,202,.7);
}
.pt-header--app .pt-title { font-size: 1.65rem; }
.pt-pill { box-shadow: 0 1px 1px rgba(24,27,52,.03); }
.pt-pill--good { background: var(--pt-good-soft); border-color: #BFE6D1; color: var(--pt-good); }
.pt-pill--accent { background: var(--pt-accent-soft); border-color: #D4D1F7; color: var(--pt-accent); }

/* ---------- Navigation tabs ---------- */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: .25rem; width: fit-content; max-width: 100%; overflow-x: auto;
  background: var(--pt-surface); border: 1px solid var(--pt-line);
  border-radius: 14px; padding: .3rem; box-shadow: var(--pt-shadow);
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none; }
[data-testid="stTabs"] button[data-baseweb="tab"] {
  height: auto; padding: .55rem 1.1rem; border-radius: 10px;
  background: transparent; color: var(--pt-muted);
  transition: background-color .15s, color .15s, box-shadow .15s;
}
[data-testid="stTabs"] button[data-baseweb="tab"] p { font-weight: 700; font-size: .92rem; color: inherit; }
[data-testid="stTabs"] button[data-baseweb="tab"]:hover { background: var(--pt-neutral-soft); color: var(--pt-ink); }
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
  background: var(--pt-accent); color: #fff;
  box-shadow: 0 6px 14px -8px rgba(67,56,202,.8);
}
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"]:hover { background: var(--pt-accent-strong); color: #fff; }
[data-testid="stTabs"] [data-baseweb="tab-panel"] { padding-top: 1.25rem; }
/* nested tabs (Settings): lighter, secondary navigation */
[data-baseweb="tab-panel"] [data-testid="stTabs"] [data-baseweb="tab-list"] { box-shadow: none; background: var(--pt-neutral-soft); }
[data-baseweb="tab-panel"] [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
  background: var(--pt-surface); color: var(--pt-accent); box-shadow: 0 1px 3px rgba(24,27,52,.14);
}
[data-baseweb="tab-panel"] [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"]:hover { background: var(--pt-surface); color: var(--pt-accent-strong); }

/* ---------- KPI cards ---------- */
.pt-metrics--3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.pt-metrics--4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.pt-metrics--4 .pt-metric-value { font-size: 1.45rem; }
.pt-metric { transition: transform .15s ease, box-shadow .15s ease; min-width: 0; }
.pt-metric:hover { transform: translateY(-2px); }
.pt-metric-value { font-size: 1.7rem; overflow-wrap: anywhere; }
.pt-icon-chip--sm { width: 24px; height: 24px; border-radius: 7px; }
.pt-icon-chip--good { background: var(--pt-good-soft); color: var(--pt-good); }
.pt-icon-chip--warn { background: var(--pt-warn-soft); color: var(--pt-warn); }
.pt-icon-chip--bad { background: var(--pt-bad-soft); color: var(--pt-bad); }
.pt-icon-chip--ai { background: var(--pt-ai-soft); color: var(--pt-ai); }
.pt-icon-chip--neutral { background: var(--pt-neutral-soft); color: var(--pt-muted); }
.pt-metric { --tone: var(--pt-accent); box-shadow: inset 0 3px 0 var(--tone), var(--pt-shadow); }
.pt-metric:hover { box-shadow: inset 0 3px 0 var(--tone), var(--pt-shadow-lift); }
.pt-metric--good { --tone: var(--pt-good); }
.pt-metric--warn { --tone: #E0861A; }
.pt-metric--ai { --tone: var(--pt-ai); }
.pt-metric--accent { --tone: var(--pt-accent); }
.pt-metric--neutral { --tone: #CBD0E1; }

/* ---------- Analytics table ---------- */
.pt-table-wrap {
  background: var(--pt-surface); border: 1px solid var(--pt-line);
  border-radius: 16px; overflow-x: auto; box-shadow: var(--pt-shadow); margin-top: .5rem;
}
.pt-table { width: 100%; min-width: 720px; border-collapse: collapse; font-size: .9rem; }
.pt-table th {
  text-align: left; padding: .75rem 1rem; white-space: nowrap;
  font-size: .78rem; font-weight: 700; color: var(--pt-muted);
  background: #F8F9FC; border-bottom: 1px solid var(--pt-line);
}
.pt-table td { padding: .85rem 1rem; border-bottom: 1px solid #F0F2F8; vertical-align: middle; }
.pt-table tbody tr:last-child td { border-bottom: 0; }
.pt-table tbody tr { transition: background-color .12s; }
.pt-table tbody tr:hover { background: #F8F8FF; }
.pt-table .num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.pt-prod-cell { font-weight: 700; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pt-date { color: var(--pt-muted); white-space: nowrap; font-size: .84rem; }
.pt-neg { color: var(--pt-good); font-weight: 700; }
.pt-pos { color: var(--pt-bad); font-weight: 700; }

/* ---------- AI prediction ---------- */
.pt-ai-banner {
  display: flex; align-items: center; gap: .85rem; margin: .25rem 0 .75rem;
  padding: .9rem 1.1rem; border-radius: 16px;
  background: linear-gradient(120deg, #F2EDFE 0%, #FFFFFF 70%);
  border: 1px solid var(--pt-ai-line);
}
.pt-ai-banner .pt-icon-chip { width: 40px; height: 40px; border-radius: 12px; background: var(--pt-ai); color: #fff; }
.pt-ai-banner-title { font-weight: 800; font-size: 1.05rem; letter-spacing: -.01em; }
.pt-ai-banner-sub { color: var(--pt-muted); font-size: .86rem; margin-top: .1rem; }
.pt-ai-grid { display: grid; gap: .8rem; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: .25rem; }
.pt-ai-card {
  background: linear-gradient(180deg, #FFFFFF, #FAF8FF); border: 1px solid var(--pt-ai-line);
  border-radius: 14px; padding: .9rem 1rem; min-width: 0;
}
.pt-ai-label { color: var(--pt-muted); font-size: .78rem; font-weight: 600; }
.pt-ai-value { font-size: 1.3rem; font-weight: 800; letter-spacing: -.01em; margin-top: .3rem; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.pt-meter { height: 6px; border-radius: 999px; background: #E9E3FB; margin-top: .6rem; overflow: hidden; }
.pt-meter span { display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, #8B5CF6, #6D3FD9); }
.pt-ai-meta { display: flex; flex-wrap: wrap; gap: .5rem; margin: .8rem 0 .2rem; }
.pt-ai-meta .pt-badge--accent { background: var(--pt-ai-soft); color: var(--pt-ai); }
.pt-ai-explain {
  margin-top: .6rem; padding: .75rem 1rem; border-radius: 12px; font-size: .88rem; line-height: 1.55;
  background: var(--pt-ai-soft); border-left: 4px solid var(--pt-ai);
}
.pt-ai-explain b { display: block; color: var(--pt-ai); font-size: .8rem; margin-bottom: .15rem; }
.pt-ai-line { display: flex; align-items: center; gap: .5rem; font-size: .86rem; color: var(--pt-muted); margin: 0 0 .6rem; flex-wrap: wrap; }
.pt-ai-line b { color: var(--pt-ink); }

/* ---------- Product cards ---------- */
[class*="st-key-card_"] { transition: box-shadow .15s ease, transform .15s ease; min-width: 0; }
[class*="st-key-card_"]:hover { box-shadow: var(--pt-shadow-lift); transform: translateY(-1px); }
.pt-url svg { vertical-align: -1px; }
.pt-stats--4 { grid-template-columns: 1.5fr 1fr 1fr 1fr; }
.pt-stat-value--hero { color: var(--pt-ink); }
[class*="st-key-chart_"] {
  background: #FBFBFE; border: 1px solid var(--pt-line); border-radius: 14px;
  padding: .8rem .9rem .35rem; margin-top: .5rem; min-width: 0;
}
[data-testid="stPlotlyChart"] { max-width: 100%; }

/* ---------- Panels, groups, settings ---------- */
.pt-panel-head { display: flex; align-items: center; gap: .7rem; margin-bottom: .6rem; }
.pt-panel-title { font-weight: 800; font-size: 1.02rem; letter-spacing: -.01em; }
.pt-panel-sub { color: var(--pt-muted); font-size: .84rem; }
.pt-group-title {
  font-weight: 700; font-size: .86rem; color: var(--pt-accent);
  margin: 1rem 0 .15rem; padding-bottom: .35rem; border-bottom: 1px solid var(--pt-line);
}
.pt-group-title:first-child { margin-top: .25rem; }

/* ---------- Inputs and buttons ---------- */
[data-testid="stTextInputRootElement"] input, [data-testid="stNumberInputContainer"] input { min-height: 2.6rem; font-weight: 500; }
[data-testid="stTextInputRootElement"], [data-testid="stNumberInputContainer"] { transition: border-color .15s, box-shadow .15s; }
[data-testid^="stBaseButton"], [data-testid^="stBaseLinkButton"] {
  min-height: 2.75rem; padding-inline: 1.2rem;
  transition: background-color .15s, border-color .15s, box-shadow .15s, transform .15s;
}
[data-testid^="stBaseButton-primary"], [data-testid^="stBaseLinkButton-primary"] { box-shadow: 0 6px 14px -8px rgba(67,56,202,.8); }
[data-testid^="stBaseButton"]:hover:not(:disabled), [data-testid^="stBaseLinkButton"]:hover { transform: translateY(-1px); }
[data-testid^="stBaseButton"]:active:not(:disabled) { transform: translateY(0); }
[data-testid="stExpander"] { box-shadow: var(--pt-shadow); border-radius: 14px; overflow: hidden; }
[data-testid="stExpander"] summary { font-weight: 700; }
[data-testid="stExpander"] summary:hover { background: var(--pt-neutral-soft); }
[data-testid="stSlider"] [data-testid="stWidgetLabel"] p { font-weight: 600; }
[data-testid="stSpinner"] { color: var(--pt-muted); }

/* ---------- Footer ---------- */
.pt-footer { margin-top: 2rem; }

/* ---------- Responsive ---------- */
@media (max-width: 1000px) {
  .pt-metrics--4 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .pt-metrics--3 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .pt-ai-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 768px) {
  [data-testid="stMainBlockContainer"], .block-container { padding: 1rem .9rem 2.5rem; }
  .pt-header--app { padding: .9rem 1rem; }
  .pt-header--app .pt-title { font-size: 1.3rem; }
  .pt-metrics--3, .pt-metrics--4 { grid-template-columns: 1fr; }
  .pt-metric-value { font-size: 1.5rem; }
  .pt-stats--4 { grid-template-columns: 1fr 1fr; }
  .pt-stats--4 > :first-child { grid-column: 1 / -1; }
  .pt-stat-value--hero { font-size: 1.5rem; }
  .pt-card-head { flex-wrap: wrap; }
  [class*="st-key-card_"], [class*="st-key-panel_"] { padding: 1rem !important; }
  [data-testid="stTabs"] [data-baseweb="tab-list"] { width: 100%; }
  [data-testid="stTabs"] button[data-baseweb="tab"] { padding: .5rem .8rem; flex: none; }
  [data-testid^="stBaseButton"], [data-testid^="stBaseLinkButton"] { width: 100%; }
}
@media (max-width: 480px) {
  .pt-ai-grid { grid-template-columns: 1fr; }
}
/* =====================================================================
   INTELLIGENCE LAYER: deal score, advisor, insights, timeline, etc.
   ===================================================================== */
.pt-tone--good { color: var(--pt-good); } .pt-tone--warn { color: var(--pt-warn); }
.pt-tone--bad { color: var(--pt-bad); } .pt-tone--accent { color: var(--pt-accent); }
.pt-tone--neutral { color: var(--pt-muted); }

.pt-intel-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.25fr); gap: .9rem; margin: .8rem 0 .5rem; }
.pt-intel {
  --tone: var(--pt-accent); background: var(--pt-surface); border: 1px solid var(--pt-line);
  border-radius: 14px; padding: .9rem 1rem 1rem; min-width: 0; margin-bottom: .6rem;
  box-shadow: inset 0 3px 0 var(--tone);
}
.pt-intel-row .pt-intel { margin-bottom: 0; }
.pt-intel--good { --tone: var(--pt-good); } .pt-intel--warn { --tone: #E0861A; }
.pt-intel--bad { --tone: var(--pt-bad); } .pt-intel--ai { --tone: var(--pt-ai); background: linear-gradient(180deg, #fff, #FAF8FF); }
.pt-intel--neutral { --tone: #CBD0E1; }
.pt-intel-head { display: flex; align-items: center; gap: .5rem; font-size: .78rem; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; color: var(--pt-muted); margin-bottom: .6rem; }

.pt-score { display: flex; align-items: center; gap: 1rem; }
.pt-ring { --c: var(--pt-accent); width: 88px; height: 88px; border-radius: 50%; flex: none; position: relative; display: grid; place-items: center;
  background: conic-gradient(var(--c) calc(var(--p) * 1%), #E9EBF3 0); }
.pt-ring::before { content: ""; position: absolute; inset: 9px; background: #fff; border-radius: 50%; }
.pt-ring span { position: relative; font-weight: 800; font-size: 1.55rem; letter-spacing: -.02em; }
.pt-ring small { font-size: .62rem; color: var(--pt-muted); font-weight: 700; margin-left: 1px; }
.pt-ring--good { --c: var(--pt-good); } .pt-ring--warn { --c: #E0861A; } .pt-ring--bad { --c: var(--pt-bad); }
.pt-score-label { font-weight: 800; font-size: 1.05rem; }
.pt-score-text { color: var(--pt-muted); font-size: .86rem; line-height: 1.5; margin-top: .25rem; }
.pt-score-text b { color: var(--pt-ink); }
.pt-score-empty { color: var(--pt-muted); font-size: .88rem; }

.pt-verdict { font-weight: 800; font-size: 1.3rem; letter-spacing: -.01em; }
.pt-verdict small { font-size: .75rem; color: var(--pt-muted); font-weight: 700; margin-left: .3rem; }
.pt-verdict--good { color: var(--pt-good); } .pt-verdict--warn { color: var(--pt-warn); }
.pt-verdict--bad { color: var(--pt-bad); } .pt-verdict--neutral { color: var(--pt-muted); }
.pt-reasons { list-style: none; margin: .6rem 0 .3rem; padding: 0; display: grid; gap: .3rem; }
.pt-reason { font-size: .86rem; display: flex; gap: .5rem; align-items: baseline; }
.pt-reason b { width: 1rem; flex: none; text-align: center; }
.pt-reason--pos b { color: var(--pt-good); } .pt-reason--neg b { color: var(--pt-warn); } .pt-reason--neu b { color: var(--pt-muted); }
.pt-confidence { margin-top: .5rem; font-size: .8rem; color: var(--pt-muted); }
.pt-confidence b { color: var(--pt-ai); font-size: .95rem; }
.pt-advice-grid, .pt-kv-grid { display: grid; gap: .6rem .9rem; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); margin: .6rem 0 .2rem; }
.pt-kv { min-width: 0; }
.pt-kv-label { color: var(--pt-muted); font-size: .76rem; font-weight: 600; }
.pt-kv-value { font-weight: 800; font-size: 1.05rem; margin-top: .1rem; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.pt-kv-value small { color: var(--pt-muted); font-weight: 600; font-size: .75rem; }
.pt-na { color: var(--pt-muted); font-size: .88rem; padding: .2rem 0; }
.pt-note { color: var(--pt-muted); font-size: .78rem; margin-top: .55rem; line-height: 1.45; }
.pt-meter--warn span { background: linear-gradient(90deg, #F5B35A, #E0861A); }
.pt-meter--warn { background: #F6E9D3; }
.pt-insight-list { margin: .7rem 0 0; padding: .6rem .9rem .6rem 1.6rem; background: var(--pt-accent-soft); border-radius: 10px; font-size: .86rem; line-height: 1.5; }

.pt-timeline { list-style: none; margin: .3rem 0 0; padding: 0 0 0 .3rem; border-left: 2px solid var(--pt-line); }
.pt-tl-item { position: relative; display: flex; flex-wrap: wrap; align-items: center; gap: .3rem .8rem; padding: .45rem 0 .45rem 1rem; }
.pt-tl-item::before { content: ""; position: absolute; left: -.62rem; top: 50%; width: 10px; height: 10px; margin-top: -5px; border-radius: 50%; background: #CBD0E1; border: 2px solid #fff; }
.pt-tl-item--drop::before { background: var(--pt-good); } .pt-tl-item--rise::before { background: var(--pt-bad); }
.pt-tl-date { color: var(--pt-muted); font-size: .8rem; min-width: 7.5rem; }
.pt-tl-price { font-weight: 800; font-variant-numeric: tabular-nums; min-width: 6rem; }

.pt-rank-list { background: var(--pt-surface); border: 1px solid var(--pt-line); border-radius: 16px; box-shadow: var(--pt-shadow); overflow: hidden; }
.pt-rank-row { display: flex; align-items: center; gap: .8rem; padding: .8rem 1.1rem; border-bottom: 1px solid #F0F2F8; flex-wrap: wrap; }
.pt-rank-row:last-child { border-bottom: 0; }
.pt-rank { width: 26px; height: 26px; border-radius: 8px; background: var(--pt-accent-soft); color: var(--pt-accent); font-weight: 800; font-size: .8rem; display: grid; place-items: center; flex: none; }
.pt-rank-name { font-weight: 700; flex: 1 1 180px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pt-rank-score { font-weight: 800; font-size: 1.05rem; } .pt-rank-score small { color: var(--pt-muted); font-size: .7rem; }
.pt-rank-price { font-weight: 800; min-width: 6rem; text-align: right; font-variant-numeric: tabular-nums; }
.pt-rank-detail { color: var(--pt-muted); font-size: .84rem; }

.pt-wl { display: grid; gap: .8rem; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.pt-wl-cell { background: var(--pt-surface); border: 1px solid var(--pt-line); border-radius: 14px; padding: .8rem 1rem; box-shadow: var(--pt-shadow); }
.pt-wl-num { font-size: 1.6rem; font-weight: 800; } .pt-wl-label { color: var(--pt-muted); font-size: .8rem; font-weight: 600; }
.pt-wl-cell--good .pt-wl-num { color: var(--pt-good); } .pt-wl-cell--warn .pt-wl-num { color: var(--pt-warn); } .pt-wl-cell--accent .pt-wl-num { color: var(--pt-accent); }

.pt-flash-alert { margin: .6rem 0; }
[class*="st-key-card_"] [data-testid="stExpander"] { box-shadow: none; }

@media (max-width: 900px) { .pt-intel-row { grid-template-columns: 1fr; } .pt-wl { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 768px) {
  .pt-score { flex-direction: column; align-items: flex-start; }
  .pt-rank-price { text-align: left; min-width: 0; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition: none !important; animation: none !important; }
  .pt-metric:hover, [class*="st-key-card_"]:hover, [data-testid^="stBaseButton"]:hover,
  [data-testid^="stBaseLinkButton"]:hover { transform: none !important; }
}
"""


def inject_styles():
    """Inject the global stylesheet once per script run."""

    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)