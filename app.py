"""MH Pension App — Home Dashboard.

Streamlit multi-page app entry point.
서브 페이지: pages/ 디렉토리.
"""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lib.auth import check_password
from lib.notion import (
    get_accounts_df,
    get_cashflow_df,
    get_holdings_df,
)
from lib.sidebar import fmt_amount, fmt_pct, render_sidebar
from lib.style import TOSS, inject_toss_style
from lib.transform import (
    compute_account_kpis,
    compute_distribution_cycle,
    compute_total_kpis,
    filter_active_holdings,
)

st.set_page_config(
    page_title="MH Pension Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_toss_style()

if not check_password():
    st.stop()

render_sidebar()


# Backward-compat alias
fmt_won = fmt_amount


# ─── Header ─────────────────────────────────────────────────────────────────
st.title("💰 MH Pension Dashboard")
st.caption(
    "노션 데이터 기반 실시간 시각화 · 5분 캐시 · "
    "**[🔮 Simulator]** 페이지에서 What-if 분석 가능"
)

# ─── Data load ─────────────────────────────────────────────────────────────
try:
    accounts_df = get_accounts_df()
    holdings_df = get_holdings_df()
    cashflow_df = get_cashflow_df()
except Exception as exc:
    st.error(f"노션 연결 실패: {exc}")
    st.info(
        "**점검 사항:**\n"
        "1. `.env` 파일에 `NOTION_TOKEN`이 올바르게 설정되어 있나요?\n"
        "2. Notion Internal Integration이 페이지에 추가되어 있나요?\n"
        "3. 토큰을 재발급한 적이 있다면 `.env` 갱신했나요?"
    )
    st.stop()

active_holdings = filter_active_holdings(holdings_df)
account_kpis = compute_account_kpis(accounts_df, active_holdings)
totals = compute_total_kpis(account_kpis)

# ─── KPI Cards ─────────────────────────────────────────────────────────────
st.markdown("### 📊 핵심 지표")
k1, k2, k3, k4, k5 = st.columns(5)

k1.metric(
    "총 자산 (평가 + 현금)",
    fmt_amount(totals["total_assets"]),
    f"{fmt_amount(totals['total_pl'])} 손익",
)
k2.metric(
    "종목 평가금액",
    fmt_amount(totals["total_market_value"]),
)
k3.metric(
    "현금성 자산",
    fmt_amount(totals["total_cash"]),
    "매매 대기 자금",
)
k4.metric(
    "자산 가중 수익률",
    fmt_pct(totals["weighted_return"]),
    f"목표 20-30% {'✓' if 20 <= totals['weighted_return'] <= 30 else ('↑' if totals['weighted_return'] < 20 else '↓')}",
)
k5.metric(
    "월 신규 입금",
    fmt_amount(totals["monthly_contribution_total"]),
    "DC + IRP + 연저 + ISA",
)

# ─── Account KPI table ─────────────────────────────────────────────────────
st.markdown("### 🏦 계좌별 자산·수익률")
if not account_kpis.empty:
    display = account_kpis.copy()
    display["월 입금"] = display["monthly_contribution"].apply(fmt_amount)
    display["매입원금"] = display["sum_purchase_cost"].apply(fmt_amount)
    display["평가금액"] = display["sum_market_value"].apply(fmt_amount)
    display["현금"] = display["cash_balance"].apply(fmt_amount)
    display["총 자산"] = display["total_assets"].apply(fmt_amount)
    display["평가손익"] = display["sum_pl"].apply(fmt_amount)
    display["수익률"] = display["return_rate"].apply(fmt_pct)
    display = display[
        [
            "account_name",
            "broker",
            "account_type",
            "n_holdings",
            "월 입금",
            "매입원금",
            "평가금액",
            "현금",
            "총 자산",
            "평가손익",
            "수익률",
        ]
    ].rename(
        columns={
            "account_name": "계좌",
            "broker": "증권사",
            "account_type": "유형",
            "n_holdings": "종목 수",
        }
    )
    st.dataframe(display, use_container_width=True, hide_index=True)

# ─── Charts ────────────────────────────────────────────────────────────────
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.markdown("#### 🥧 계좌별 자산 비중")
    if not account_kpis.empty and account_kpis["sum_market_value"].sum() > 0:
        fig = px.pie(
            account_kpis,
            values="sum_market_value",
            names="account_name",
            hole=0.45,
        )
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=350)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("데이터가 충분하지 않습니다.")

with chart_col2:
    st.markdown("#### 📊 계좌별 수익률 비교")
    if not account_kpis.empty:
        fig = px.bar(
            account_kpis.sort_values("return_rate", ascending=True),
            x="return_rate",
            y="account_name",
            orientation="h",
            color="return_rate",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=350,
            xaxis_title="수익률 %",
            yaxis_title="",
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)

# ─── Distribution by Cycle ─────────────────────────────────────────────────
st.markdown("### 💸 분배 사이클별 1회 지급액")
cycle_df = compute_distribution_cycle(active_holdings)
if not cycle_df.empty:
    cycle_df = cycle_df[cycle_df["Pay Cycle"].notna()]
    fig = px.bar(
        cycle_df,
        x="Pay Cycle",
        y="Period Dividend",
        color="Pay Cycle",
        text="Period Dividend",
    )
    fig.update_traces(texttemplate="%{text:,.0f}원", textposition="outside")
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=320,
        xaxis_title="지급 사이클",
        yaxis_title="1회 지급액 (원)",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "월배당은 매월 / 분기 종목은 해당 사이클 월에만 입금. "
        "예: (2·5·8·11) = 5월·8월·11월 등 4회"
    )

# ─── 12-month Cashflow Preview ─────────────────────────────────────────────
st.markdown("### 📅 12개월 분배 캐시플로우 (예상)")
if not cashflow_df.empty and "Year-Month" in cashflow_df.columns:
    cf = cashflow_df.copy()
    cf = cf.sort_values("Year-Month")
    if "Expected Total" in cf.columns:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=cf["Year-Month"],
                y=cf["Expected Total"],
                mode="lines+markers",
                name="예상 분배금",
                line=dict(width=3),
            )
        )
        # Target line at 3M
        fig.add_hline(
            y=3_000_000,
            line_dash="dash",
            line_color="red",
            annotation_text="목표 3,000,000원/월",
            annotation_position="top right",
        )
        fig.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=380,
            xaxis_title="",
            yaxis_title="분배금 (원)",
            yaxis=dict(tickformat=","),
        )
        st.plotly_chart(fig, use_container_width=True)

# ─── Footer ────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "**데이터 소스**: 노션 만형 이's Space (Accounts / Holdings / Cashflow Monthly DB) · "
    "**갱신 주기**: 5분 (또는 ⟳ 새로고침) · "
    "**노션 직접 편집** 시 5분 후 자동 반영."
)
