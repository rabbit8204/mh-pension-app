"""Holdings — 보유 종목 상세 + 필터 + 수익률 히트맵."""

import plotly.express as px
import streamlit as st

from lib.auth import check_password
from lib.notion import get_accounts_df, get_holdings_df
from lib.sidebar import fmt_amount, render_sidebar
from lib.style import TOSS, inject_toss_style
from lib.transform import filter_active_holdings

st.set_page_config(page_title="보유 종목", page_icon="📊", layout="wide")
inject_toss_style()

if not check_password():
    st.stop()

render_sidebar()
st.title("📊 보유 종목")

try:
    holdings_df = get_holdings_df()
    accounts_df = get_accounts_df()
except Exception as exc:
    st.error(f"노션 연결 실패: {exc}")
    st.stop()

if holdings_df.empty:
    st.info("Holdings DB가 비어 있습니다.")
    st.stop()

# ─── Filters ───────────────────────────────────────────────────────────────
st.markdown("### 🔍 필터")
fc1, fc2, fc3, fc4 = st.columns(4)

include_sold = fc1.checkbox("매도완료 종목 포함", value=False)
df = holdings_df if include_sold else filter_active_holdings(holdings_df)

with fc2:
    if "Buy Tier" in df.columns:
        all_tiers = sorted(df["Buy Tier"].dropna().unique().tolist())
        sel_tiers = st.multiselect("Buy Tier", all_tiers, default=all_tiers)
    else:
        sel_tiers = []
with fc3:
    if "Asset Class" in df.columns:
        all_classes = sorted(df["Asset Class"].dropna().unique().tolist())
        sel_classes = st.multiselect("Asset Class", all_classes, default=all_classes)
    else:
        sel_classes = []
with fc4:
    if "Manager" in df.columns:
        all_managers = sorted(df["Manager"].dropna().unique().tolist())
        sel_managers = st.multiselect("운용사", all_managers, default=all_managers)
    else:
        sel_managers = []

if sel_tiers:
    df = df[df["Buy Tier"].isin(sel_tiers) | df["Buy Tier"].isna()]
if sel_classes:
    df = df[df["Asset Class"].isin(sel_classes) | df["Asset Class"].isna()]
if sel_managers:
    df = df[df["Manager"].isin(sel_managers) | df["Manager"].isna()]

st.caption(f"**{len(df)}개 종목** · 매도완료 {'포함' if include_sold else '제외'}")

# ─── Summary ───────────────────────────────────────────────────────────────
st.markdown("### 📈 요약")
sc1, sc2, sc3, sc4 = st.columns(4)
total_purchase = df["Purchase Cost"].fillna(0).sum() if "Purchase Cost" in df else 0
total_value = df["Market Value"].fillna(0).sum() if "Market Value" in df else 0
total_pl = total_value - total_purchase
ret = (total_pl / total_purchase * 100) if total_purchase > 0 else 0

sc1.metric("총 매입원금", fmt_amount(total_purchase))
sc2.metric("총 평가금액", fmt_amount(total_value))
sc3.metric("평가손익", fmt_amount(total_pl))
sc4.metric("자산 가중 수익률", f"{ret:.2f}%")

# ─── Charts ────────────────────────────────────────────────────────────────
ch1, ch2 = st.columns(2)

with ch1:
    st.markdown("#### 수익률 분포")
    if "Return Rate" in df.columns and df["Return Rate"].notna().any():
        plot_df = df.dropna(subset=["Return Rate"]).copy()
        fig = px.histogram(
            plot_df,
            x="Return Rate",
            nbins=20,
            color_discrete_sequence=["#150F96"],
        )
        fig.update_layout(
            xaxis_title="수익률 %",
            yaxis_title="종목 수",
            margin=dict(l=10, r=10, t=10, b=10),
            height=320,
        )
        fig.add_vline(x=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("수익률 데이터가 입력되지 않았습니다.")

with ch2:
    st.markdown("#### Asset Class별 비중 (평가금액)")
    if "Asset Class" in df.columns and "Market Value" in df.columns:
        agg = (
            df.dropna(subset=["Asset Class"])
            .groupby("Asset Class")["Market Value"]
            .sum()
            .reset_index()
        )
        agg = agg[agg["Market Value"] > 0]
        if not agg.empty:
            fig = px.pie(
                agg,
                values="Market Value",
                names="Asset Class",
                hole=0.45,
            )
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
            st.plotly_chart(fig, use_container_width=True)

# ─── Heatmap by Buy Tier × Account ────────────────────────────────────────
st.markdown("### 🔥 수익률 히트맵 (종목별)")
if "Symbol" in df.columns and "Return Rate" in df.columns:
    plot_df = df.dropna(subset=["Return Rate"]).copy()
    plot_df = plot_df.sort_values("Return Rate", ascending=True)
    if not plot_df.empty:
        fig = px.bar(
            plot_df.tail(30) if len(plot_df) > 30 else plot_df,
            x="Return Rate",
            y="Symbol",
            orientation="h",
            color="Return Rate",
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
            hover_data=["Buy Tier", "Asset Class", "Market Value"]
            if all(c in plot_df.columns for c in ["Buy Tier", "Asset Class", "Market Value"])
            else None,
        )
        fig.update_layout(
            xaxis_title="수익률 %",
            yaxis_title="",
            margin=dict(l=10, r=10, t=10, b=10),
            height=max(400, len(plot_df) * 18),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)

# ─── Detailed Table ────────────────────────────────────────────────────────
st.markdown("### 📋 상세 표")
display_cols = [
    c
    for c in [
        "Symbol",
        "Buy Tier",
        "Asset Class",
        "Manager",
        "Pay Cycle",
        "Quantity",
        "Avg Price",
        "Current Price",
        "Purchase Cost",
        "Market Value",
        "Return Rate",
        "Per-Share Dividend",
        "Period Dividend",
    ]
    if c in df.columns
]
sort_col = st.selectbox(
    "정렬 기준",
    options=display_cols,
    index=display_cols.index("Return Rate") if "Return Rate" in display_cols else 0,
)
ascending = st.checkbox("오름차순", value=False)
table_df = df[display_cols].sort_values(sort_col, ascending=ascending, na_position="last")

# 단위 적용 (사이드바에서 선택한 단위로 표시)
formatted_df = table_df.copy()
amount_cols = ["Purchase Cost", "Market Value", "Avg Price", "Current Price", "Period Dividend"]
for col in amount_cols:
    if col in formatted_df.columns:
        formatted_df[col] = formatted_df[col].apply(
            lambda v: fmt_amount(v) if v is not None and v == v else "—"
        )

st.dataframe(
    formatted_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Return Rate": st.column_config.NumberColumn("수익률 %", format="%.2f"),
        "Purchase Cost": st.column_config.Column("매입원금"),
        "Market Value": st.column_config.Column("평가금액"),
        "Avg Price": st.column_config.Column("평균가"),
        "Current Price": st.column_config.Column("현재가"),
        "Period Dividend": st.column_config.Column("1회 분배"),
    },
)
