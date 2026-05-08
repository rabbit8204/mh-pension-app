"""Password gate for Streamlit app.

URL이 공개라 비밀번호 게이트로 보호. 비밀번호는 Streamlit Secrets의
APP_PASSWORD에 저장 (코드에 노출 X).
"""

import os

import streamlit as st


def _get_password() -> str:
    """Read APP_PASSWORD from env (.env locally) or st.secrets (Cloud)."""
    val = os.getenv("APP_PASSWORD")
    if val:
        return val
    try:
        if hasattr(st, "secrets") and "APP_PASSWORD" in st.secrets:
            return st.secrets["APP_PASSWORD"]
    except Exception:
        pass
    return ""


def check_password() -> bool:
    """Return True if user has authenticated. Block page render otherwise.

    Call at the top of every page, right after page_config + style:
        if not check_password():
            st.stop()
    """
    expected = _get_password()
    # 비밀번호가 설정되지 않은 경우 (로컬 개발 등) → 게이트 비활성화
    if not expected:
        return True

    # 이미 인증됨
    if st.session_state.get("_authenticated"):
        return True

    # 인증 화면
    st.markdown(
        """
<style>
.auth-container {
    max-width: 380px;
    margin: 80px auto 0 auto;
    padding: 32px 28px;
    background: #FFFFFF;
    border-radius: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    text-align: center;
}
.auth-emoji {
    font-size: 48px;
    margin-bottom: 8px;
}
.auth-title {
    font-size: 20px;
    font-weight: 700;
    color: #191F28;
    letter-spacing: -0.02em;
    margin-bottom: 6px;
}
.auth-sub {
    font-size: 14px;
    color: #8B95A1;
    margin-bottom: 20px;
}
</style>
<div class="auth-container">
    <div class="auth-emoji">🔒</div>
    <div class="auth-title">MH Pension Dashboard</div>
    <div class="auth-sub">접속하려면 비밀번호를 입력하세요</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Center the input column
    cols = st.columns([1, 2, 1])
    with cols[1]:
        password = st.text_input(
            " ",  # 공백 라벨
            type="password",
            placeholder="비밀번호",
            key="_password_input",
            label_visibility="collapsed",
        )
        submit = st.button("로그인", use_container_width=True)

        if submit or password:
            if password == expected:
                st.session_state["_authenticated"] = True
                st.rerun()
            elif password:  # 입력은 있는데 틀림
                st.error("비밀번호가 일치하지 않습니다.")

    return False
