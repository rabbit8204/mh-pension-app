"""Global sidebar — every page imports & calls render_sidebar()."""

import streamlit as st

from lib.notion import clear_cache


CURRENCY_DIVISORS = {
    "원": 1,
    "만원": 10_000,
    "백만원": 1_000_000,
}


def render_sidebar() -> None:
    """Persistent sidebar: 단위 / 새로고침 / 도움말."""
    with st.sidebar:
        st.markdown("### ⚙️ 도구")

        # 단위
        unit = st.selectbox(
            "💱 표시 단위",
            options=list(CURRENCY_DIVISORS.keys()),
            index=0,
            key="currency_unit",
            help="모든 금액 표시에 적용",
        )
        st.session_state["unit_divisor"] = CURRENCY_DIVISORS[unit]
        st.session_state["unit_label"] = unit

        # Refresh
        if st.button("🔄 노션 데이터 새로고침", use_container_width=True):
            clear_cache()
            st.rerun()

        # Quick links
        st.markdown("---")
        st.markdown("### 🔗 노션 직접 편집")
        st.markdown(
            "- [💰 Pension Dashboard](https://www.notion.so/359fabacbbb081ac8b24da7f8736bab9)\n"
            "- [📊 Holdings DB](https://www.notion.so/fb793b4172e349f79184c1ac3598235f)\n"
            "- [💸 Cashflow DB](https://www.notion.so/3e03524a32cb4c6b911a9a943fb88f0b)\n"
            "- [🎯 Buy Strategy](https://www.notion.so/359fabacbbb0810683dfcfe3063e9897)"
        )

        st.markdown("---")
        st.caption("**MVP v1.0** · Streamlit · 5분 캐시")


def fmt_amount(value: float, decimals: int = 0) -> str:
    """Format a won amount according to current unit setting."""
    if value is None:
        return "—"
    divisor = st.session_state.get("unit_divisor", 1)
    label = st.session_state.get("unit_label", "원")
    scaled = value / divisor
    if decimals == 0:
        return f"{scaled:,.0f}{label}"
    return f"{scaled:,.{decimals}f}{label}"


def fmt_pct(value: float, decimals: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f}%"
