"""
app.py
------
Natural Language to SQL Query Generator — Streamlit application.

Run locally with:
    streamlit run app.py

See README.md for setup details.
"""

import io
import base64
import datetime
from pathlib import Path

import streamlit as st

import database as db
import nl2sql_engine as engine
import sql_visualizer as viz
import streamlit.components.v1 as components

# --------------------------------------------------------------------------- #
# Page config + global styling
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="NL to SQL Query Generator",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRIMARY = "#7F849F"
SECONDARY = "#D9A996"
ACCENT = "#B8B0C8"
SUCCESS = "#7A9B84"
WARNING = "#C96C5B"
BG = "#F5F1ED"
TEXT = "#354151"

# --------------------------------------------------------------------------- #
# Assets (images shipped alongside app.py in an "assets" folder)
# --------------------------------------------------------------------------- #
ASSETS_DIR = Path(__file__).parent / "assets"
MODULE_BG_IMAGE = ASSETS_DIR / "bg_pattern.png"  # 3rd image -> background for every module


def _img_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def set_module_background(image_path: Path = MODULE_BG_IMAGE, corner_width: str = "340px"):
    """
    Places the given artwork as a small, fixed watermark tucked into the
    bottom-right corner of the viewport, on every module page. Implemented
    as a plain <img> overlay rather than a CSS background-image, since a
    single sized/positioned <img> is far more reliable to get right than
    juggling background-size/position/repeat across multiple CSS layers.
    """
    if not image_path.exists():
        return

    b64 = _img_to_base64(image_path)
    overlay_html = (
        f'<img src="data:image/png;base64,{b64}" '
        f'style="position:fixed;bottom:-22px;right:-22px;width:{corner_width};'
        'z-index:0;pointer-events:none;opacity:0.9;border-radius:20px;'
        'box-shadow:0 8px 30px rgba(90,80,100,0.12);" />'
    )
    st.markdown(overlay_html, unsafe_allow_html=True)


