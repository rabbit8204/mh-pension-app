"""Simulator — '얼마를 어디에 넣으면 어떻게 변할까?' What-if 시뮬레이션.

v1.2: NAV 성장 별도 모델링 추가 (TDF/주식형/CC 등 자산 클래스별 차등).
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.notion import get_accounts_df, get_holdings_df
from lib.sidebar import fmt_amount, render_sidebar
from lib.simulator import AccountState, compare_scenarios, project
from lib.style import (
    LOSS_COLOR,
    PROFIT_COLOR,
    TOSS,
    get_plotly_layout_defaults,
    inject_toss_style,
)
from lib.transform import (
    DEFAULT_NAV_GROWTH_BY_CLASS,
    compute_account_nav_growth,
    compute_account_yields,
)

st.set_page_config(page_title="시뮬레이터", page_icon="🔮", layout="wide")
inject_toss_style()
render_sidebar()

st.title("🔮 What-If 시뮬레이터")
st.caption(
    "**얼마를 어디에 넣으면 분배금·자산이 어떻게 변할까?** — "
    "월 입금액·재투자율·NAV 성장률을 조절해 미래 캐시플로우와 자산 추이를 즉시 확인. "
    "v1.2: TDF NAV 성장 별도 모델링."
)

# ─── Data load ─────────────────────────────────────────────────────────────
try:
    accounts_df = get_accounts_df()
    holdings_df = get_holdings_df()
except Exception as exc:
    st.error(f"노션 연결 실패: {exc}")
    st.stop()

if accounts_df.empty:
    st.info("Accounts DB가 비어 있습니다.")
    st.stop()

yields_df = compute_account_yields(holdings_df, accounts_df)
nav_growth_df = compute_account_nav_growth(holdings_df, accounts_df)

# Merge NAV growth into yields
nav_dict = dict(
    zip(nav_growth_df["account_id"], nav_growth_df["weighted_nav_growth_pct"])
)

# ─── Input Panel ──────────────────────────────────────────────────────────
st.markdown("### 🎛️ 입력 패널")

ic1, ic2, ic3 = st.columns([2, 1, 1])

with ic1:
    months = st.slider(
        "⏱️ 시뮬레이션 기간 (개월)",
        min_value=6,
        max_value=120,
        value=60,
        step=6,
    )

with ic2:
    reinvest_rate = st.select_slider(
        "💰 분배금 재투자율",
        options=[0.0, 0.25, 0.5, 0.75, 1.0],
        value=1.0,
        format_func=lambda x: f"{int(x*100)}%",
    )

with ic3:
    target = st.number_input(
        "🎯 목표 월 분배금",
        min_value=500_000,
        max_value=10_000_000,
        value=3_000_000,
        step=100_000,
        format="%d",
    )

# ─── Account-level inputs ──────────────────────────────────────────────────
st.markdown("#### 🏦 계좌별 월 입금액 + NAV 성장률")
st.caption(
    "**월 입금액**: 노션 Accounts DB의 Monthly Contribution 기본값. "
    "**NAV 성장률**: 보유 종목의 Asset Class 비중 기반 자동 계산 (TDF +28% / 주식형 +10% / CC −3% / 채권혼합 +3% / REITs +5%). "
    "수동 조정 가능."
)

contributions: dict[str, int] = {}
yields_dict: dict[str, float] = {}
nav_growth_dict: dict[str, float] = {}
capital_dict: dict[str, float] = {}

for _, acc in yields_df.iterrows():
    acc_id = acc["account_id"]
    acc_name = acc["account_name"]
    auto_nav = nav_dict.get(acc_id, 5.0)

    with st.expander(
        f"🏦 **{acc_name}** "
        f"· 평가 {fmt_amount(acc['market_value'])} "
        f"· 분배율 {acc['dividend_yield']:.2f}% "
        f"· NAV 성장 추정 {auto_nav:+.1f}%",
        expanded=False,
    ):
        ec1, ec2 = st.columns(2)
        with ec1:
            default_amt = int(acc["monthly_contribution"] or 0)
            new_amt = st.number_input(
                "월 입금액",
                min_value=0,
                max_value=5_000_000,
                value=default_amt,
                step=10_000,
                key=f"contrib_{acc_id}",
            )
            delta = new_amt - default_amt
            if delta != 0:
                st.caption(
                    f"📊 {'+' if delta > 0 else ''}{int(delta):,}원 "
                    f"vs 현재"
                )
        with ec2:
            new_nav = st.slider(
                "연 NAV 성장률 % (수동 조정)",
                min_value=-10.0,
                max_value=40.0,
                value=float(auto_nav),
                step=0.5,
                key=f"nav_{acc_id}",
                help="음수 = NAV 침식 (커버드콜), 양수 = 성장 (TDF/주식형)",
            )

        contributions[acc_name] = new_amt
        yields_dict[acc_name] = acc["dividend_yield"]
        nav_growth_dict[acc_name] = new_nav
        capital_dict[acc_name] = acc["market_value"]

# 빠른 시나리오 프리셋
st.markdown("#### ⚡ 빠른 시나리오")
preset_cols = st.columns(5)

if preset_cols[0].button("🔄 현행 유지"):
    for _, acc in yields_df.iterrows():
        st.session_state[f"contrib_{acc['account_id']}"] = int(
            acc["monthly_contribution"] or 0
        )
    st.rerun()

if preset_cols[1].button("➕ 모든 +10%"):
    for _, acc in yields_df.iterrows():
        cur = int(acc["monthly_contribution"] or 0)
        st.session_state[f"contrib_{acc['account_id']}"] = int(cur * 1.10)
    st.rerun()

if preset_cols[2].button("➕ 모든 +20%"):
    for _, acc in yields_df.iterrows():
        cur = int(acc["monthly_contribution"] or 0)
        st.session_state[f"contrib_{acc['account_id']}"] = int(cur * 1.20)
    st.rerun()

if preset_cols[3].button("🅿️ ISA 50만"):
    for _, acc in yields_df.iterrows():
        cur = int(acc["monthly_contribution"] or 0)
        if "ISA" in str(acc["account_name"]):
            st.session_state[f"contrib_{acc['account_id']}"] = 500_000
        else:
            st.session_state[f"contrib_{acc['account_id']}"] = cur
    st.rerun()

if preset_cols[4].button("🚀 공격 모드"):
    for _, acc in yields_df.iterrows():
        cur = int(acc["monthly_contribution"] or 0)
        name = str(acc["account_name"])
        if "ISA" in name:
            st.session_state[f"contrib_{acc['account_id']}"] = 1_000_000
        elif "연금저축" in name:
            st.session_state[f"contrib_{acc['account_id']}"] = 500_000
        else:
            st.session_state[f"contrib_{acc['account_id']}"] = int(cur * 1.20)
    st.rerun()

# ─── Run simulation ────────────────────────────────────────────────────────
accounts: list[AccountState] = []
for name, contrib in contributions.items():
    accounts.append(
        AccountState(
            name=name,
            capital=capital_dict[name],
            annual_yield_pct=yields_dict[name],
            annual_nav_growth_pct=nav_growth_dict[name],
            monthly_contribution=contrib,
        )
    )

projection = project(accounts, months, reinvest_rate, target_monthly_dividend=target)

# ─── KPI Result Cards ──────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📊 시뮬레이션 결과")

current = projection.iloc[0]
final = projection.iloc[-1]
total_contrib = sum(contributions.values())
total_contrib_over_period = total_contrib * months
nav_appreciation = final["total_capital"] - current["total_capital"] - total_contrib_over_period

target_month = projection.attrs.get("target_reached_month")

k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "종료 시점 월 분배금",
    fmt_amount(final["total_monthly_dividend"]),
    fmt_amount(final["total_monthly_dividend"] - current["total_monthly_dividend"]),
)
k2.metric(
    "종료 시점 총 자산",
    fmt_amount(final["total_capital"]),
    fmt_amount(final["total_capital"] - current["total_capital"]),
)
k3.metric(
    "이 중 NAV 성장분",
    fmt_amount(nav_appreciation),
    f"누적 입금 {fmt_amount(total_contrib_over_period)} 제외",
)

if target_month is not None:
    yrs = target_month / 12
    k4.metric(
        f"목표 {fmt_amount(target)} 도달",
        f"{target_month}개월 ({yrs:.1f}년)",
        "✓ 시뮬 기간 내 달성",
    )
else:
    growth_per_month = (
        (final["total_monthly_dividend"] - current["total_monthly_dividend"]) / months
        if months > 0
        else 0
    )
    if growth_per_month > 0:
        gap = target - final["total_monthly_dividend"]
        more_months = int(gap / growth_per_month) if growth_per_month else 999
        k4.metric(
            f"목표 {fmt_amount(target)} 도달",
            "기간 내 미달성",
            f"+{more_months}개월 추가 필요 추정",
            delta_color="inverse",
        )
    else:
        k4.metric(f"목표 {fmt_amount(target)} 도달", "기간 내 미달성")

# ─── Charts ────────────────────────────────────────────────────────────────
plotly_defaults = get_plotly_layout_defaults()

st.markdown("### 📈 월별 분배금 추이")
fig1 = go.Figure()
fig1.add_trace(
    go.Scatter(
        x=projection["month"],
        y=projection["total_monthly_dividend"],
        mode="lines",
        line=dict(width=4, color=TOSS["blue_500"]),
        fill="tozeroy",
        fillcolor="rgba(0, 100, 255, 0.10)",
        name="월 분배금 추정",
        hovertemplate="개월: %{x}<br>월 분배금: %{y:,.0f}원<extra></extra>",
    )
)
fig1.add_hline(
    y=target,
    line_dash="dash",
    line_color=PROFIT_COLOR,
    annotation_text=f"목표 {fmt_amount(target)}",
    annotation_position="top right",
)
if target_month is not None:
    fig1.add_vline(
        x=target_month,
        line_dash="dot",
        line_color=TOSS["green_500"],
        annotation_text=f"{target_month}개월차 도달",
        annotation_position="top",
    )
fig1.update_layout(
    height=380,
    margin=dict(l=10, r=10, t=10, b=10),
    xaxis_title="개월 (현재 기준)",
    yaxis_title="월 분배금 (원)",
    yaxis=dict(tickformat=","),
    hovermode="x unified",
    **plotly_defaults,
)
st.plotly_chart(fig1, use_container_width=True)

st.markdown("### 💰 총 자산 추이 (NAV 성장 + 입금 + 재투자 누적)")
fig2 = go.Figure()
fig2.add_trace(
    go.Scatter(
        x=projection["month"],
        y=projection["total_capital"],
        mode="lines",
        line=dict(width=4, color=TOSS["yellow_500"]),
        fill="tozeroy",
        fillcolor="rgba(255, 178, 0, 0.10)",
        name="총 자산",
        hovertemplate="개월: %{x}<br>총 자산: %{y:,.0f}원<extra></extra>",
    )
)
fig2.update_layout(
    height=380,
    margin=dict(l=10, r=10, t=10, b=10),
    xaxis_title="개월",
    yaxis_title="총 자산 (원)",
    yaxis=dict(tickformat=","),
    hovermode="x unified",
    **plotly_defaults,
)
st.plotly_chart(fig2, use_container_width=True)

st.markdown("### 🏦 계좌별 자산 추이 (스택)")
fig3 = go.Figure()
acc_cols = [c for c in projection.columns if c.startswith("capital_")]
toss_palette = [
    TOSS["blue_500"],
    TOSS["yellow_500"],
    TOSS["green_500"],
    "#7B61FF",
    "#FF6B6B",
    "#4ECDC4",
    "#FFA94D",
]
for i, col in enumerate(acc_cols):
    name = col.replace("capital_", "")
    fig3.add_trace(
        go.Scatter(
            x=projection["month"],
            y=projection[col],
            mode="lines",
            stackgroup="one",
            name=name,
            line=dict(color=toss_palette[i % len(toss_palette)]),
            hovertemplate=f"{name}<br>개월: %{{x}}<br>자산: %{{y:,.0f}}원<extra></extra>",
        )
    )
fig3.update_layout(
    height=380,
    margin=dict(l=10, r=10, t=10, b=10),
    xaxis_title="개월",
    yaxis_title="자산 (원, 스택)",
    yaxis=dict(tickformat=","),
    **plotly_defaults,
)
st.plotly_chart(fig3, use_container_width=True)

# ─── Scenario Comparison ───────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🆚 시나리오 비교")
st.caption("위 입력값을 '현재 시뮬'로 두고 다른 표준 시나리오와 비교.")

base_contributions = {
    str(acc["account_name"]): int(acc["monthly_contribution"] or 0)
    for _, acc in yields_df.iterrows()
}

scenarios = {
    "현행 유지": base_contributions,
    "현재 시뮬 (위 입력)": contributions,
    "+10% 입금": {k: int(v * 1.1) for k, v in base_contributions.items()},
    "+20% 입금": {k: int(v * 1.2) for k, v in base_contributions.items()},
}

scenario_results = compare_scenarios(accounts, scenarios, months, reinvest_rate)

fig_compare = go.Figure()
compare_palette = [
    TOSS["gray_400"],
    TOSS["blue_500"],
    TOSS["yellow_500"],
    PROFIT_COLOR,
]
for i, (name, df) in enumerate(scenario_results.items()):
    fig_compare.add_trace(
        go.Scatter(
            x=df["month"],
            y=df["total_monthly_dividend"],
            mode="lines",
            name=name,
            line=dict(width=3, color=compare_palette[i % len(compare_palette)]),
            hovertemplate=f"{name}<br>개월: %{{x}}<br>월 분배: %{{y:,.0f}}원<extra></extra>",
        )
    )
fig_compare.add_hline(
    y=target,
    line_dash="dash",
    line_color=PROFIT_COLOR,
    annotation_text=f"목표 {fmt_amount(target)}",
)
fig_compare.update_layout(
    height=420,
    margin=dict(l=10, r=10, t=10, b=10),
    xaxis_title="개월",
    yaxis_title="월 분배금 (원)",
    yaxis=dict(tickformat=","),
    hovermode="x unified",
    **plotly_defaults,
)
st.plotly_chart(fig_compare, use_container_width=True)

target_table = []
for name, df in scenario_results.items():
    tm = df.attrs.get("target_reached_month")
    final_div = df.iloc[-1]["total_monthly_dividend"]
    final_cap = df.iloc[-1]["total_capital"]
    target_table.append({
        "시나리오": name,
        f"{months}개월 후 월분배금": fmt_amount(final_div),
        f"{months}개월 후 총 자산": fmt_amount(final_cap),
        "목표 도달": f"{tm}개월" if tm is not None else "기간 내 미달성",
    })
st.dataframe(pd.DataFrame(target_table), use_container_width=True, hide_index=True)

# ─── Assumptions ──────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("⚙️ 시뮬레이션 가정 (모델 설명)"):
    st.markdown(
        f"""
