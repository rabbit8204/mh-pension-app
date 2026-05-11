"""월별 비교 — 두 시점의 Holdings 스냅샷을 나란히 비교.

예: 2026-05 vs 2026-08 → 자산/수익률/배당 변동 한눈에.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.auth import check_password
from lib.notion import (
    get_accounts_df,
    get_holdings_for_period,
    list_snapshot_months,
)
from lib.sidebar import fmt_amount, fmt_pct, render_sidebar
from lib.style import LOSS_COLOR, PROFIT_COLOR, TOSS, inject_toss_style
from lib.transform import (
    annualize_period_dividend,
    compute_account_kpis,
    compute_total_kpis,
    filter_active_holdings,
)

st.set_page_config(page_title="월별 비교", page_icon="📆", layout="wide")
inject_toss_style()

if not check_password():
    st.stop()

render_sidebar()

st.title("📆 월별 비교")
st.caption(
    "두 시점의 Holdings 스냅샷을 비교 — 자산·수익률·배당이 어떻게 변했는지 한눈에 확인. "
    "스냅샷은 매월 1회 `scripts/seed_snapshot.py`로 생성."
)

# ─── 시점 선택 ──────────────────────────────────────────────────────────────
try:
    past_months = list_snapshot_months()
except Exception as exc:
    st.error(f"노션 연결 실패: {exc}")
    st.stop()

options = ["최신"] + past_months
if len(options) < 2:
    st.info(
        f"비교를 위해서는 최소 1개 이상의 과거 스냅샷이 필요합니다. "
        f"현재 사용 가능한 시점: {options}\n\n"
        "**스냅샷 추가 방법**: `python scripts/seed_snapshot.py YYYY-MM` 실행."
    )
    st.stop()

c1, c2, _ = st.columns([1, 1, 2])
with c1:
    base = st.selectbox("📌 기준 시점 (Base)", options=options, index=min(1, len(options) - 1))
with c2:
    compare = st.selectbox("📌 비교 시점 (vs)", options=options, index=0)

if base == compare:
    st.warning("같은 시점을 선택했습니다. 다른 시점을 골라주세요.")
    st.stop()


def _kpis(period: str):
    holdings = filter_active_holdings(get_holdings_for_period(period))
    accounts = get_accounts_df()
    kpi = compute_account_kpis(accounts, holdings)
    totals = compute_total_kpis(kpi)

    if not holdings.empty:
        annual_div = holdings.apply(annualize_period_dividend, axis=1).sum()
    else:
        annual_div = 0
    monthly_div = annual_div / 12

    return {
        "totals": totals,
        "kpi": kpi,
        "annual_div": annual_div,
        "monthly_div": monthly_div,
        "n_holdings": len(holdings),
    }


with st.spinner("스냅샷 비교 중..."):
    base_data = _kpis(base)
    cmp_data = _kpis(compare)


# ─── KPI 비교 ──────────────────────────────────────────────────────────────
def _delta_str(b: float, c: float, fmt) -> str:
    diff = c - b
    sign = "+" if diff > 0 else ""
    return f"{sign}{fmt(diff)}"


st.markdown(f"### 📊 핵심 지표 변화 — {base} → {compare}")
m1, m2, m3, m4, m5 = st.columns(5)

m1.metric(
    "총 자산",
    fmt_amount(cmp_data["totals"]["total_assets"]),
    _delta_str(
        base_data["totals"]["total_assets"],
        cmp_data["totals"]["total_assets"],
        fmt_amount,
    ),
)
m2.metric(
    "평가금액",
    fmt_amount(cmp_data["totals"]["total_market_value"]),
    _delta_str(
        base_data["totals"]["total_market_value"],
        cmp_data["totals"]["total_market_value"],
        fmt_amount,
    ),
)
m3.metric(
    "현금",
    fmt_amount(cmp_data["totals"]["total_cash"]),
    _delta_str(
        base_data["totals"]["total_cash"],
        cmp_data["totals"]["total_cash"],
        fmt_amount,
    ),
)
m4.metric(
    "가중수익률",
    fmt_pct(cmp_data["totals"]["weighted_return"]),
    f"{(cmp_data['totals']['weighted_return'] - base_data['totals']['weighted_return']):+.2f}%p",
)
m5.metric(
    "월 분배 (예상)",
    fmt_amount(cmp_data["monthly_div"]),
    _delta_str(base_data["monthly_div"], cmp_data["monthly_div"], fmt_amount),
)

# ─── 계좌별 비교 표 ────────────────────────────────────────────────────────
st.markdown("### 🏦 계좌별 비교")

if base_data["kpi"].empty or cmp_data["kpi"].empty:
    st.info("계좌별 KPI 비교 데이터가 부족합니다.")
else:
    base_k = base_data["kpi"][
        ["account_name", "sum_market_value", "total_assets", "return_rate"]
    ].rename(
        columns={
            "sum_market_value": f"평가({base})",
            "total_assets": f"총자산({base})",
            "return_rate": f"수익률({base})",
        }
    )
    cmp_k = cmp_data["kpi"][
        ["account_name", "sum_market_value", "total_assets", "return_rate"]
    ].rename(
        columns={
            "sum_market_value": f"평가({compare})",
            "total_assets": f"총자산({compare})",
            "return_rate": f"수익률({compare})",
        }
    )
    merged = base_k.merge(cmp_k, on="account_name", how="outer")
    merged["Δ평가"] = merged.get(f"평가({compare})", 0).fillna(0) - merged.get(
        f"평가({base})", 0
    ).fillna(0)
    merged["Δ수익률(%p)"] = merged.get(f"수익률({compare})", 0).fillna(0) - merged.get(
        f"수익률({base})", 0
    ).fillna(0)

    # Format
    fmt_cols = [
        f"평가({base})",
        f"총자산({base})",
        f"평가({compare})",
        f"총자산({compare})",
        "Δ평가",
    ]
    for c in fmt_cols:
        if c in merged.columns:
            merged[c] = merged[c].apply(
                lambda v: fmt_amount(v) if pd.notna(v) else "—"
            )
    for c in [f"수익률({base})", f"수익률({compare})"]:
        if c in merged.columns:
            merged[c] = merged[c].apply(
                lambda v: f"{v:.2f}%" if pd.notna(v) else "—"
            )
    merged["Δ수익률(%p)"] = merged["Δ수익률(%p)"].apply(
        lambda v: f"{v:+.2f}" if pd.notna(v) else "—"
    )

    merged = merged.rename(columns={"account_name": "계좌"})
    st.dataframe(merged, use_container_width=True, hide_index=True)

# ─── 종목별 변동 표 (수익률 차이) ──────────────────────────────────────────
st.markdown("### 📋 종목별 수익률 변화")

base_h = filter_active_holdings(get_holdings_for_period(base))
cmp_h = filter_active_holdings(get_holdings_for_period(compare))

if base_h.empty or cmp_h.empty:
    st.info("종목 데이터가 부족합니다.")
else:
    # Merge by Symbol
    bh = base_h[["Symbol", "Market Value", "Return Rate", "Buy Tier", "Asset Class"]].rename(
        columns={
            "Market Value": f"평가({base})",
            "Return Rate": f"수익률({base})",
        }
    )
    ch = cmp_h[["Symbol", "Market Value", "Return Rate"]].rename(
        columns={
            "Market Value": f"평가({compare})",
            "Return Rate": f"수익률({compare})",
        }
    )
    sym_merged = bh.merge(ch, on="Symbol", how="outer")
    sym_merged["Δ수익률(%p)"] = sym_merged[f"수익률({compare})"].fillna(0) - sym_merged[
        f"수익률({base})"
    ].fillna(0)
    sym_merged["Δ평가"] = sym_merged[f"평가({compare})"].fillna(0) - sym_merged[
        f"평가({base})"
    ].fillna(0)

    sort_by = st.selectbox(
        "정렬",
        options=["Δ수익률(%p)", "Δ평가", f"수익률({compare})", "Symbol"],
        index=0,
    )
    asc = st.checkbox("오름차순", value=False)
    sym_merged = sym_merged.sort_values(sort_by, ascending=asc, na_position="last")

    # Format
    for c in [f"평가({base})", f"평가({compare})", "Δ평가"]:
        sym_merged[c] = sym_merged[c].apply(
            lambda v: fmt_amount(v) if pd.notna(v) else "—"
        )
    for c in [f"수익률({base})", f"수익률({compare})"]:
        sym_merged[c] = sym_merged[c].apply(
            lambda v: f"{v:.2f}%" if pd.notna(v) else "—"
        )
    sym_merged["Δ수익률(%p)"] = sym_merged["Δ수익률(%p)"].apply(
        lambda v: f"{v:+.2f}" if pd.notna(v) else "—"
    )

    st.dataframe(sym_merged, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption(
    f"**스냅샷 운영**: 매월 1회 `scripts/seed_snapshot.py YYYY-MM` 실행으로 새 시점 추가. "
    f"한 번 저장되면 영구 보존되어 시계열 추적 가능."
)
