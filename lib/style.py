"""Toss-inspired CSS injection for Streamlit.

Reference: ../../Design_Tokens/Toss_DNA.md (v1.0)
"""

import streamlit as st


# Toss DNA tokens
TOSS = {
    "blue_500": "#0064FF",
    "blue_600": "#0050D8",
    "blue_100": "#E8F2FF",
    "gray_000": "#FFFFFF",
    "gray_50": "#F9FAFB",
    "gray_100": "#F2F4F6",
    "gray_200": "#E5E8EB",
    "gray_400": "#B0B8C1",
    "gray_600": "#8B95A1",
    "gray_700": "#4E5968",
    "gray_900": "#191F28",
    "red_500": "#F04452",
    "red_100": "#FFE5E8",
    "green_500": "#20C997",
    "green_100": "#E5F8F1",
    "yellow_500": "#FFB200",
}

# Korean convention: 빨강 = 상승, 파랑 = 하락
PROFIT_COLOR = TOSS["red_500"]
LOSS_COLOR = TOSS["blue_500"]


def inject_toss_style() -> None:
    """Apply Toss DNA — Pretendard font + clean card style + bigger metrics."""
    st.markdown(
        f"""
<link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">

<style>
/* ─── Global font ─────────────────────────────────────── */
html, body, [class*="css"] {{
    font-family: "Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont,
        "Apple SD Gothic Neo", system-ui, sans-serif !important;
    letter-spacing: -0.01em;
}}

/* App background — slight off-white, cards on white */
.stApp {{
    background-color: {TOSS["gray_50"]};
}}

/* Main container — white surface, rounded */
.main .block-container {{
    background-color: {TOSS["gray_000"]};
    border-radius: 16px;
    padding: 32px 40px;
    margin-top: 1rem;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}}

/* ─── Headings ────────────────────────────────────────── */
h1 {{
    font-weight: 700 !important;
    color: {TOSS["gray_900"]} !important;
    letter-spacing: -0.02em;
    font-size: 2rem !important;
}}
h2 {{
    font-weight: 700 !important;
    color: {TOSS["gray_900"]} !important;
    font-size: 1.5rem !important;
    letter-spacing: -0.015em;
}}
h3, h4 {{
    font-weight: 600 !important;
    color: {TOSS["gray_900"]} !important;
    letter-spacing: -0.01em;
}}

/* Caption gray */
[data-testid="stCaptionContainer"] {{
    color: {TOSS["gray_600"]} !important;
}}

/* ─── Metric (KPI 카드) — 토스 강조 스타일 ────────────── */
[data-testid="stMetric"] {{
    background-color: {TOSS["gray_100"]};
    border-radius: 12px;
    padding: 18px 20px;
    box-shadow: none;
    border: none;
}}
[data-testid="stMetricLabel"] {{
    font-size: 0.875rem !important;
    color: {TOSS["gray_600"]} !important;
    font-weight: 500 !important;
}}
[data-testid="stMetricValue"] {{
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    color: {TOSS["gray_900"]} !important;
    letter-spacing: -0.02em;
    line-height: 1.2;
}}
[data-testid="stMetricDelta"] {{
    font-size: 0.875rem !important;
    font-weight: 500 !important;
}}

/* ─── Buttons ─────────────────────────────────────────── */
.stButton > button {{
    background-color: {TOSS["blue_500"]} !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 16px !important;
    font-weight: 600 !important;
    font-size: 0.9375rem !important;
    transition: background-color 150ms ease-out;
    box-shadow: none !important;
}}
.stButton > button:hover {{
    background-color: {TOSS["blue_600"]} !important;
    color: white !important;
}}
.stButton > button:active {{
    background-color: {TOSS["blue_600"]} !important;
}}

/* Secondary buttons (in sidebar etc) */
section[data-testid="stSidebar"] .stButton > button {{
    background-color: {TOSS["gray_100"]} !important;
    color: {TOSS["gray_900"]} !important;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
    background-color: {TOSS["gray_200"]} !important;
}}

/* ─── Inputs (text / number / select) ─────────────────── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div > select {{
    background-color: {TOSS["gray_50"]} !important;
    border: 1px solid {TOSS["gray_200"]} !important;
    border-radius: 8px !important;
    color: {TOSS["gray_900"]} !important;
    font-weight: 500 !important;
}}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {{
    border-color: {TOSS["blue_500"]} !important;
    box-shadow: 0 0 0 2px {TOSS["blue_100"]} !important;
}}

/* Slider */
.stSlider [data-baseweb="slider"] > div > div {{
    background-color: {TOSS["blue_500"]} !important;
}}

/* ─── Sidebar ─────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background-color: {TOSS["gray_50"]};
    border-right: 1px solid {TOSS["gray_200"]};
}}
section[data-testid="stSidebar"] h3 {{
    font-size: 1rem !important;
    color: {TOSS["gray_700"]} !important;
    font-weight: 600 !important;
}}

/* ─── Tables ──────────────────────────────────────────── */
[data-testid="stDataFrame"] {{
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid {TOSS["gray_200"]};
}}

/* ─── Alert boxes ─────────────────────────────────────── */
[data-testid="stAlert"] {{
    border-radius: 12px;
    border: none;
}}

/* Info */
[data-testid="stAlertContentInfo"] {{
    background-color: {TOSS["blue_100"]};
    color: {TOSS["gray_900"]};
}}

/* Error */
[data-testid="stAlertContentError"] {{
    background-color: {TOSS["red_100"]};
    color: {TOSS["red_500"]};
}}

/* ─── Expander ────────────────────────────────────────── */
[data-testid="stExpander"] {{
    border-radius: 12px !important;
    border: 1px solid {TOSS["gray_200"]} !important;
    background-color: {TOSS["gray_50"]};
}}

/* ─── Tabs (Streamlit) ────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    gap: 8px;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 8px;
    padding: 8px 16px;
    background-color: {TOSS["gray_100"]};
    color: {TOSS["gray_700"]};
}}
.stTabs [aria-selected="true"] {{
    background-color: {TOSS["blue_500"]} !important;
    color: white !important;
}}

/* ─── Hide Streamlit branding ─────────────────────────── */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}

/* ─── Responsive — mobile friendly ────────────────────── */
@media (max-width: 768px) {{
    .main .block-container {{
        padding: 20px 16px;
        border-radius: 0;
    }}
    h1 {{ font-size: 1.5rem !important; }}
    [data-testid="stMetricValue"] {{ font-size: 1.4rem !important; }}
}}
</style>
""",
        unsafe_allow_html=True,
    )


def get_plotly_layout_defaults() -> dict:
    """Default Plotly layout matching Toss DNA."""
    return {
        "font": {
            "family": "Pretendard, system-ui, sans-serif",
            "color": TOSS["gray_900"],
        },
        "plot_bgcolor": "rgba(0,0,0,0)",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "xaxis": {
            "gridcolor": TOSS["gray_100"],
            "linecolor": TOSS["gray_200"],
            "tickfont": {"color": TOSS["gray_600"]},
        },
        "yaxis": {
            "gridcolor": TOSS["gray_100"],
            "linecolor": TOSS["gray_200"],
            "tickfont": {"color": TOSS["gray_600"]},
        },
        "hoverlabel": {
            "bgcolor": "white",
            "bordercolor": TOSS["gray_200"],
            "font": {"family": "Pretendard, system-ui, sans-serif"},
        },
    }


def color_for_value(v: float) -> str:
    """수익률 등 양/음에 따라 한국 관습 색상 반환 (양=빨강, 음=파랑)."""
    if v is None or v == 0:
        return TOSS["gray_600"]
    return PROFIT_COLOR if v > 0 else LOSS_COLOR