**v1.2 모델**:
```
자본(t+1) = 자본(t) × (1 + NAV성장/12)   ← NAV 성장 (TDF/주식형)
          + 월 입금
          + 분배금 × 재투자율             ← 분배 재투자

분배금(t) = 자본(t) × 분배율 / 12
```

**자산 클래스별 기본 NAV 성장률** (수동 조정 가능):
- TDF: **+{DEFAULT_NAV_GROWTH_BY_CLASS['TDF']}%** (실제 관측 27-30% 평균)
- 주식형: +{DEFAULT_NAV_GROWTH_BY_CLASS['주식형']}% (장기 시장 평균)
- 커버드콜: **{DEFAULT_NAV_GROWTH_BY_CLASS['커버드콜']:+}%** (NAV 침식 보수 추정)
- 채권혼합: +{DEFAULT_NAV_GROWTH_BY_CLASS['채권혼합']}%
- REITs: +{DEFAULT_NAV_GROWTH_BY_CLASS['REITs']}%

**계좌별 자동 NAV 성장률**: 보유 종목의 Asset Class 비중 × 클래스별 성장률 가중 평균. 위 expander에서 수동 조정 가능.

**한계**:
- 분배율은 시뮬 기간 동안 상수 가정 (실제는 변동)
- NAV 성장률도 상수 (시장 사이클 고려 X)
- 새 입금의 효과는 매수 비중 가이드 적용 필요 (별도 페이지)

**v1.3 개선 예정**:
- Buy Strategy v2.0 비중 따라 새 입금의 정확한 yield/growth 자동 계산
- 시장 사이클별 NAV 성장률 시나리오 (강세/약세/혼란장)
"""
    )
