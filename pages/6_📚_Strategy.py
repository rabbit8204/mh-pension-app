"""Strategy — 전략가 학습 노트 대시보드.

옵시디언 Strategy_Notes 폴더를 직접 읽어 표시.
"""

from pathlib import Path
import re

import streamlit as st

from lib.auth import check_password
from lib.buy_tier import (
    DIVIDEND_MONTHLY_TARGET,
    PROFIT_TAKE_THRESHOLD,
    TARGET_RETURN_LOWER,
    TARGET_RETURN_UPPER,
)
from lib.sidebar import fmt_amount, render_sidebar
from lib.style import inject_toss_style

NOTES_DIR = Path("/Users/manhyunglee/Desktop/01_MH_Finance/00_MH_Finance/Strategy_Notes")

st.set_page_config(page_title="Strategy", page_icon="📚", layout="wide")
inject_toss_style()

if not check_password():
    st.stop()

render_sidebar()

st.title("📚 Strategy — 전략가 학습 대시보드")
st.caption("Claude가 학습한 외부 지식 + 의사결정 로그 누적")

# ─── 운용 철학 ─────────────────────────────────────────────────────────────
st.markdown("### 🎯 운용 철학")
c1, c2, c3 = st.columns(3)
c1.metric("1순위 — 월 분배금", f"≥ {fmt_amount(DIVIDEND_MONTHLY_TARGET)}", "A, B 등급")
c2.metric("2순위 — 가중 수익률", f"{TARGET_RETURN_LOWER}~{TARGET_RETURN_UPPER}%", "S 등급")
c3.metric("액티브 — 매도 트리거", f"{PROFIT_TAKE_THRESHOLD}% 초과", "S → A/B 회전")

# ─── 거시 변수 (최신 Macro 노트) ───────────────────────────────────────────
st.markdown("### 🌐 거시 변수 (최신)")
macro_dir = NOTES_DIR / "Macro"
if macro_dir.exists():
    macro_files = sorted(macro_dir.glob("*.md"), reverse=True)
    if macro_files:
        latest = macro_files[0]
        with st.expander(f"📊 {latest.stem} (클릭하여 펼치기)", expanded=False):
            st.markdown(latest.read_text(encoding="utf-8"))
    else:
        st.info("거시 노트 없음.")
else:
    st.info("Macro 폴더 없음.")

# ─── 의사결정 로그 ─────────────────────────────────────────────────────────
st.markdown("### 📝 의사결정 로그")
decisions_dir = NOTES_DIR / "Decisions"
if decisions_dir.exists():
    decision_files = sorted(decisions_dir.glob("*.md"), reverse=True)
    for d in decision_files:
        content = d.read_text(encoding="utf-8")
        # Extract topic / status from frontmatter
        fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
        topic = d.stem
        status = "?"
        date = ""
        if fm_match:
            fm = fm_match.group(1)
            topic_m = re.search(r"^topic:\s*(.+)$", fm, re.MULTILINE)
            if topic_m:
                topic = topic_m.group(1).strip()
            status_m = re.search(r"^status:\s*(.+)$", fm, re.MULTILINE)
            if status_m:
                status = status_m.group(1).strip()
            date_m = re.search(r"^date:\s*(.+)$", fm, re.MULTILINE)
            if date_m:
                date = date_m.group(1).strip()

        status_emoji = "✅" if status.upper() == "DECIDED" else "🔍" if status == "research" else "⏸"
        with st.expander(f"{status_emoji} {date} — {topic} `{status}`", expanded=False):
            st.markdown(content)
else:
    st.info("의사결정 로그 없음.")

# ─── 학습 노트 인덱스 ──────────────────────────────────────────────────────
st.markdown("### 📚 학습 노트 인덱스")
ic1, ic2, ic3 = st.columns(3)

symbols_dir = NOTES_DIR / "Symbols"
symbol_count = len(list(symbols_dir.glob("*.md"))) if symbols_dir.exists() else 0
ic1.metric("📊 종목 노트", f"{symbol_count}개")

macro_count = len(list((NOTES_DIR / "Macro").glob("*.md"))) if (NOTES_DIR / "Macro").exists() else 0
ic2.metric("🌐 거시 노트", f"{macro_count}개")

sources_dir = NOTES_DIR / "Sources"
source_count = sum(
    len(list(sub.glob("*.md"))) for sub in sources_dir.iterdir() if sub.is_dir()
) if sources_dir.exists() else 0
ic3.metric("📺 학습 자료", f"{source_count}개")

# ─── 종목 학습 상태 ────────────────────────────────────────────────────────
if symbols_dir.exists():
    with st.expander("📋 종목 노트 학습 상태 (전체)", expanded=False):
        rows = []
        for sf in sorted(symbols_dir.glob("*.md")):
            content = sf.read_text(encoding="utf-8")
            status_m = re.search(r"^status:\s*(.+)$", content[:500], re.MULTILINE)
            status = status_m.group(1).strip() if status_m else "?"
            emoji = "📚" if status == "learned" else "⏸"
            rows.append({"status": emoji, "노트": sf.stem.replace("__", " · ")})

        st.dataframe(rows, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption(
    "📚 학습 노트 원본: 옵시디언 vault `00_MH_Finance/Strategy_Notes/` · "
    "Streamlit은 파일 직접 읽기 · Vercel은 빌드 시 JSON 컴파일"
)