CUSTOM_CSS = """
<style>

/* =========================================================
   GLOBAL APPLICATION BACKGROUND
========================================================= */

.stApp {
    background:
        radial-gradient(
            circle at 0% 0%,
            rgba(229, 167, 145, 0.40),
            transparent 24%
        ),

        radial-gradient(
            circle at 100% 100%,
            rgba(142, 143, 180, 0.35),
            transparent 30%
        ),

        radial-gradient(
            circle at 80% 15%,
            rgba(255, 255, 255, 0.75),
            transparent 25%
        ),

        linear-gradient(
            135deg,
            #f7f2ed 0%,
            #eee9e6 50%,
            #f5f1ed 100%
        );

    color: #354151;
}


/* Main content transparent */

[data-testid="stAppViewContainer"] {
    background: transparent;
}


[data-testid="stMain"] {
    background: transparent;
}


/* Decorative background */

.stApp::before {
    content: "";
    position: fixed;

    width: 600px;
    height: 600px;

    right: -300px;
    bottom: -220px;

    border-radius: 50%;

    background:
        radial-gradient(
            circle,
            rgba(143, 145, 181, 0.25),
            rgba(143, 145, 181, 0.05),
            transparent 70%
        );

    border: 1px solid rgba(255,255,255,0.45);

    pointer-events: none;

    z-index: 0;
}


.stApp::after {
    content: "";

    position: fixed;

    width: 550px;
    height: 550px;

    left: -260px;
    top: -220px;

    border-radius: 50%;

    background:
        radial-gradient(
            circle,
            rgba(225, 157, 135, 0.30),
            rgba(225, 157, 135, 0.05),
            transparent 70%
        );

    pointer-events: none;

    z-index: 0;
}


/* Keep content above background */

.block-container {
    position: relative;
    z-index: 1;
}


/* =========================================================
   SIDEBAR
========================================================= */

section[data-testid="stSidebar"] {

    background:
        linear-gradient(
            180deg,
            rgba(255,255,255,0.65),
            rgba(240,234,231,0.85)
        );

    border-right: 1px solid rgba(180,170,180,0.30);
}


section[data-testid="stSidebar"] * {
    color: #354151 !important;
}


/* =========================================================
   GENERAL CARDS
========================================================= */

.app-card {

    background: rgba(255,255,255,0.55);

    backdrop-filter: blur(14px);

    border: 1px solid rgba(255,255,255,0.70);

    border-radius: 22px;

    padding: 24px;

    box-shadow:
        0 12px 35px rgba(90,80,100,0.10);

    margin-bottom: 18px;
}


/* =========================================================
   HEADINGS
========================================================= */

h1, h2, h3, h4 {

    color: #354151 !important;

    font-family: Georgia, serif;
}


/* =========================================================
   HERO
========================================================= */

.hero-banner {

    background: rgba(255,255,255,0.40);

    backdrop-filter: blur(12px);

    border: 1px solid rgba(255,255,255,0.65);

    border-radius: 24px;

    padding: 38px 32px;

    color: #354151;

    box-shadow:
        0 12px 35px rgba(90,80,100,0.10);

    margin-bottom: 24px;
}


.hero-banner h1 {

    color: #354151 !important;
}


.hero-banner p {

    color: #687080 !important;

    font-size: 1.05rem;
}


/* =========================================================
   INPUTS
========================================================= */

div[data-baseweb="input"] {

    background: rgba(255,255,255,0.45);

    border-radius: 14px;

    border: 1px solid #d6c8c4;
}


div[data-baseweb="input"] input {

    color: #354151 !important;
}


/* =========================================================
   NORMAL BUTTONS
========================================================= */

div.stButton > button {

    background: rgba(255,255,255,0.55) !important;

    color: #354151 !important;

    border: 1px solid #c9c0c5 !important;

    border-radius: 14px !important;

    transition: all 0.25s ease !important;
}


div.stButton > button:hover {

    transform: translateY(-2px);

    background: rgba(255,255,255,0.85) !important;

    box-shadow:
        0 8px 20px rgba(80,70,90,0.12);
}


/* SQL code */

.sql-box {

    background: rgba(53,65,81,0.94);

    color: #f5f1ed;

    font-family: "Courier New", monospace;

    padding: 18px;

    border-radius: 14px;

    white-space: pre-wrap;
}


/* =====================================================
   LANDING PAGE
===================================================== */

.landing-container {

    text-align: center;

    padding-top: 30px;

    padding-bottom: 20px;
}


/* =====================================================
   AUTH CARDS
===================================================== */

.auth-card {

    text-align: center;

    padding: 35px 30px 10px;

    background: rgba(255,255,255,0.38);

    backdrop-filter: blur(15px);

    border-radius: 32px 32px 0 0;

    border:
        1px solid rgba(255,255,255,0.70);

    box-shadow:
        0 12px 40px rgba(80,70,90,0.08);

    margin-top: 20px;
}


.auth-card h1 {

    font-family: Georgia, serif;

    font-size: 2.4rem;

    font-weight: 500;

    color: #354151;

    margin-top: 18px;

    margin-bottom: 8px;
}


.auth-subtitle {

    color: #747983;

    font-size: 1rem;

    margin-bottom: 20px;
}


/* Icons */

.auth-icon {

    position: relative;

    width: 105px;

    height: 105px;

    margin: auto;

    border-radius: 50%;

    display: flex;

    align-items: center;

    justify-content: center;

    font-size: 2.5rem;

    background: rgba(255,255,255,0.35);

    border: 1px solid rgba(255,255,255,0.60);
}


.login-icon {

    color: #7f849f;

    box-shadow:
        0 8px 25px rgba(127,132,159,0.20);
}


.signup-icon {

    color: #c78f79;

    box-shadow:
        0 8px 25px rgba(199,143,121,0.20);
}


.auth-icon-plus-badge {

    position: absolute;

    right: -2px;

    bottom: -2px;

    width: 30px;

    height: 30px;

    border-radius: 50%;

    display: flex;

    align-items: center;

    justify-content: center;

    font-size: 1.1rem;

    font-weight: 700;

    line-height: 1;

    color: #ffffff;

    background: #c78f79;

    border: 2px solid rgba(255,255,255,0.85);

    box-shadow: 0 4px 10px rgba(199,143,121,0.35);
}


/* =====================================================
   AUTH FORM
===================================================== */

div[data-testid="stForm"] {

    background: rgba(255,255,255,0.38);

    backdrop-filter: blur(15px);

    padding: 20px 40px 35px;

    border-radius: 0 0 32px 32px;

    border-left:
        1px solid rgba(255,255,255,0.70);

    border-right:
        1px solid rgba(255,255,255,0.70);

    border-bottom:
        1px solid rgba(255,255,255,0.70);

    box-shadow:
        0 12px 40px rgba(80,70,90,0.08);
}


/* Input fields */

div[data-testid="stForm"] div[data-baseweb="input"] {

    background:
        rgba(255,255,255,0.40);

    border-radius: 16px;

    border:
        1px solid #d7cbc6;
}


div[data-testid="stForm"] input {

    color: #354151 !important;
}


/* Form submit button */

div[data-testid="stFormSubmitButton"] > button {

    width: 100% !important;

    min-height: 70px !important;

    border-radius: 18px !important;

    border: none !important;

    background:
        linear-gradient(
            135deg,
            #a8abc9,
            #858caf
        ) !important;

    color: #354151 !important;

    font-family: Georgia, serif !important;

    font-size: 1.5rem !important;

    font-weight: 500 !important;

    margin-top: 12px !important;

    transition: all 0.25s ease !important;
}


div[data-testid="stFormSubmitButton"] > button:hover {

    transform: translateY(-3px);

    box-shadow:
        0 12px 28px
        rgba(100,100,140,0.25) !important;
}


/* =====================================================
   DASHBOARD
===================================================== */

.dashboard-welcome {

    text-align: center;

    padding: 40px 20px;

    margin-bottom: 30px;

    background:
        rgba(255,255,255,0.38);

    backdrop-filter: blur(15px);

    border-radius: 30px;

    border:
        1px solid rgba(255,255,255,0.70);

    box-shadow:
        0 12px 35px rgba(90,80,100,0.10);
}


.dashboard-db {

    font-size: 4rem;

    margin-bottom: 10px;
}


.dashboard-welcome h1 {

    font-size: 2.8rem;

    font-family: Georgia, serif;

    font-weight: 500;
}


.dashboard-welcome h1 span {

    color: #b47d70;
}


.dashboard-welcome p {

    color: #687080;

    font-size: 1.05rem;
}


/* Dashboard cards */

.dashboard-card {

    min-height: 190px;

    padding: 24px;

    margin-bottom: 22px;

    background:
        rgba(255,255,255,0.48);

    backdrop-filter: blur(14px);

    border-radius: 22px;

    border:
        1px solid rgba(255,255,255,0.70);

    box-shadow:
        0 10px 30px rgba(80,70,90,0.10);

    transition: all 0.25s ease;
}


.dashboard-card:hover {

    transform: translateY(-5px);

    background:
        rgba(255,255,255,0.70);

    box-shadow:
        0 16px 35px rgba(80,70,90,0.16);
}


.dashboard-icon {

    width: 55px;

    height: 55px;

    display: flex;

    align-items: center;

    justify-content: center;

    border-radius: 16px;

    font-size: 1.8rem;

    background:
        linear-gradient(
            135deg,
            rgba(174,177,208,0.45),
            rgba(239,196,177,0.40)
        );

    margin-bottom: 15px;
}


.dashboard-card h3 {

    font-family: Georgia, serif;

    font-size: 1.3rem;

    margin-bottom: 8px;
}


.dashboard-card p {

    color: #6f7480;

    font-size: 0.9rem;

    line-height: 1.5;
}


/* =========================================================
   NEW DASHBOARD — SIDEBAR
========================================================= */

.sb-logo-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 2px 18px;
    margin-bottom: 6px;
    border-bottom: 1px solid rgba(180,170,180,0.30);
}

.sb-logo-icon {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    background: linear-gradient(135deg, #cfd1e6, #f0d5c8);
    box-shadow: 0 4px 12px rgba(90,80,100,0.15);
    flex-shrink: 0;
}

.sb-logo-text h1 {
    font-family: Georgia, serif !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    color: #354151 !important;
    margin: 0 !important;
    line-height: 1.2 !important;
}

.sb-logo-text p {
    font-size: 0.72rem;
    color: #8a8f9a;
    margin: 0;
}

.sb-user-card {
    display: flex;
    align-items: center;
    gap: 12px;
    background: rgba(255,255,255,0.55);
    border: 1px solid rgba(255,255,255,0.70);
    border-radius: 16px;
    padding: 12px 14px;
    margin: 14px 0 10px;
}

.sb-user-avatar {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 1.05rem;
    color: #ffffff;
    background: linear-gradient(135deg, #d98f74, #c96c5b);
    flex-shrink: 0;
}

.sb-user-name {
    font-weight: 700;
    color: #354151;
    font-size: 0.95rem;
    line-height: 1.25;
}

.sb-user-sub {
    font-size: 0.75rem;
    color: #8a8f9a;
}

div.st-key-logout_btn_wrap div.stButton > button {
    background: rgba(255,255,255,0.7) !important;
    border: 1px solid #e3b6a6 !important;
    color: #c96c5b !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
    margin-bottom: 10px;
}

div.st-key-logout_btn_wrap div.stButton > button:hover {
    background: rgba(230,140,110,0.12) !important;
}

/* Custom nav items (buttons styled as pills) */
div[class*="st-key-nav_"] div.stButton > button {
    text-align: left !important;
    justify-content: flex-start !important;
    background: transparent !important;
    border: 1px solid transparent !important;
    color: #4a5364 !important;
    font-weight: 500 !important;
    border-radius: 12px !important;
    padding: 10px 14px !important;
    margin-bottom: 2px !important;
    box-shadow: none !important;
    width: 100%;
}

div[class*="st-key-nav_"] div.stButton > button:hover {
    background: rgba(127,132,159,0.10) !important;
    transform: none !important;
    box-shadow: none !important;
}

div[class*="st-key-nav_"] div.stButton > button p {
    text-align: left !important;
    font-size: 0.92rem !important;
}

div[class*="st-key-nav_active_"] div.stButton > button {
    background: rgba(230,140,110,0.16) !important;
    border: 1px solid rgba(230,140,110,0.35) !important;
    color: #c96c5b !important;
    font-weight: 700 !important;
    border-left: 3px solid #c96c5b !important;
}


/* =========================================================
   NEW DASHBOARD — TOP BAR + HERO
========================================================= */

.topbar {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 16px;
    margin-bottom: 6px;
}

.topbar-bell {
    position: relative;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255,255,255,0.55);
    border: 1px solid rgba(255,255,255,0.70);
    font-size: 1.1rem;
}

.topbar-bell-dot {
    position: absolute;
    top: 8px;
    right: 9px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #d9694f;
    border: 1.5px solid #f5f1ed;
}

.topbar-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    color: #ffffff;
    background: linear-gradient(135deg, #a3a6cf, #8085b3);
}

.dash-hero {
    position: relative;
    padding: 8px 4px 30px;
    overflow: hidden;
}

.dash-hero h1 {
    font-family: Georgia, serif !important;
    font-size: 2.3rem !important;
    color: #354151 !important;
    margin: 0 0 6px !important;
}

.dash-hero p {
    color: #687080;
    font-size: 1rem;
    margin: 0;
}

.dash-hero-graphic {
    position: absolute;
    right: 10px;
    top: -10px;
    width: 200px;
    height: 150px;
    pointer-events: none;
}

.dash-hero-dots {
    position: absolute;
    left: -10px;
    top: 30px;
    display: grid;
    grid-template-columns: repeat(3, 8px);
    gap: 12px;
    opacity: 0.5;
}

.dash-hero-dots span {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #d9a996;
}

.dash-hero-stack {
    position: absolute;
    right: 40px;
    top: 15px;
    width: 110px;
    height: 90px;
}

.dash-hero-layer {
    position: absolute;
    width: 118px;
    height: 42px;
    left: 0;
    border-radius: 50%;
    box-shadow: 0 10px 22px rgba(60,65,90,0.16), inset 0 2px 2px rgba(255,255,255,0.6);
}

.dash-hero-layer.l1 { top: 0; background: linear-gradient(135deg,#c9b6dd,#9f97c8); }
.dash-hero-layer.l2 { top: 26px; background: linear-gradient(135deg,#e7bcbd,#d99a9c); }
.dash-hero-layer.l3 { top: 52px; background: linear-gradient(135deg,#c3d3bc,#a3b89a); }


/* =========================================================
   NEW DASHBOARD — WORKSPACE STEP FLOW
========================================================= */

.workspace-card {
    background: rgba(255,255,255,0.65);
    backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,0.75);
    border-radius: 24px;
    padding: 28px 30px;
    box-shadow: 0 12px 35px rgba(90,80,100,0.08);
    margin-bottom: 22px;
}

.workspace-title {
    font-family: Georgia, serif;
    font-size: 1.25rem;
    color: #354151;
    font-weight: 700;
    display: inline-block;
    padding-bottom: 8px;
    border-bottom: 3px solid #d9a996;
    margin-bottom: 26px;
}

.step-flow {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
}

.step-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    width: 130px;
}

.step-circle {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    margin-bottom: 12px;
    box-shadow: 0 6px 16px rgba(60,65,90,0.12);
}

.step-circle.c1 { background: #ece9f7; color: #7f6fbf; }
.step-circle.c2 { background: #fce6dd; color: #d9714f; }
.step-circle.c3 { background: #dcefe0; color: #4a9d5f; }
.step-circle.c4 { background: #fdecd0; color: #d99a2b; }
.step-circle.c5 { background: #dbeafc; color: #3a86c8; }

.step-item h4 {
    font-size: 0.95rem;
    color: #354151;
    margin: 0 0 4px;
    font-weight: 700;
}

.step-item p {
    font-size: 0.78rem;
    color: #8a8f9a;
    margin: 0;
    line-height: 1.35;
}

.step-arrow {
    flex: 1;
    min-width: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #c9c0c5;
    font-size: 1.1rem;
    margin-top: 28px;
    border-top: 2px dashed #d9cfc9;
    position: relative;
}


/* =========================================================
   NEW DASHBOARD — RECENT QUERIES + QUICK START
========================================================= */

.section-card {
    background: rgba(255,255,255,0.65);
    backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,0.75);
    border-radius: 22px;
    padding: 22px 24px;
    box-shadow: 0 10px 30px rgba(90,80,100,0.08);
    height: 100%;
}

div.st-key-recent_queries_card,
div.st-key-quickstart_card {
    background: rgba(255,255,255,0.65);
    backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,0.75);
    border-radius: 22px;
    padding: 22px 24px;
    box-shadow: 0 10px 30px rgba(90,80,100,0.08);
    height: 100%;
}

.section-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
}

.section-card-title {
    font-family: Georgia, serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #354151;
    display: inline-block;
    padding-bottom: 6px;
    border-bottom: 3px solid #d9a996;
}

.section-card-link {
    font-size: 0.85rem;
    color: #7f849f;
    font-weight: 600;
    text-decoration: none;
}

.recent-query-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 13px 2px;
    border-bottom: 1px solid rgba(190,180,185,0.25);
    gap: 10px;
}

.recent-query-row:last-child {
    border-bottom: none;
}

.recent-query-left {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
}

.recent-query-icon {
    font-size: 1.1rem;
    flex-shrink: 0;
}

.recent-query-text {
    color: #354151;
    font-size: 0.9rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.recent-query-time {
    color: #a3a8b0;
    font-size: 0.78rem;
    flex-shrink: 0;
    margin-left: 10px;
}

.recent-query-chevron {
    color: #c2c7cf;
    flex-shrink: 0;
    margin-left: 6px;
}

.qs-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin-top: 18px;
}

div.st-key-qs_grid div.stButton > button {
    height: 78px !important;
    border-radius: 16px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    border: none !important;
    box-shadow: none !important;
}

div.st-key-qs_generate div.stButton > button {
    background: rgba(217,113,79,0.14) !important;
    color: #c9633f !important;
}
div.st-key-qs_voice div.stButton > button {
    background: rgba(127,111,191,0.14) !important;
    color: #6f5fb0 !important;
}
div.st-key-qs_practice div.stButton > button {
    background: rgba(74,157,95,0.14) !important;
    color: #3f8752 !important;
}
div.st-key-qs_validate div.stButton > button {
    background: rgba(217,154,43,0.16) !important;
    color: #b9822a !important;
}

div.st-key-qs_grid div.stButton > button:hover {
    transform: translateY(-2px) !important;
    filter: brightness(0.97);
}

div.st-key-recent_view_all div.stButton > button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #7f849f !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0 !important;
    width: auto !important;
}

div.st-key-recent_view_all div.stButton > button:hover {
    color: #c96c5b !important;
    transform: none !important;
}


</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
# Session state defaults
# --------------------------------------------------------------------------- #
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "last_nl_text" not in st.session_state:
    st.session_state.last_nl_text = ""
if "voice_transcript" not in st.session_state:
    st.session_state.voice_transcript = ""
if "auth_view" not in st.session_state:
    st.session_state.auth_view = "landing"  # "landing" -> "login" / "signup"


# --------------------------------------------------------------------------- #
# Auth screens
# --------------------------------------------------------------------------- #

def load_login_css():
    st.markdown("""
    <style>

    /* Remove Streamlit default layout */
    [data-testid="stHeader"] {
        display: none;
    }

    [data-testid="stSidebar"] {
        display: none;
    }

    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }

    /* Main background */
    .login-page {
        min-height: 100vh;
        width: 100%;
        position: relative;
        overflow: hidden;

        background:
            radial-gradient(
                circle at 0% 0%,
                rgba(198, 125, 110, 0.55),
                transparent 28%
            ),

            radial-gradient(
                circle at 100% 0%,
                rgba(219, 203, 192, 0.55),
                transparent 30%
            ),

            radial-gradient(
                circle at 100% 100%,
                rgba(121, 128, 164, 0.50),
                transparent 35%
            ),

            linear-gradient(
                135deg,
                #f4ede7 0%,
                #e8e6e7 45%,
                #e9e5e1 100%
            );

        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #2f3b4a;
    }


    /* Decorative circles */

    .circle-top-left {
        position: absolute;
        width: 520px;
        height: 520px;

        top: -280px;
        left: -80px;

        border-radius: 50%;

        border: 1px solid rgba(255, 255, 255, 0.45);

        background:
            radial-gradient(
                circle,
                rgba(200, 130, 120, 0.30),
                rgba(200, 130, 120, 0.05),
                transparent 70%
            );
    }


    .circle-right {
        position: absolute;

        width: 600px;
        height: 600px;

        right: -300px;
        bottom: -180px;

        border-radius: 50%;

        border: 1px solid rgba(255,255,255,0.35);
    }


    /* Database icon area */

    .db-icon-container {
        position: relative;

        width: 280px;
        height: 220px;

        margin: 0 auto 25px;
    }


    .db-circle {
        position: absolute;

        width: 300px;
        height: 300px;

        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);

        border-radius: 50%;

        border: 1px solid rgba(255,255,255,0.5);
    }


    .database-stack {
        position: absolute;

        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);

        width: 190px;
        height: 150px;
    }


    .database-layer {
        position: absolute;

        width: 200px;
        height: 70px;

        left: 0;

        border-radius: 50%;

        background:
            linear-gradient(
                135deg,
                #d5bfc7,
                #8d91b0
            );

        box-shadow:
            0 14px 30px rgba(60, 65, 90, 0.18),
            inset 0 2px 2px rgba(255,255,255,0.7);
    }


    .layer-one {
        top: 0;
    }


    .layer-two {
        top: 45px;

        background:
            linear-gradient(
                135deg,
                #d8c2c2,
                #9b92a6
            );
    }


    .layer-three {
        top: 90px;

        background:
            linear-gradient(
                135deg,
                #e0bba7,
                #b08e87
            );
    }


    /* Orbit */

    .orbit {
        position: absolute;

        width: 420px;
        height: 170px;

        top: 50%;
        left: 50%;

        border: 2px solid #777e9d;

        border-radius: 50%;

        transform: translate(-50%, -50%) rotate(-18deg);

        opacity: 0.65;
    }


    .orbit-dot-left {
        position: absolute;

        width: 20px;
        height: 20px;

        background: #8e93aa;

        border-radius: 50%;

        left: -5px;
        top: 70px;
    }


    .orbit-dot-right {
        position: absolute;

        width: 22px;
        height: 22px;

        background: #c89d86;

        border-radius: 50%;

        right: -8px;
        top: 70px;
    }


    /* Title */

    .main-title {
        text-align: center;

        font-family: Georgia, serif;

        font-size: 4.8rem;

        font-weight: 500;

        letter-spacing: -2px;

        line-height: 1.05;

        color: #354151;

        margin-top: 15px;
    }


    .sql-highlight {
        color: #b47d70;
    }


    /* Decorative line */

    .title-divider {
        display: flex;

        align-items: center;
        justify-content: center;

        gap: 12px;

        margin: 28px 0 40px;
    }


    .title-divider::before,
    .title-divider::after {

        content: "";

        width: 110px;

        height: 1px;

        background: linear-gradient(
            90deg,
            transparent,
            #cbb6a8
        );
    }


    .title-divider::after {
        background: linear-gradient(
            90deg,
            #cbb6a8,
            transparent
        );
    }


    .diamond {
        color: #cbb6a8;

        font-size: 25px;
    }


    /* Landing page action buttons (Login / Sign Up) */

    .landing-actions {
        display: flex;
        gap: 30px;
        max-width: 620px;
        margin: 0 auto;
        padding: 0 20px;
    }

    div.st-key-landing_buttons div.stButton > button {
        min-height: 78px !important;
        border-radius: 20px !important;
        font-family: Georgia, serif !important;
        font-size: 1.6rem !important;
        font-weight: 500 !important;
        background: rgba(255,255,255,0.28) !important;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease !important;
    }

    div.st-key-btn_login_wrap div.stButton > button {
        border: 1.5px solid #9ba1bd !important;
        color: #354151 !important;
    }

    div.st-key-btn_signup_wrap div.stButton > button {
        border: 1.5px solid #c99f8f !important;
        color: #354151 !important;
    }

    div.st-key-landing_buttons div.stButton > button:hover {
        transform: translateY(-4px);
        background: rgba(255,255,255,0.55) !important;
        box-shadow: 0 12px 30px rgba(70,80,110,0.18) !important;
    }

    /* Back link on the auth-forms page */
    div.st-key-back_to_landing div.stButton > button {
        background: transparent !important;
        border: none !important;
        color: #687080 !important;
        font-size: 0.95rem !important;
        box-shadow: none !important;
        padding-left: 4px !important;
    }

    div.st-key-back_to_landing div.stButton > button:hover {
        color: #354151 !important;
        transform: none;
        background: transparent !important;
    }


    /* Bottom dots */

    .dot-pattern {

        position: absolute;

        left: 50px;
        bottom: 60px;

        display: grid;

        grid-template-columns: repeat(5, 10px);

        gap: 18px;

        opacity: 0.45;
    }


    .dot-pattern span {

        width: 7px;
        height: 7px;

        border-radius: 50%;

        background: #b5a9a8;
    }


    /* Mobile */

    @media (max-width: 768px) {

        .main-title {
            font-size: 3rem;
        }

        .db-icon-container {
            transform: scale(0.8);
        }

        div.stButton > button {
            min-height: 80px;
            font-size: 1.3rem !important;
        }

    }

    </style>
    """, unsafe_allow_html=True)


def render_landing_page():
    """
    PAGE 1 — the hero/landing screen (matches the "Natural Language to SQL
    Query Generator" title screen with just Login / Sign Up buttons).
    """

    load_login_css()

    landing_html = (
        '<div class="landing-container">'
        '<div class="db-icon-container">'
        '<div class="db-circle"></div>'
        '<div class="orbit"><div class="orbit-dot-left"></div><div class="orbit-dot-right"></div></div>'
        '<div class="database-stack">'
        '<div class="database-layer layer-one"></div>'
        '<div class="database-layer layer-two"></div>'
        '<div class="database-layer layer-three"></div>'
        '</div>'
        '</div>'
        '<div class="main-title">Natural Language<br>to <span class="sql-highlight">SQL</span> Query Generator</div>'
        '<div class="title-divider"><span class="diamond">✦</span></div>'
        '</div>'
    )
    st.markdown(landing_html, unsafe_allow_html=True)

    # Centered Login / Sign Up buttons -> take the user to page 2 (the forms)
    with st.container(key="landing_buttons"):
        _, col_center, _ = st.columns([1, 2, 1])
        with col_center:
            b1, b2 = st.columns(2, gap="large")
            with b1:
                with st.container(key="btn_login_wrap"):
                    if st.button("→   Login", use_container_width=True, key="go_login"):
                        st.session_state.auth_view = "login"
                        st.rerun()
            with b2:
                with st.container(key="btn_signup_wrap"):
                    if st.button("+   Sign Up", use_container_width=True, key="go_signup"):
                        st.session_state.auth_view = "signup"
                        st.rerun()


def render_auth_forms():
    """
    PAGE 2 — the actual Login / Sign Up form cards, reached after the user
    taps a button on the landing page.
    """

    load_login_css()

    with st.container(key="back_to_landing"):
        if st.button("← Back to Home", key="back_home_btn"):
            st.session_state.auth_view = "landing"
            st.rerun()

    col1, col2 = st.columns(2, gap="large")

    # ---------------- LOGIN ----------------

    with col1:

        login_card_html = (
            '<div class="auth-card login-card">'
            '<div class="auth-icon login-icon">👤</div>'
            '<h1>Welcome Back</h1>'
            '<p class="auth-subtitle">Login to continue</p>'
            '</div>'
        )
        st.markdown(login_card_html, unsafe_allow_html=True)


        with st.form("login_form"):

            login_user = st.text_input(
                "Username",
                placeholder="Username",
                key="login_username"
            )

            login_pass = st.text_input(
                "Password",
                type="password",
                placeholder="Password",
                key="login_password"
            )

            submitted = st.form_submit_button(
                "→   Login",
                use_container_width=True
            )


            if submitted:

                if db.verify_user(login_user, login_pass):

                    st.session_state.logged_in = True

                    st.session_state.username = login_user.strip()

                    st.session_state.auth_view = "landing"

                    st.rerun()

                else:

                    st.error("Invalid username or password.")


    # ---------------- SIGNUP ----------------

    with col2:

        signup_card_html = (
            '<div class="auth-card signup-card">'
            '<div class="auth-icon signup-icon">👤<span class="auth-icon-plus-badge">+</span></div>'
            '<h1>Create Account</h1>'
            '<p class="auth-subtitle">Sign up to get started</p>'
            '</div>'
        )
        st.markdown(signup_card_html, unsafe_allow_html=True)


        with st.form("signup_form"):

            new_user = st.text_input(
                "Username",
                placeholder="Choose a username",
                key="signup_username"
            )

            new_email = st.text_input(
                "Email",
                placeholder="Enter your email"
            )

            new_pass = st.text_input(
                "Password",
                type="password",
                placeholder="Create password",
                key="signup_password"
            )

            new_pass2 = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="Confirm password",
                key="signup_password2"
            )

            submitted = st.form_submit_button(
                "+   Sign Up",
                use_container_width=True
            )


            if submitted:

                if new_pass != new_pass2:

                    st.error("Passwords do not match.")

                else:

                    ok, msg = db.create_user(
                        new_user,
                        new_pass
                    )

                    if ok:

                        st.success(
                            msg + " You can now log in."
                        )

                    else:

                        st.error(msg)


# --------------------------------------------------------------------------- #
# Shared: display a generated SQL result (used by Text-to-SQL and Voice-to-SQL)
# --------------------------------------------------------------------------- #
def render_result_block(result: engine.SQLResult, natural_language: str):
    if result.warning:
        st.markdown(f'<span class="pill pill-warning">Notice</span> {result.warning}', unsafe_allow_html=True)

    engine_pill = "AI-assisted" if result.engine_used == "ai" else "Rule-based engine"
    pill_class = "pill-accent" if result.engine_used == "ai" else "pill-success"
    st.markdown(f'<span class="pill {pill_class}">{engine_pill}</span>', unsafe_allow_html=True)

    st.markdown("#### Generated SQL")
    st.markdown(f'<div class="sql-box">{result.sql}</div>', unsafe_allow_html=True)

    st.markdown("#### Explanation")
    st.write(result.explanation)

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        st.download_button(
            "📋 Copy (download .sql)",
            data=result.sql,
            file_name="query.sql",
            mime="text/plain",
            use_container_width=True,
        )
    with c2:
        if st.button("💾 Save Query", use_container_width=True, key=f"save_{hash(result.sql)}"):
            db.save_query(st.session_state.username, natural_language, result.sql, result.explanation)
            st.success("Query saved!")

    steps_html = viz.build_query_steps_html(result.sql)
    if steps_html:
        st.markdown("#### 🔎 Step-by-Step Query Explanation")
        st.caption("Illustrative sample data — showing how WHERE and SELECT shape the result.")
        st.markdown(steps_html, unsafe_allow_html=True)

    st.markdown("#### 🗳️ Feedback")
    fb1, fb2, fb3, fb4 = st.columns(4)
    feedback_map = {
        fb1: ("✅ Correct", "correct"),
        fb2: ("❌ Incorrect", "incorrect"),
        fb3: ("💡 Suggestion", "suggestion"),
        fb4: ("🚩 Report Issue", "report"),
    }
    for col, (label, ftype) in feedback_map.items():
        with col:
            if st.button(label, key=f"fb_{ftype}_{hash(result.sql)}", use_container_width=True):
                db.add_feedback(st.session_state.username, result.sql, ftype)
                st.toast(f"Thanks! Feedback recorded: {label}")


# --------------------------------------------------------------------------- #
# Feature pages
# --------------------------------------------------------------------------- #
def page_text_to_sql():
    st.header("💬 Text-to-SQL")
    st.caption("Type any SQL-related request in plain English.")
    example = "e.g. Show all employees from the sales department with salary greater than 50000 order by salary descending"
    nl_text = st.text_area("Your request", placeholder=example, height=100, key="text2sql_input")

    if st.button("⚡ Generate SQL", type="primary"):
        if not nl_text.strip():
            st.warning("Please enter a request first.")
        else:
            with st.spinner("Analyzing your request..."):
                result = engine.generate_sql(nl_text, st.session_state.api_key)
            st.session_state.last_result = result
            st.session_state.last_nl_text = nl_text

    if st.session_state.last_result and st.session_state.last_nl_text == st.session_state.get("text2sql_input", st.session_state.last_nl_text):
        st.markdown("---")
        render_result_block(st.session_state.last_result, st.session_state.last_nl_text)


def page_voice_to_sql():
    st.header("🎙️ Voice-to-SQL")
    st.caption("Record your request, review/edit the transcript, then generate SQL.")

    audio_value = st.audio_input("Record your request")

    if audio_value is not None:
        st.audio(audio_value)

        if st.button("📝 Transcribe Audio", key="transcribe_audio_btn"):
            with st.spinner("Transcribing..."):
                transcript, error = _transcribe_audio(audio_value)

            if transcript:
                st.session_state.voice_transcript = transcript
                st.success("Audio transcribed successfully!")
            else:
                st.error(error or "Could not transcribe the audio.")

    edited_text = st.text_area(
        "Recognized text (edit if needed before generating)",
        value=st.session_state.get("voice_transcript", ""),
        height=100,
    )

    if st.button("⚡ Generate SQL from Voice Text", type="primary"):
        if not edited_text.strip():
            st.warning("Nothing to generate from — record or type your request first.")
        else:
            with st.spinner("Analyzing your request..."):
                result = engine.generate_sql(
                    edited_text,
                    st.session_state.api_key
                )

            st.session_state.last_result = result
            st.session_state.last_nl_text = edited_text
            st.markdown("---")
            render_result_block(result, edited_text)

def _transcribe_audio(audio_value):
    import speech_recognition as sr

    try:
        recognizer = sr.Recognizer()

        # Streamlit audio_input provides WAV audio
        audio_value.seek(0)

        with sr.AudioFile(audio_value) as source:
            audio_data = recognizer.record(source)

        text = recognizer.recognize_google(
            audio_data,
            language="en-IN"
        )

        return text.strip(), None

    except sr.UnknownValueError:
        return "", "Could not understand the audio. Please speak clearly."

    except sr.RequestError as e:
        return "", f"Google Speech Recognition error: {e}"

    except Exception as e:
        return "", f"Transcription error: {type(e).__name__}: {e}"

    
SQL_NOTES = {

    "📘 SQL Basics": {

        "SELECT & FROM": (
            "### Syntax\n"
            "`SELECT column1, column2 FROM table_name;`\n\n"

            "### Explanation\n"
            "`SELECT` chooses the columns you want to retrieve, while `FROM` "
            "specifies the table containing the data.\n\n"

            "### Example\n"
            "`SELECT name, salary FROM employees;`\n\n"

            "### More Information\n"
            "- Use `*` to select all columns.\n"
            "- Select one or multiple columns.\n"
            "- Use `AS` to give a temporary name to a column.\n\n"

            "**Example:** `SELECT name AS employee_name FROM employees;`"
        ),

        "DISTINCT": (
            "### Syntax\n"
            "`SELECT DISTINCT column_name FROM table_name;`\n\n"

            "### Explanation\n"
            "`DISTINCT` removes duplicate values from the result.\n\n"

            "### Example\n"
            "`SELECT DISTINCT department FROM employees;`\n\n"

            "If multiple columns are selected, SQL removes duplicate combinations "
            "of those values."
        ),

        "WHERE": (
            "### Syntax\n"
            "`SELECT * FROM table_name WHERE condition;`\n\n"

            "### Explanation\n"
            "`WHERE` filters rows based on a condition.\n\n"

            "### Example\n"
            "`SELECT * FROM employees WHERE salary > 50000;`\n\n"

            "### Common Operators\n"
            "- `=` Equal to\n"
            "- `>` Greater than\n"
            "- `<` Less than\n"
            "- `>=` Greater than or equal to\n"
            "- `<=` Less than or equal to\n"
            "- `!=` or `<>` Not equal to"
        ),

        "LIKE": (
            "### Syntax\n"
            "`SELECT * FROM table_name WHERE column_name LIKE pattern;`\n\n"

            "### Explanation\n"
            "`LIKE` searches for a specific text pattern.\n\n"

            "### Wildcards\n"
            "- `%` → Zero or more characters\n"
            "- `_` → Exactly one character\n\n"

            "### Examples\n"
            "`WHERE name LIKE 'A%'` → Names starting with A\n\n"
            "`WHERE name LIKE '%son'` → Names ending with son\n\n"
            "`WHERE name LIKE '%ar%'` → Names containing ar"
        ),

        "IN": (
            "### Syntax\n"
            "`SELECT * FROM table_name WHERE column_name IN (value1, value2);`\n\n"

            "### Explanation\n"
            "`IN` checks whether a value matches any value in a list.\n\n"

            "### Example\n"
            "`SELECT * FROM employees "
            "WHERE department IN ('HR', 'IT', 'Sales');`"
        ),

        "BETWEEN": (
            "### Syntax\n"
            "`SELECT * FROM table_name "
            "WHERE column_name BETWEEN value1 AND value2;`\n\n"

            "### Explanation\n"
            "`BETWEEN` selects values within a specified range.\n\n"

            "### Example\n"
            "`SELECT * FROM products WHERE price BETWEEN 100 AND 500;`\n\n"

            "The starting and ending values are included."
        ),

        "NULL Values": (
            "### Syntax\n"
            "`SELECT * FROM table_name WHERE column_name IS NULL;`\n\n"

            "### Explanation\n"
            "`NULL` represents missing or unknown data.\n\n"

            "### Examples\n"
            "`WHERE last_login IS NULL`\n\n"
            "`WHERE last_login IS NOT NULL`\n\n"

            "⚠️ Do not use `= NULL`. Always use `IS NULL` or `IS NOT NULL`."
        ),
    },


    "🔗 Working with Tables": {

        "JOIN": (
            "### Syntax\n"
            "`SELECT columns FROM table1 "
            "JOIN table2 ON table1.id = table2.id;`\n\n"

            "### Explanation\n"
            "`JOIN` combines data from two or more tables using related columns.\n\n"

            "### Example\n"
            "`SELECT employees.name, departments.department_name "
            "FROM employees "
            "JOIN departments "
            "ON employees.dept_id = departments.id;`\n\n"

            "### Types of JOIN\n"
            "- `INNER JOIN` → Matching rows from both tables.\n"
            "- `LEFT JOIN` → All rows from the left table.\n"
            "- `RIGHT JOIN` → All rows from the right table.\n"
            "- `FULL OUTER JOIN` → Matching and non-matching rows from both tables."
        ),

        "Aliases (AS)": (
            "### Syntax\n"
            "`SELECT column_name AS alias_name FROM table_name;`\n\n"

            "### Explanation\n"
            "Aliases provide temporary names for columns or tables.\n\n"

            "### Column Example\n"
            "`SELECT name AS employee_name FROM employees;`\n\n"

            "### Table Example\n"
            "`SELECT e.name FROM employees AS e;`"
        ),

        "CREATE TABLE": (
            "### Syntax\n"
            "`CREATE TABLE table_name (column1 datatype, column2 datatype);`\n\n"

            "### Example\n"
            "`CREATE TABLE employees (`\n"
            "`id INT,`\n"
            "`name VARCHAR(100),`\n"
            "`salary DECIMAL`\n"
            "`);`\n\n"

            "`CREATE TABLE` creates a new table and defines its columns."
        ),

        "ALTER TABLE": (
            "### Syntax\n"
            "`ALTER TABLE table_name ADD column_name datatype;`\n\n"

            "### Example\n"
            "`ALTER TABLE employees ADD email VARCHAR(100);`\n\n"

            "`ALTER TABLE` is used to modify the structure of an existing table."
        ),

        "DROP TABLE": (
            "### Syntax\n"
            "`DROP TABLE table_name;`\n\n"

            "### Example\n"
            "`DROP TABLE employees;`\n\n"

            "⚠️ This permanently removes the table and its data."
        ),
    },


    "📊 Data Analysis": {

        "Aggregate Functions": (
            "Aggregate functions perform calculations on multiple rows and return "
            "a single result.\n\n"

            "### Common Functions\n"
            "- `COUNT()` → Counts rows\n"
            "- `SUM()` → Adds values\n"
            "- `AVG()` → Calculates average\n"
            "- `MAX()` → Finds largest value\n"
            "- `MIN()` → Finds smallest value\n\n"

            "### Examples\n"
            "`SELECT COUNT(*) FROM employees;`\n\n"
            "`SELECT AVG(salary) FROM employees;`\n\n"
            "`SELECT MAX(price) FROM products;`"
        ),

        "GROUP BY & HAVING": (
            "### Syntax\n"
            "`SELECT column, COUNT(*) FROM table_name "
            "GROUP BY column HAVING condition;`\n\n"

            "### Explanation\n"
            "`GROUP BY` groups rows with the same values.\n"
            "`HAVING` filters those groups.\n\n"

            "### Example\n"
            "`SELECT department, COUNT(*) "
            "FROM employees "
            "GROUP BY department "
            "HAVING COUNT(*) > 5;`\n\n"

            "### WHERE vs HAVING\n"
            "- `WHERE` filters rows before grouping.\n"
            "- `HAVING` filters groups after grouping."
        ),

        "ORDER BY": (
            "### Syntax\n"
            "`SELECT * FROM table_name ORDER BY column_name ASC;`\n\n"

            "### Explanation\n"
            "`ORDER BY` sorts the result.\n\n"

            "- `ASC` → Ascending order\n"
            "- `DESC` → Descending order\n\n"

            "### Example\n"
            "`SELECT * FROM employees ORDER BY salary DESC;`\n\n"

            "Multiple columns:\n"
            "`ORDER BY department ASC, salary DESC;`"
        ),

        "LIMIT": (
            "### Syntax\n"
            "`SELECT * FROM table_name LIMIT number;`\n\n"

            "### Explanation\n"
            "`LIMIT` restricts the number of rows returned.\n\n"

            "### Example\n"
            "`SELECT * FROM employees LIMIT 5;`"
        ),
    },


    "✏️ Modifying Data": {

        "INSERT": (
            "### Syntax\n"
            "`INSERT INTO table_name (column1, column2) "
            "VALUES (value1, value2);`\n\n"

            "### Explanation\n"
            "`INSERT` adds new rows to a table.\n\n"

            "### Example\n"
            "`INSERT INTO employees (name, salary) "
            "VALUES ('John', 50000);`"
        ),

        "UPDATE": (
            "### Syntax\n"
            "`UPDATE table_name SET column_name = value WHERE condition;`\n\n"

            "### Explanation\n"
            "`UPDATE` modifies existing records.\n\n"

            "### Example\n"
            "`UPDATE employees SET salary = 60000 WHERE id = 5;`\n\n"

            "⚠️ Without `WHERE`, all rows may be updated."
        ),

        "DELETE": (
            "### Syntax\n"
            "`DELETE FROM table_name WHERE condition;`\n\n"

            "### Explanation\n"
            "`DELETE` removes rows from a table.\n\n"

            "### Example\n"
            "`DELETE FROM employees WHERE id = 10;`\n\n"

            "⚠️ Without `WHERE`, all rows may be deleted."
        ),
    },


    "🧠 Advanced SQL": {

        "Subqueries": (
            "### Explanation\n"
            "A subquery is a SQL query written inside another query.\n\n"

            "### Example\n"
            "`SELECT name FROM employees "
            "WHERE dept_id IN (`\n"
            "`SELECT id FROM departments WHERE region = 'West'`\n"
            "`);`\n\n"

            "Subqueries can be used with `WHERE`, `FROM`, `SELECT`, and `HAVING`."
        ),

        "SQL Query Execution Order": (
            "### Query Writing Order\n"
            "`SELECT → FROM → WHERE → GROUP BY → HAVING → ORDER BY → LIMIT`\n\n"

            "### Conceptual Execution Order\n"
            "1. `FROM` → Select source table.\n"
            "2. `JOIN` → Combine tables.\n"
            "3. `WHERE` → Filter rows.\n"
            "4. `GROUP BY` → Create groups.\n"
            "5. `HAVING` → Filter groups.\n"
            "6. `SELECT` → Select columns.\n"
            "7. `ORDER BY` → Sort results.\n"
            "8. `LIMIT` → Restrict rows."
        ),
    },
}

PRACTICE_QUESTIONS = {

    "📘 SELECT & FROM": [
        {
            "question": "Write a query to get all columns from the customers table.",
            "answer_keywords": ["select", "*", "from", "customers"],
            "sample_answer": "SELECT * FROM customers;",
        },
        {
            "question": "Write a query to get only the name column from the employees table.",
            "answer_keywords": ["select", "name", "from", "employees"],
            "sample_answer": "SELECT name FROM employees;",
        },
        {
            "question": "Write a query to get the name and salary columns from the employees table.",
            "answer_keywords": ["select", "name", "salary", "from", "employees"],
            "sample_answer": "SELECT name, salary FROM employees;",
        },
        {
            "question": "Write a query to get all columns from the products table.",
            "answer_keywords": ["select", "*", "from", "products"],
            "sample_answer": "SELECT * FROM products;",
        },
        {
            "question": "Write a query to get customer_id and customer_name from the customers table.",
            "answer_keywords": ["select", "customer_id", "customer_name", "from", "customers"],
            "sample_answer": "SELECT customer_id, customer_name FROM customers;",
        },
        {
            "question": "Write a query to get the email column from the users table.",
            "answer_keywords": ["select", "email", "from", "users"],
            "sample_answer": "SELECT email FROM users;",
        },
        {
            "question": "Write a query to get product_name and price from the products table.",
            "answer_keywords": ["select", "product_name", "price", "from", "products"],
            "sample_answer": "SELECT product_name, price FROM products;",
        },
        {
            "question": "Write a query to get all columns from the orders table.",
            "answer_keywords": ["select", "*", "from", "orders"],
            "sample_answer": "SELECT * FROM orders;",
        },
        {
            "question": "Write a query to get id, name, and department from the employees table.",
            "answer_keywords": ["select", "id", "name", "department", "from", "employees"],
            "sample_answer": "SELECT id, name, department FROM employees;",
        },
        {
            "question": "Write a query to get the title column from the books table.",
            "answer_keywords": ["select", "title", "from", "books"],
            "sample_answer": "SELECT title FROM books;",
        },
    ],

    "🔍 WHERE & Operators": [
        {
            "question": "Find all products with a price greater than 100.",
            "answer_keywords": ["select", "from", "products", "where", "price", ">", "100"],
            "sample_answer": "SELECT * FROM products WHERE price > 100;",
        },
        {
            "question": "Find employees with a salary greater than or equal to 50000.",
            "answer_keywords": ["select", "employees", "where", "salary", ">=", "50000"],
            "sample_answer": "SELECT * FROM employees WHERE salary >= 50000;",
        },
        {
            "question": "Find students whose marks are less than 40.",
            "answer_keywords": ["select", "students", "where", "marks", "<", "40"],
            "sample_answer": "SELECT * FROM students WHERE marks < 40;",
        },
        {
            "question": "Find users whose age is equal to 25.",
            "answer_keywords": ["select", "users", "where", "age", "=", "25"],
            "sample_answer": "SELECT * FROM users WHERE age = 25;",
        },
        {
            "question": "Find employees who are not in the HR department.",
            "answer_keywords": ["select", "employees", "where", "department", "!=", "hr"],
            "sample_answer": "SELECT * FROM employees WHERE department != 'HR';",
        },
        {
            "question": "Find products with a price between 100 and 500.",
            "answer_keywords": ["select", "products", "where", "price", "between", "100", "500"],
            "sample_answer": "SELECT * FROM products WHERE price BETWEEN 100 AND 500;",
        },
        {
            "question": "Find employees working in either IT or HR.",
            "answer_keywords": ["select", "employees", "where", "department", "in", "it", "hr"],
            "sample_answer": "SELECT * FROM employees WHERE department IN ('IT', 'HR');",
        },
        {
            "question": "Find employees with salary greater than 50000 and department IT.",
            "answer_keywords": ["select", "employees", "where", "salary", ">", "50000", "and", "department", "it"],
            "sample_answer": "SELECT * FROM employees WHERE salary > 50000 AND department = 'IT';",
        },
        {
            "question": "Find users whose name starts with A.",
            "answer_keywords": ["select", "users", "where", "name", "like", "a%"],
            "sample_answer": "SELECT * FROM users WHERE name LIKE 'A%';",
        },
        {
            "question": "Find users who have not logged in.",
            "answer_keywords": ["select", "users", "where", "last_login", "is", "null"],
            "sample_answer": "SELECT * FROM users WHERE last_login IS NULL;",
        },
    ],

    "🔗 JOIN": [
        {
            "question": "Display employee names with their department names.",
            "answer_keywords": ["select", "employees", "departments", "join", "on"],
            "sample_answer": "SELECT employees.name, departments.department_name FROM employees JOIN departments ON employees.dept_id = departments.id;",
        },
        {
            "question": "Join orders with customers using customer_id.",
            "answer_keywords": ["select", "orders", "customers", "join", "customer_id"],
            "sample_answer": "SELECT * FROM orders JOIN customers ON orders.customer_id = customers.id;",
        },
        {
            "question": "Get all employees and their departments using INNER JOIN.",
            "answer_keywords": ["select", "employees", "inner", "join", "departments", "on"],
            "sample_answer": "SELECT * FROM employees INNER JOIN departments ON employees.dept_id = departments.id;",
        },
        {
            "question": "Get all customers and their orders, including customers without orders.",
            "answer_keywords": ["select", "customers", "left", "join", "orders", "on"],
            "sample_answer": "SELECT * FROM customers LEFT JOIN orders ON customers.id = orders.customer_id;",
        },
        {
            "question": "Display product names with their category names.",
            "answer_keywords": ["select", "products", "categories", "join", "category_id"],
            "sample_answer": "SELECT products.product_name, categories.category_name FROM products JOIN categories ON products.category_id = categories.id;",
        },
        {
            "question": "Get student names and course names from students and courses.",
            "answer_keywords": ["select", "students", "courses", "join", "on"],
            "sample_answer": "SELECT students.name, courses.course_name FROM students JOIN courses ON students.course_id = courses.id;",
        },
        {
            "question": "Get all employees and matching projects using LEFT JOIN.",
            "answer_keywords": ["select", "employees", "left", "join", "projects"],
            "sample_answer": "SELECT * FROM employees LEFT JOIN projects ON employees.id = projects.employee_id;",
        },
        {
            "question": "Join books with authors using author_id.",
            "answer_keywords": ["select", "books", "authors", "join", "author_id"],
            "sample_answer": "SELECT books.title, authors.name FROM books JOIN authors ON books.author_id = authors.id;",
        },
        {
            "question": "Get order details with customer names.",
            "answer_keywords": ["select", "orders", "customers", "join", "customer_id"],
            "sample_answer": "SELECT orders.id, customers.name FROM orders JOIN customers ON orders.customer_id = customers.id;",
        },
        {
            "question": "Display all departments and employees using LEFT JOIN.",
            "answer_keywords": ["select", "departments", "left", "join", "employees"],
            "sample_answer": "SELECT * FROM departments LEFT JOIN employees ON departments.id = employees.dept_id;",
        },
    ],

    "📊 GROUP BY & HAVING": [
        {
            "question": "Count the number of orders for each customer.",
            "answer_keywords": ["select", "customer_id", "count", "orders", "group by"],
            "sample_answer": "SELECT customer_id, COUNT(*) FROM orders GROUP BY customer_id;",
        },
        {
            "question": "Count employees in each department.",
            "answer_keywords": ["select", "department", "count", "employees", "group by"],
            "sample_answer": "SELECT department, COUNT(*) FROM employees GROUP BY department;",
        },
        {
            "question": "Find the average salary for each department.",
            "answer_keywords": ["select", "department", "avg", "salary", "employees", "group by"],
            "sample_answer": "SELECT department, AVG(salary) FROM employees GROUP BY department;",
        },
        {
            "question": "Find departments with more than 5 employees.",
            "answer_keywords": ["select", "department", "count", "employees", "group by", "having"],
            "sample_answer": "SELECT department, COUNT(*) FROM employees GROUP BY department HAVING COUNT(*) > 5;",
        },
        {
            "question": "Find the total sales for each product.",
            "answer_keywords": ["select", "product_id", "sum", "sales", "group by"],
            "sample_answer": "SELECT product_id, SUM(amount) FROM sales GROUP BY product_id;",
        },
        {
            "question": "Find categories with more than 10 products.",
            "answer_keywords": ["select", "category_id", "count", "products", "group by", "having"],
            "sample_answer": "SELECT category_id, COUNT(*) FROM products GROUP BY category_id HAVING COUNT(*) > 10;",
        },
        {
            "question": "Find the maximum salary in each department.",
            "answer_keywords": ["select", "department", "max", "salary", "employees", "group by"],
            "sample_answer": "SELECT department, MAX(salary) FROM employees GROUP BY department;",
        },
        {
            "question": "Find customers who placed more than 3 orders.",
            "answer_keywords": ["select", "customer_id", "count", "orders", "group by", "having"],
            "sample_answer": "SELECT customer_id, COUNT(*) FROM orders GROUP BY customer_id HAVING COUNT(*) > 3;",
        },
        {
            "question": "Find the minimum price in each category.",
            "answer_keywords": ["select", "category_id", "min", "price", "products", "group by"],
            "sample_answer": "SELECT category_id, MIN(price) FROM products GROUP BY category_id;",
        },
        {
            "question": "Find departments where the average salary is greater than 60000.",
            "answer_keywords": ["select", "department", "avg", "salary", "group by", "having"],
            "sample_answer": "SELECT department, AVG(salary) FROM employees GROUP BY department HAVING AVG(salary) > 60000;",
        },
    ],

    "↕️ ORDER BY & LIMIT": [
        {
            "question": "Display all employees sorted by salary in descending order.",
            "answer_keywords": ["select", "employees", "order by", "salary", "desc"],
            "sample_answer": "SELECT * FROM employees ORDER BY salary DESC;",
        },
        {
            "question": "Display all products sorted by price in ascending order.",
            "answer_keywords": ["select", "products", "order by", "price", "asc"],
            "sample_answer": "SELECT * FROM products ORDER BY price ASC;",
        },
        {
            "question": "Show the first 5 employees.",
            "answer_keywords": ["select", "employees", "limit", "5"],
            "sample_answer": "SELECT * FROM employees LIMIT 5;",
        },
        {
            "question": "Show the top 10 most expensive products.",
            "answer_keywords": ["select", "products", "order by", "price", "desc", "limit", "10"],
            "sample_answer": "SELECT * FROM products ORDER BY price DESC LIMIT 10;",
        },
        {
            "question": "Sort students by marks from highest to lowest.",
            "answer_keywords": ["select", "students", "order by", "marks", "desc"],
            "sample_answer": "SELECT * FROM students ORDER BY marks DESC;",
        },
        {
            "question": "Show the first 3 customers alphabetically.",
            "answer_keywords": ["select", "customers", "order by", "name", "asc", "limit", "3"],
            "sample_answer": "SELECT * FROM customers ORDER BY name ASC LIMIT 3;",
        },
        {
            "question": "Sort employees first by department and then by salary descending.",
            "answer_keywords": ["select", "employees", "order by", "department", "asc", "salary", "desc"],
            "sample_answer": "SELECT * FROM employees ORDER BY department ASC, salary DESC;",
        },
        {
            "question": "Show the 20 newest orders based on order_date.",
            "answer_keywords": ["select", "orders", "order by", "order_date", "desc", "limit", "20"],
            "sample_answer": "SELECT * FROM orders ORDER BY order_date DESC LIMIT 20;",
        },
        {
            "question": "Show the 5 cheapest products.",
            "answer_keywords": ["select", "products", "order by", "price", "asc", "limit", "5"],
            "sample_answer": "SELECT * FROM products ORDER BY price ASC LIMIT 5;",
        },
        {
            "question": "Sort books by title alphabetically.",
            "answer_keywords": ["select", "books", "order by", "title", "asc"],
            "sample_answer": "SELECT * FROM books ORDER BY title ASC;",
        },
    ],

    "🔢 Aggregate Functions": [
        {
            "question": "Count the total number of employees.",
            "answer_keywords": ["select", "count", "employees"],
            "sample_answer": "SELECT COUNT(*) FROM employees;",
        },
        {
            "question": "Find the average salary of employees.",
            "answer_keywords": ["select", "avg", "salary", "employees"],
            "sample_answer": "SELECT AVG(salary) FROM employees;",
        },
        {
            "question": "Find the highest salary.",
            "answer_keywords": ["select", "max", "salary", "employees"],
            "sample_answer": "SELECT MAX(salary) FROM employees;",
        },
        {
            "question": "Find the lowest product price.",
            "answer_keywords": ["select", "min", "price", "products"],
            "sample_answer": "SELECT MIN(price) FROM products;",
        },
        {
            "question": "Find the total sales amount.",
            "answer_keywords": ["select", "sum", "amount", "sales"],
            "sample_answer": "SELECT SUM(amount) FROM sales;",
        },
        {
            "question": "Count the total number of customers.",
            "answer_keywords": ["select", "count", "customers"],
            "sample_answer": "SELECT COUNT(*) FROM customers;",
        },
        {
            "question": "Find the average product price.",
            "answer_keywords": ["select", "avg", "price", "products"],
            "sample_answer": "SELECT AVG(price) FROM products;",
        },
        {
            "question": "Find the maximum marks scored by a student.",
            "answer_keywords": ["select", "max", "marks", "students"],
            "sample_answer": "SELECT MAX(marks) FROM students;",
        },
        {
            "question": "Find the minimum salary of employees.",
            "answer_keywords": ["select", "min", "salary", "employees"],
            "sample_answer": "SELECT MIN(salary) FROM employees;",
        },
        {
            "question": "Find the total quantity of products sold.",
            "answer_keywords": ["select", "sum", "quantity", "sales"],
            "sample_answer": "SELECT SUM(quantity) FROM sales;",
        },
    ],

    "➕ INSERT": [
        {
            "question": "Insert a new employee named John with a salary of 50000.",
            "answer_keywords": ["insert", "into", "employees", "name", "salary", "values", "john", "50000"],
            "sample_answer": "INSERT INTO employees (name, salary) VALUES ('John', 50000);",
        },
        {
            "question": "Insert a customer named Alice with email alice@example.com.",
            "answer_keywords": ["insert", "into", "customers", "name", "email", "values", "alice"],
            "sample_answer": "INSERT INTO customers (name, email) VALUES ('Alice', 'alice@example.com');",
        },
        {
            "question": "Insert a product named Laptop with price 75000.",
            "answer_keywords": ["insert", "into", "products", "product_name", "price", "values", "laptop", "75000"],
            "sample_answer": "INSERT INTO products (product_name, price) VALUES ('Laptop', 75000);",
        },
        {
            "question": "Insert a student named Rahul with marks 85.",
            "answer_keywords": ["insert", "into", "students", "name", "marks", "values", "rahul", "85"],
            "sample_answer": "INSERT INTO students (name, marks) VALUES ('Rahul', 85);",
        },
        {
            "question": "Insert a new order with customer_id 10 and amount 2500.",
            "answer_keywords": ["insert", "into", "orders", "customer_id", "amount", "values", "10", "2500"],
            "sample_answer": "INSERT INTO orders (customer_id, amount) VALUES (10, 2500);",
        },
        {
            "question": "Insert a department named HR.",
            "answer_keywords": ["insert", "into", "departments", "department_name", "values", "hr"],
            "sample_answer": "INSERT INTO departments (department_name) VALUES ('HR');",
        },
        {
            "question": "Insert a book titled Python Basics.",
            "answer_keywords": ["insert", "into", "books", "title", "values", "python", "basics"],
            "sample_answer": "INSERT INTO books (title) VALUES ('Python Basics');",
        },
        {
            "question": "Insert a user named Sam with age 25.",
            "answer_keywords": ["insert", "into", "users", "name", "age", "values", "sam", "25"],
            "sample_answer": "INSERT INTO users (name, age) VALUES ('Sam', 25);",
        },
        {
            "question": "Insert a category named Electronics.",
            "answer_keywords": ["insert", "into", "categories", "category_name", "values", "electronics"],
            "sample_answer": "INSERT INTO categories (category_name) VALUES ('Electronics');",
        },
        {
            "question": "Insert a new product named Mouse with price 800.",
            "answer_keywords": ["insert", "into", "products", "product_name", "price", "values", "mouse", "800"],
            "sample_answer": "INSERT INTO products (product_name, price) VALUES ('Mouse', 800);",
        },
    ],

    "✏️ UPDATE": [
        {
            "question": "Update the status of order id 5 to shipped.",
            "answer_keywords": ["update", "orders", "set", "status", "where", "id", "5", "shipped"],
            "sample_answer": "UPDATE orders SET status = 'shipped' WHERE id = 5;",
        },
        {
            "question": "Update the salary of employee id 10 to 60000.",
            "answer_keywords": ["update", "employees", "set", "salary", "60000", "where", "id", "10"],
            "sample_answer": "UPDATE employees SET salary = 60000 WHERE id = 10;",
        },
        {
            "question": "Update the price of product id 3 to 1500.",
            "answer_keywords": ["update", "products", "set", "price", "1500", "where", "id", "3"],
            "sample_answer": "UPDATE products SET price = 1500 WHERE id = 3;",
        },
        {
            "question": "Update the email of user id 7 to new@example.com.",
            "answer_keywords": ["update", "users", "set", "email", "where", "id", "7"],
            "sample_answer": "UPDATE users SET email = 'new@example.com' WHERE id = 7;",
        },
        {
            "question": "Update the marks of student id 12 to 90.",
            "answer_keywords": ["update", "students", "set", "marks", "90", "where", "id", "12"],
            "sample_answer": "UPDATE students SET marks = 90 WHERE id = 12;",
        },
        {
            "question": "Update the department of employee id 4 to IT.",
            "answer_keywords": ["update", "employees", "set", "department", "it", "where", "id", "4"],
            "sample_answer": "UPDATE employees SET department = 'IT' WHERE id = 4;",
        },
        {
            "question": "Update the name of customer id 8 to Alice.",
            "answer_keywords": ["update", "customers", "set", "name", "alice", "where", "id", "8"],
            "sample_answer": "UPDATE customers SET name = 'Alice' WHERE id = 8;",
        },
        {
            "question": "Update the quantity of product id 15 to 100.",
            "answer_keywords": ["update", "products", "set", "quantity", "100", "where", "id", "15"],
            "sample_answer": "UPDATE products SET quantity = 100 WHERE id = 15;",
        },
        {
            "question": "Update the category of product id 9 to Electronics.",
            "answer_keywords": ["update", "products", "set", "category", "electronics", "where", "id", "9"],
            "sample_answer": "UPDATE products SET category = 'Electronics' WHERE id = 9;",
        },
        {
            "question": "Update the phone number of customer id 20 to 9876543210.",
            "answer_keywords": ["update", "customers", "set", "phone", "9876543210", "where", "id", "20"],
            "sample_answer": "UPDATE customers SET phone = '9876543210' WHERE id = 20;",
        },
    ],

    "🗑️ DELETE": [
        {
            "question": "Delete the employee with id 10.",
            "answer_keywords": ["delete", "from", "employees", "where", "id", "10"],
            "sample_answer": "DELETE FROM employees WHERE id = 10;",
        },
        {
            "question": "Delete the product with id 5.",
            "answer_keywords": ["delete", "from", "products", "where", "id", "5"],
            "sample_answer": "DELETE FROM products WHERE id = 5;",
        },
        {
            "question": "Delete the user named John.",
            "answer_keywords": ["delete", "from", "users", "where", "name", "john"],
            "sample_answer": "DELETE FROM users WHERE name = 'John';",
        },
        {
            "question": "Delete the order with id 20.",
            "answer_keywords": ["delete", "from", "orders", "where", "id", "20"],
            "sample_answer": "DELETE FROM orders WHERE id = 20;",
        },
        {
            "question": "Delete customers whose age is less than 18.",
            "answer_keywords": ["delete", "from", "customers", "where", "age", "<", "18"],
            "sample_answer": "DELETE FROM customers WHERE age < 18;",
        },
        {
            "question": "Delete employees who belong to the HR department.",
            "answer_keywords": ["delete", "from", "employees", "where", "department", "hr"],
            "sample_answer": "DELETE FROM employees WHERE department = 'HR';",
        },
        {
            "question": "Delete products with quantity equal to 0.",
            "answer_keywords": ["delete", "from", "products", "where", "quantity", "=", "0"],
            "sample_answer": "DELETE FROM products WHERE quantity = 0;",
        },
        {
            "question": "Delete students whose marks are below 35.",
            "answer_keywords": ["delete", "from", "students", "where", "marks", "<", "35"],
            "sample_answer": "DELETE FROM students WHERE marks < 35;",
        },
        {
            "question": "Delete orders with status cancelled.",
            "answer_keywords": ["delete", "from", "orders", "where", "status", "cancelled"],
            "sample_answer": "DELETE FROM orders WHERE status = 'cancelled';",
        },
        {
            "question": "Delete users who have not logged in.",
            "answer_keywords": ["delete", "from", "users", "where", "last_login", "null"],
            "sample_answer": "DELETE FROM users WHERE last_login IS NULL;",
        },
    ],

    "🧠 Advanced SQL": [
        {
            "question": "Find employees whose salary is greater than the average salary.",
            "answer_keywords": ["select", "employees", "where", "salary", ">", "avg"],
            "sample_answer": "SELECT * FROM employees WHERE salary > (SELECT AVG(salary) FROM employees);",
        },
        {
            "question": "Find employees working in departments located in the West region.",
            "answer_keywords": ["select", "employees", "where", "dept_id", "in", "select", "departments", "region", "west"],
            "sample_answer": "SELECT * FROM employees WHERE dept_id IN (SELECT id FROM departments WHERE region = 'West');",
        },
        {
            "question": "Find products whose price is greater than the average product price.",
            "answer_keywords": ["select", "products", "where", "price", ">", "avg"],
            "sample_answer": "SELECT * FROM products WHERE price > (SELECT AVG(price) FROM products);",
        },
        {
            "question": "Find customers who have placed at least one order.",
            "answer_keywords": ["select", "customers", "where", "id", "in", "select", "customer_id", "orders"],
            "sample_answer": "SELECT * FROM customers WHERE id IN (SELECT customer_id FROM orders);",
        },
        {
            "question": "Find employees who do not belong to any department.",
            "answer_keywords": ["select", "employees", "where", "dept_id", "is", "null"],
            "sample_answer": "SELECT * FROM employees WHERE dept_id IS NULL;",
        },
        {
            "question": "Find the second highest salary.",
            "answer_keywords": ["select", "max", "salary", "where", "salary", "<"],
            "sample_answer": "SELECT MAX(salary) FROM employees WHERE salary < (SELECT MAX(salary) FROM employees);",
        },
        {
            "question": "Find departments that have more employees than the average department size.",
            "answer_keywords": ["select", "department", "count", "employees", "group by", "having"],
            "sample_answer": "SELECT department, COUNT(*) FROM employees GROUP BY department HAVING COUNT(*) > (SELECT AVG(emp_count) FROM (SELECT COUNT(*) AS emp_count FROM employees GROUP BY department) AS department_counts);",
        },
        {
            "question": "Find products that have never been ordered.",
            "answer_keywords": ["select", "products", "where", "id", "not", "in", "select", "product_id", "orders"],
            "sample_answer": "SELECT * FROM products WHERE id NOT IN (SELECT product_id FROM orders);",
        },
        {
            "question": "Find customers who have placed more than 5 orders.",
            "answer_keywords": ["select", "customer_id", "count", "orders", "group by", "having"],
            "sample_answer": "SELECT customer_id FROM orders GROUP BY customer_id HAVING COUNT(*) > 5;",
        },
        {
            "question": "Find the highest paid employee in each department.",
            "answer_keywords": ["select", "employees", "where", "salary", "in", "select", "max", "group by"],
            "sample_answer": "SELECT * FROM employees WHERE salary IN (SELECT MAX(salary) FROM employees GROUP BY department);",
        },
    ],
}

FAQ_ITEMS = [
    ("Do I need to know SQL to use this app?", "Not at all — describe what you want in plain English or by voice, and the app generates the SQL for you, along with a visual explanation."),
    ("Can I edit the generated SQL?", "Yes. Copy it via the download button and edit it in your own SQL editor or database tool."),
    ("Does Voice-to-SQL work without an internet connection?", "Recording works offline, but automatic transcription (speech-to-text) generally requires the SpeechRecognition library and, depending on setup, an internet connection. You can always type/edit the transcript manually."),
    ("Is my data / are my saved queries private?", "Saved queries and feedback are stored locally in the app's SQLite database (app_data.db) under your username."),
    ("Can I plug in a real AI model for smarter query generation?", "Yes — enter an Anthropic API key in the sidebar. When present, requests are sent to Claude for translation; the app automatically falls back to the built-in rule-based engine if the AI call fails."),
    ("What SQL dialect does this target?", "Generated queries follow standard ANSI SQL, which works across MySQL, PostgreSQL, and SQLite with minor syntax variations."),
]


def page_sql_notes():
    st.title("📚 SQL Notes")

    for category, topics in SQL_NOTES.items():

        with st.expander(category, expanded=False):

            for topic, content in topics.items():

                st.markdown(f"## {topic}")

                st.markdown(content)

                st.divider()
            

def page_sql_practice():

    st.title("✍️ SQL Practice")

    topic = st.selectbox(
        "📚 Choose a SQL Topic",
        list(PRACTICE_QUESTIONS.keys())
    )

    questions = PRACTICE_QUESTIONS[topic]

    # Initialize session state
    if "practice_index" not in st.session_state:
        st.session_state.practice_index = 0

    if "current_topic" not in st.session_state:
        st.session_state.current_topic = topic

    # Reset to Question 1 when topic changes
    if st.session_state.current_topic != topic:
        st.session_state.current_topic = topic
        st.session_state.practice_index = 0

    index = st.session_state.practice_index
    current_question = questions[index]

    # Progress
    st.markdown(
        f"### 📝 Question {index + 1} of {len(questions)}"
    )

    st.progress((index + 1) / len(questions))

    # Question
    st.info(current_question["question"])

    # User answer
    user_answer = st.text_area(
        "✍️ Write your SQL query:",
        key=f"answer_{topic}_{index}",
        height=120
    )

    # Check answer
    if st.button("✅ Check Answer", use_container_width=True):

        answer = user_answer.lower()

        correct = all(
            keyword.lower() in answer
            for keyword in current_question["answer_keywords"]
        )

        if correct:
            st.success("🎉 Correct! Good job.")
        else:
            st.error("❌ Your answer is not quite correct.")

        with st.expander("💡 Show Sample Answer"):
            st.code(
                current_question["sample_answer"],
                language="sql"
            )

    # Navigation buttons
    col1, col2 = st.columns(2)

    with col1:
        if index > 0:
            if st.button(
                "⬅️ Previous Question",
                use_container_width=True
            ):
                st.session_state.practice_index -= 1
                st.rerun()

    with col2:
        if index < len(questions) - 1:
            if st.button(
                "Next Question ➡️",
                use_container_width=True
            ):
                st.session_state.practice_index += 1
                st.rerun()

        else:
            st.success("🎉 You completed all 10 questions!")

def page_sql_validation():
    st.header("🛡️ SQL Validation")
    st.caption("Paste a SQL query to check for common syntax issues.")
    query = st.text_area("SQL query to validate", height=140, placeholder="SELECT * FROM employees WHERE salary > 50000;")
    if st.button("Validate", type="primary"):
        if not query.strip():
            st.warning("Please paste a query first.")
        else:
            issues = _validate_sql(query)
            if not issues:
                st.success("✅ No obvious syntax issues detected.")
            else:
                for issue in issues:
                    st.error(f"⚠️ {issue}")


def _validate_sql(query: str):
    issues = []
    q = query.strip()
    upper = q.upper()

    if not q.rstrip().endswith(";"):
        issues.append("Missing semicolon (;) at the end of the statement.")
    if q.count("(") != q.count(")"):
        issues.append("Mismatched parentheses — check your '(' and ')' counts.")
    single_quotes = q.count("'")
    if single_quotes % 2 != 0:
        issues.append("Unmatched single quote (') — string literals must be opened and closed.")

    starts_ok = any(upper.startswith(k) for k in ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH", "CREATE", "ALTER", "DROP"))
    if not starts_ok:
        issues.append("Query doesn't start with a recognized SQL command (SELECT, INSERT, UPDATE, DELETE, ...).")

    if upper.startswith("SELECT") and " FROM " not in f" {upper} ":
        issues.append("SELECT statement is missing a FROM clause.")
    if upper.startswith("UPDATE") and " SET " not in f" {upper} ":
        issues.append("UPDATE statement is missing a SET clause.")
    if upper.startswith("INSERT") and "VALUES" not in upper:
        issues.append("INSERT statement is missing a VALUES clause.")
    if "GROUP BY" in upper and "SELECT" in upper:
        # crude check: aggregate without group by mismatch not evaluated deeply here
        pass
    if "WHERE" in upper and "FROM" not in upper:
        issues.append("WHERE clause found without a FROM clause.")

    return issues


def page_text_based_practice():
    st.header("🧠 Text-Based Practice")
    st.caption("Convert the natural-language question into SQL yourself, then compare with the AI-generated version.")
    nl_question = st.text_area("Natural language question", placeholder="e.g. List all customers who joined after 2023", height=80)
    your_sql = st.text_area("Your SQL attempt", height=90)

    if st.button("Compare with generated SQL", type="primary"):
        if not nl_question.strip():
            st.warning("Enter a question first.")
        else:
            result = engine.generate_sql(nl_question, st.session_state.api_key)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Your answer**")
                st.code(your_sql or "(empty)", language="sql")
            with col2:
                st.markdown("**Generated answer**")
                st.code(result.sql, language="sql")
            st.info(result.explanation)


def page_faq():
    st.header("❓ FAQ")
    for question, answer in FAQ_ITEMS:
        with st.expander(question):
            st.write(answer)


def page_saved_queries():
    st.header("💾 Saved Queries")
    search = st.text_input("🔍 Search your saved queries")
    rows = db.get_saved_queries(st.session_state.username, search)

    if not rows:
        if search.strip():
            st.info(f"No saved queries match \"{search}\". Try a different search term, or clear the box to see all saved queries.")
        else:
            st.info("No saved queries yet. Generate one from Text-to-SQL or Voice-to-SQL and hit 'Save Query'.")
        return

    for row in rows:
        when = _relative_time(row["created_at"]) if row["created_at"] else ""
        with st.expander(f"🕐 {when} — {(row['natural_language'] or '')[:60]}"):
            st.markdown(f'<div class="sql-box">{row["sql_query"]}</div>', unsafe_allow_html=True)
            if row["explanation"]:
                st.caption(row["explanation"])
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("📋 Copy (download .sql)", data=row["sql_query"], file_name=f"query_{row['id']}.sql", key=f"dl_{row['id']}")
            with c2:
                if st.button("🗑️ Delete", key=f"del_{row['id']}"):
                    db.delete_query(row["id"], st.session_state.username)
                    st.rerun()


def page_feedback_history():
    st.header("🗳️ My Feedback History")
    rows = db.get_feedback(st.session_state.username)
    if not rows:
        st.info("You haven't submitted any feedback yet.")
        return
    for row in rows:
        st.markdown(f"**{row['feedback_type'].capitalize()}** — {row['created_at'][:19]}")
        st.code(row["sql_query"], language="sql")
        st.markdown("---")


def _relative_time(ts_str: str) -> str:
    """Turn a 'YYYY-MM-DD HH:MM:SS'-style timestamp into '2 min ago' style text."""
    if not ts_str:
        return ""
    try:
        ts = datetime.datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return ts_str[:19] if len(ts_str) >= 19 else ts_str

    delta = datetime.datetime.now() - ts
    seconds = delta.total_seconds()

    if seconds < 60:
        return "just now"
    if seconds < 3600:
        mins = int(seconds // 60)
        return f"{mins} min ago"
    if seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if seconds < 172800:
        return "Yesterday"
    days = int(seconds // 86400)
    if days < 7:
        return f"{days} days ago"
    return ts.strftime("%b %d, %Y")


NAV_ITEMS = [
    ("dashboard", "🏠", "Dashboard"),
    ("text_to_sql", "💬", "Text-to-SQL"),
    ("voice_to_sql", "🎙️", "Voice-to-SQL"),
    ("sql_notes", "📚", "SQL Notes"),
    ("sql_practice", "✍️", "SQL Practice"),
    ("sql_validation", "🛡️", "SQL Validation"),
    ("text_practice", "🧠", "Text-Based Practice"),
    ("saved_queries", "💾", "Saved Queries"),
    ("feedback_history", "🗳️", "Feedback History"),
    ("faq", "❓", "FAQ"),
]


# --------------------------------------------------------------------------- #
# Dashboard shell
# --------------------------------------------------------------------------- #
def render_dashboard():
    # 3rd image -> used as the background for every module/page in the app
    set_module_background()

    if "current_page" not in st.session_state:
        st.session_state.current_page = "dashboard"

    username = st.session_state.username or "there"
    initial = username[:1].upper() if username else "U"

    with st.sidebar:
        # ---- Logo ----
        logo_html = (
            '<div class="sb-logo-card">'
            '<div class="sb-logo-icon">🗄️</div>'
            '<div class="sb-logo-text"><h1>NL &rarr; SQL</h1><p>Query Generator</p></div>'
            '</div>'
        )
        st.markdown(logo_html, unsafe_allow_html=True)

        # ---- User card ----
        user_html = (
            '<div class="sb-user-card">'
            f'<div class="sb-user-avatar">{initial}</div>'
            f'<div><div class="sb-user-name">{username}</div>'
            '<div class="sb-user-sub">Welcome back!</div></div>'
            '</div>'
        )
        st.markdown(user_html, unsafe_allow_html=True)

        with st.container(key="logout_btn_wrap"):
            if st.button("↔  Log Out", use_container_width=True, key="logout_btn"):
                for key in ("logged_in", "username", "last_result", "last_nl_text", "voice_transcript"):
                    st.session_state[key] = False if key == "logged_in" else ""
                st.session_state.auth_view = "landing"
                st.session_state.current_page = "dashboard"
                st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # ---- Nav ----
        for pid, icon, label in NAV_ITEMS:
            is_active = st.session_state.current_page == pid
            container_key = f"nav_active_{pid}" if is_active else f"nav_{pid}"
            with st.container(key=container_key):
                if st.button(f"{icon}  {label}", use_container_width=True, key=f"navbtn_{pid}"):
                    st.session_state.current_page = pid
                    st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        with st.expander("⚙️ AI Mode (optional)"):
            st.session_state.api_key = st.text_input(
                "Anthropic API key",
                type="password",
                value=st.session_state.api_key,
                help="Leave blank to use the built-in rule-based engine. If provided, requests are sent to Claude for more flexible SQL generation.",
            )

    page = st.session_state.current_page
    if page == "dashboard":
        render_dashboard_home()
    elif page == "text_to_sql":
        page_text_to_sql()
    elif page == "voice_to_sql":
        page_voice_to_sql()
    elif page == "sql_notes":
        page_sql_notes()
    elif page == "sql_practice":
        page_sql_practice()
    elif page == "sql_validation":
        page_sql_validation()
    elif page == "text_practice":
        page_text_based_practice()
    elif page == "saved_queries":
        page_saved_queries()
    elif page == "feedback_history":
        page_feedback_history()
    elif page == "faq":
        page_faq()


def render_dashboard_home():
    username = st.session_state.username or "there"
    initial = username[:1].upper() if username else "U"

    # ---- Top bar (bell + avatar) ----
    topbar_html = (
        '<div class="topbar">'
        '<div class="topbar-bell">🔔<span class="topbar-bell-dot"></span></div>'
        f'<div class="topbar-avatar">{initial}</div>'
        '</div>'
    )
    st.markdown(topbar_html, unsafe_allow_html=True)

    # ---- Hero greeting ----
    hero_html = (
        '<div class="dash-hero">'
        f'<h1>Hi, {username}! 👋</h1>'
        "<p>Let's turn your ideas into powerful SQL queries.</p>"
        '<div class="dash-hero-graphic">'
        '<div class="dash-hero-dots"><span></span><span></span><span></span>'
        '<span></span><span></span><span></span></div>'
        '<div class="dash-hero-stack">'
        '<div class="dash-hero-layer l1"></div>'
        '<div class="dash-hero-layer l2"></div>'
        '<div class="dash-hero-layer l3"></div>'
        '</div>'
        '</div>'
        '</div>'
    )
    st.markdown(hero_html, unsafe_allow_html=True)

    # ---- Your Workspace: 5-step flow ----
    steps = [
        ("c1", "💬", "1. Ask", "Describe what you need."),
        ("c2", "&lt;/&gt;", "2. Generate", "Get SQL in seconds."),
        ("c3", "✓", "3. Validate", "Check and improve your query."),
        ("c4", "📊", "4. Execute", "Run and get results."),
        ("c5", "🔖", "5. Save", "Save useful queries."),
    ]
    step_parts = []
    for i, (cls, icon, title, desc) in enumerate(steps):
        step_parts.append(
            f'<div class="step-item"><div class="step-circle {cls}">{icon}</div>'
            f'<h4>{title}</h4><p>{desc}</p></div>'
        )
        if i < len(steps) - 1:
            step_parts.append('<div class="step-arrow">&rarr;</div>')

    workspace_html = (
        '<div class="workspace-card">'
        '<div class="workspace-title">Your Workspace</div>'
        f'<div class="step-flow">{"".join(step_parts)}</div>'
        '</div>'
    )
    st.markdown(workspace_html, unsafe_allow_html=True)

    # ---- Recent Queries + Quick Start ----
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        with st.container(key="recent_queries_card"):
            header_html = (
                '<div class="section-card-header">'
                '<div class="section-card-title">Recent Queries</div>'
                '</div>'
            )
            st.markdown(header_html, unsafe_allow_html=True)

            try:
                rows = db.get_saved_queries(st.session_state.username, "") or []
            except Exception:
                rows = []

            if rows:
                with st.container(key="recent_view_all"):
                    if st.button("View all →", key="view_all_btn"):
                        st.session_state.current_page = "saved_queries"
                        st.rerun()

            recent_rows = rows[:4]

            if not recent_rows:
                st.markdown(
                    '<p style="color:#8a8f9a;font-size:0.9rem;">'
                    "No saved queries yet — generate one and hit 'Save Query' to see it here."
                    '</p>',
                    unsafe_allow_html=True,
                )
            else:
                rows_html = []
                for raw_row in recent_rows:
                    row = dict(raw_row)
                    label = (row.get("natural_language") or row.get("sql_query") or "Untitled query")[:60]
                    when = _relative_time(row.get("created_at", ""))
                    rows_html.append(
                        '<div class="recent-query-row">'
                        '<div class="recent-query-left">'
                        '<span class="recent-query-icon">📄</span>'
                        f'<span class="recent-query-text">{label}</span>'
                        '</div>'
                        f'<span class="recent-query-time">{when}</span>'
                        '<span class="recent-query-chevron">›</span>'
                        '</div>'
                    )
                st.markdown("".join(rows_html), unsafe_allow_html=True)

    with col_right:
        with st.container(key="quickstart_card"):
            st.markdown(
                '<div class="section-card-header"><div class="section-card-title">Quick Start</div></div>',
                unsafe_allow_html=True,
            )

            with st.container(key="qs_grid"):
                qs1, qs2 = st.columns(2)
                with qs1:
                    with st.container(key="qs_generate"):
                        if st.button("💬  Generate SQL  →", use_container_width=True, key="qs_generate_btn"):
                            st.session_state.current_page = "text_to_sql"
                            st.rerun()
                    with st.container(key="qs_practice"):
                        if st.button("🎓  Practice SQL  →", use_container_width=True, key="qs_practice_btn"):
                            st.session_state.current_page = "sql_practice"
                            st.rerun()
                with qs2:
                    with st.container(key="qs_voice"):
                        if st.button("🎙️  Voice to SQL  →", use_container_width=True, key="qs_voice_btn"):
                            st.session_state.current_page = "voice_to_sql"
                            st.rerun()
                    with st.container(key="qs_validate"):
                        if st.button("🛡️  Validate SQL  →", use_container_width=True, key="qs_validate_btn"):
                            st.session_state.current_page = "sql_validation"
                            st.rerun()


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main():
    if st.session_state.logged_in:
        render_dashboard()
    else:
        if st.session_state.auth_view == "landing":
            render_landing_page()
        else:
            render_auth_forms()


if __name__ == "__main__":
    main()
