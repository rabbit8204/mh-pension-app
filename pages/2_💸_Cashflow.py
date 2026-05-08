"""Cashflow Monthly — 12개월 분배 캐시플로우 + 사이클 누적 + 목표 대비."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lib.notion import get_cashflow_df, get_holdings_df
from lib.sidebar import fmt_amount, render_sidebar
from lib.style import TOSS, inject_toss_style
from lib.transform import compute_distribution_cycle, filter_active_holdings

st.set_page_config(page_title="캐시플로우", page_icon="💸", layout="wide")
inject_toss_style()
render_sidebar()
st.title("💸 분배금 캐시플로우")

try:
    cashflow_df = get_cashflow_df()
    holdings_df = get_holdings_df()
except Exception as exc:
    st.error(f"노션 연결 실패: {exc}")
    st.stop()

if cashflow_df.empty:
    st.info("Cashflow Monthly DB가 비어 있습니다.")
    st.stop()

cf = cashflow_df.sort_values("Year-Month").copy()

# ─── KPI ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
expected_year = cf["Expected Total"].sum() if "Expected Total" in cf.columns else 0
target_monthly = 3_000_000
expected_monthly_avg = expected_year / 12 if expected_year else 0
gap = target_monthly - expected_monthly_avg

k1.metric("연 예상 분배금", fmt_amount(expected_year))
k2.metric("월 평균 (예상)", fmt_amount(expected_monthly_avg))
k3.metric("월 목표", fmt_amount(target_monthly))
k4.metric("갭 (월)", fmt_amount(gap), f"-{(gap/target_monthly*100):.1f}%")

# ─── Main timeline chart ───────────────────────────────────────────────────
st.markdown("### 📈 월별 분배 추이")
fig = go.Figure()

if "Expected Total" in cf.columns:
    fig.add_trace(
        go.Bar(
            x=cf["Year-Month"],
            y=cf["Expected Total"],
            name="예상 총액",
            marker_color="#150F96",
        )
    )

if "Actual Received" in cf.columns and cf["Actual Received"].notna().any():
    fig.add_trace(
        go.Scatter(
            x=cf["Year-Month"],
            y=cf["Actual Received"],
            mode="lines+markers",
            name="실수령",
            line=dict(color="#FFC107", width=3),
            marker=dict(size=10),
        )
    )

fig.add_hline(
    y=target_monthly,
    line_dash="dash",
    line_color="red",
    annotation_text="목표 3,000,000원",
    annotation_position="top right",
)

fig.update_layout(
    height=420,
    margin=dict(l=10, r=10, t=10, b=10),
    yaxis_title="분배금 (원)",
    yaxis=dict(tickformat=","),
    xaxis_title="",
    barmode="group",
)
st.plotly_chart(fig, use_container_width=True)

# ─── Cycle composition ─────────────────────────────────────────────────────
st.markdown("### 🔄 사이클별 구성")

c1, c2 = st.columns(2)

with c1:
    st.markdown("#### 사이클 타입별 월 분포")
    if "Cycle Type" in cf.columns:
        cycle_count = cf["Cycle Type"].value_counts().reset_index()
        cycle_count.columns = ["Cycle Type", "월 수"]
        fig = px.bar(
            cycle_count,
            x="Cycle Type",
            y="월 수",
            color="Cycle Type",
            text="월 수",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown("#### 사이클별 1회 지급액 (Holdings 기준)")
    active_holdings = filter_active_holdings(holdings_df)
    cycle_df = compute_distribution_cycle(active_holdings)
    cycle_df = cycle_df[cycle_df["Pay Cycle"].notna()]
    if not cycle_df.empty:
        fig = px.bar(
            cycle_df,
            x="Pay Cycle",
            y="Period Dividend",
            color="Pay Cycle",
            text="Period Dividend",
        )
        fig.update_traces(texttemplate="%{text:,.0f}원", textposition="outside")
        fig.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            yaxis_title="1회 지급액",
        )
        st.plotly_chart(fig, use_container_width=True)

# ─── Achievement Rate Trend ────────────────────────────────────────────────
if "Achievement Rate" in cf.columns:
    st.markdown("### 🎯 목표 달성률 추이")
    fig = px.line(
        cf,
        x="Year-Month",
        y="Achievement Rate",
        markers=True,
    )
    fig.update_traces(line=dict(width=3))
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis_title="달성률 %",
        xaxis_title="",
    )
    fig.add_hline(y=100, line_dash="dash", line_color="green", annotation_text="목표 도달")
    st.plotly_chart(fig, use_container_width=True)

# ─── Detailed table ────────────────────────────────────────────────────────
st.markdown("### 📋 월별 상세")
table_cols = [
    c
    for c in [
        "Year-Month",
        "Cycle Type",
        "Expected Monthly Base",
        "Expected Quarterly Add",
        "Expected Total",
        "Actual Received",
        "Variance",
        "New Contribution",
        "Cumulative Asset Added",
        "Achievement Rate",
        "Notes",
    ]
    if c in cf.columns
]
cf_display = cf[table_cols].copy()
amt_cols = [
    "Expected Monthly Base",
    "Expected Quarterly Add",
    "Expected Total",
    "Actual Received",
    "Variance",
    "New Contribution",
    "Cumulative Asset Added",
]
for col in amt_cols:
    if col in cf_display.columns:
        cf_display[col] = cf_display[col].apply(
            lambda v: fmt_amount(v) if v is not None and v == v else "—"
        )

st.dataframe(
    cf_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Expected Total": st.column_config.Column("예상 총액"),
        "Actual Received": st.column_config.Column("실수령"),
        "Achievement Rate": st.column_config.NumberColumn("달성률 %", format="%.2f"),
        "New Contribution": st.column_config.Column("월 입금"),
        "Cumulative Asset Added": st.column_config.Column("누적 입금"),
    },
)

st.caption(
    "**Actual Received 컬럼**을 노션에서 직접 입력하면 이 페이지에서 자동으로 실수령 라인이 표시됩니다."
)
