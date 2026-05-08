"""Buy Strategy — 계좌별 매수 비중 가이드 + 입금액 시뮬레이터."""

import pandas as pd
import streamlit as st

from lib.sidebar import fmt_amount, render_sidebar
from lib.style import inject_toss_style

st.set_page_config(page_title="매수 가이드", page_icon="🎯", layout="wide")
inject_toss_style()
render_sidebar()
st.title("🎯 매수 비중 가이드")
st.caption(
    "Buy Strategy v2.0 기반 — 비중대로 종목별 매수 금액 자동 계산. "
    "분배 흐름 미래 예측은 **[🔮 Simulator]** 페이지 참고."
)

# Buy ratios per account (v2.0 confirmed)
BUY_RATIOS = {
    "삼성-DC": {
        "default_amount": 1_200_000,
        "rule": "30% 안전자산 룰 (실제 50% 권고)",
        "items": [
            {"symbol": "타) 미국S&P500 타겟데일리 CC", "ratio": 17, "tier": "S"},
            {"symbol": "키) 고배당", "ratio": 17, "tier": "S"},
            {"symbol": "타) 미국배당다우존스", "ratio": 16, "tier": "B"},
            {"symbol": "코) 테슬라 CC 채권혼합 액티브", "ratio": 21, "tier": "S"},
            {"symbol": "라) 삼성SK 채혼50", "ratio": 15, "tier": "C"},
            {"symbol": "플) 고배당주 채혼", "ratio": 14, "tier": "C"},
        ],
    },
    "삼성-IRP(002)": {
        "default_amount": 340_000,
        "rule": "30% 안전자산 + 분기 (3·6·9·12) 보강",
        "items": [
            {"symbol": "코) 미국AI테크TOP10 CC", "ratio": 29, "tier": "A"},
            {"symbol": "타) 미국S&P500 타겟데일리 CC", "ratio": 22, "tier": "S"},
            {"symbol": "라) 삼성SK 채혼50", "ratio": 21, "tier": "C"},
            {"symbol": "코) 고배당주", "ratio": 14, "tier": "S"},
            {"symbol": "코) 미국S&P500 배당귀족 CC(합성H) 분기", "ratio": 14, "tier": "D"},
        ],
    },
    "삼성-연금저축": {
        "default_amount": 300_000,
        "rule": "30% 룰 없음 / 세액공제 대상",
        "items": [
            {"symbol": "코) 고배당주", "ratio": 33, "tier": "S"},
            {"symbol": "라) 미국S&P500_분기지급 (1·4·7·10)", "ratio": 27, "tier": "D"},
            {"symbol": "솔) 미국배당다우존스", "ratio": 20, "tier": "B"},
            {"symbol": "라) 글로벌 리얼티인컴", "ratio": 20, "tier": "B"},
        ],
    },
    "KB-연금저축": {
        "default_amount": 300_000,
        "rule": "비공제 의도 / NAV 안정 우선",
        "items": [
            {"symbol": "코) 미국AI테크TOP10 CC", "ratio": 40, "tier": "A"},
            {"symbol": "솔) 미국배당다우존스", "ratio": 33, "tier": "B"},
            {"symbol": "라) 글로벌 리얼티인컴", "ratio": 17, "tier": "B"},
            {"symbol": "코) 미국배당다우존스", "ratio": 10, "tier": "B"},
        ],
    },
    "삼성-ISA (5월~9월)": {
        "default_amount": 300_000,
        "rule": "비과세 / 9월까지 30만 입금",
        "items": [
            {"symbol": "타) 미국S&P500 타겟데일리 CC", "ratio": 33, "tier": "S"},
            {"symbol": "솔) 미국배당다우존스", "ratio": 33, "tier": "B"},
            {"symbol": "코) 고배당주", "ratio": 34, "tier": "S"},
        ],
    },
    "삼성-ISA (10월~)": {
        "default_amount": 500_000,
        "rule": "10월부터 50만으로 증액",
        "items": [
            {"symbol": "타) 미국S&P500 타겟데일리 CC", "ratio": 20, "tier": "S"},
            {"symbol": "솔) 미국배당다우존스", "ratio": 20, "tier": "B"},
            {"symbol": "코) 고배당주", "ratio": 20, "tier": "S"},
            {"symbol": "타) 미국나스닥100 타겟데일리 CC", "ratio": 20, "tier": "A"},
            {"symbol": "코) 미국AI테크TOP10 CC (Cleanup 해소)", "ratio": 20, "tier": "A"},
        ],
    },
}


def render_account(name: str, config: dict) -> None:
    st.markdown(f"### 🏦 {name}")
    st.caption(config["rule"])

    amount = st.number_input(
        f"이번 달 매수 금액 ({name})",
        min_value=0,
        step=10_000,
        value=config["default_amount"],
        key=f"amt_{name}",
    )

    rows = []
    for item in config["items"]:
        amt = amount * item["ratio"] / 100
        rows.append(
            {
                "종목": item["symbol"],
                "등급": item["tier"],
                "비중": f"{item['ratio']}%",
                "매수 금액": int(round(amt)),
            }
        )

    df = pd.DataFrame(rows)
    total = df["매수 금액"].sum()
    rem = amount - total

    df_display = df.copy()
    df_display["매수 금액"] = df_display["매수 금액"].apply(fmt_amount)

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
    )

    cols = st.columns(3)
    cols[0].metric("총 배분", fmt_amount(total))
    cols[1].metric("입금액", fmt_amount(amount))
    cols[2].metric("잔액", fmt_amount(rem), delta_color="off" if rem == 0 else "normal")
    st.markdown("---")


# Sidebar - quick toggle
with st.sidebar:
    st.markdown("### 빠른 입금액 변경")
    multiplier = st.slider("일괄 배수 (×)", 0.5, 2.0, 1.0, 0.05)
    st.caption("기본 입금액에 배수 곱해 빠른 시나리오 비교")

# Render all accounts
total_amount = 0
total_distributed = 0

for name, config in BUY_RATIOS.items():
    config = config.copy()
    config["default_amount"] = int(config["default_amount"] * multiplier)
    render_account(name, config)
    total_amount += st.session_state.get(f"amt_{name}", config["default_amount"])

st.markdown("## 📊 전체 합계")
cols = st.columns(3)
cols[0].metric("월 신규 입금 총합", fmt_amount(total_amount))
cols[1].metric("계좌 수", f"{len(BUY_RATIOS)}개")
cols[2].metric("연 환산", fmt_amount(total_amount * 12))

st.info(
    "**원칙**: 금액은 매월 사용자 조정. 비중(%)은 v2.0 가이드 그대로. "
    "분기 사이클 보강 종목(D 등급)은 약점 사이클 균형용 — 매월 매수해도 OK."
)

st.markdown("---")
st.markdown(
    """
### ❌ 매수 X 종목 (참고)
- **코) 200타겟위클리 CC** (ISA): 위클리 CC NAV 침식 우려
- **타) 코스피고배당_분기** (KB연저): (2·5·8·11) 과중
- **분기 종목 다수 (2·5·8·11)**: 과중
- **TDF 3종**: 25% 매도 진행 중 (DC, IRP-001 50%, IRP-002)
- **IRP(001) 모든 종목**: 입금 불가 계좌 (운용으로만 종목 전환)

### 🛡️ 절대 룰
- 종목당 ≤ 20% (총 투자금액)
- 현금 비중 ≥ 20% lock
- 손절가 / 목표가 사전 정의 의무
"""
)
