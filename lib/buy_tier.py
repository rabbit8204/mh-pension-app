"""Buy Tier 등급 체계 — 역할 기반 분류.

운용 철학:
  1순위 목표: 월 분배금 ≥ 3,000,000원 달성
  2순위 목표: 자산 가중 수익률 20~30% 구간 유지
  액티브 운용: 수익률 30% 초과 시 매도 → 분배금 종목으로 자본 회전

등급은 종목의 '포트폴리오 내 역할'을 표현:
  - S: 수익률 driver (자본 차익)
  - A, B: 분배금 driver (3M 목표 달성 핵심)
  - C: 안전자산 (30% 룰)
  - D: 분산
  - W, X: 관찰 / 매수 금지
  - 매도 사이클 4단계
"""

from typing import Dict, List, Optional

# 매도 트리거 임계값
PROFIT_TAKE_THRESHOLD = 30.0  # % — S 등급이 이 수익률 초과 시 매도 검토
DIVIDEND_MONTHLY_TARGET = 3_000_000  # 원 — 월 분배 목표
TARGET_RETURN_LOWER = 20.0  # % — 가중 수익률 하한 목표
TARGET_RETURN_UPPER = 30.0  # % — 가중 수익률 상한 목표 (초과 시 회전 검토)

BUY_TIERS: List[Dict] = [
    {
        "code": "S",
        "label": "Capital Growth",
        "korean": "수익률 driver",
        "definition": "자본 차익 추구. 분배 적음/없음. 수익률 견인 핵심 역할.",
        "trigger": "수익률 30% 도달 시 매도 후보 → 자본 회전",
        "color": "red",
        "role": "growth",
    },
    {
        "code": "A",
        "label": "Income Active",
        "korean": "분배 핵심",
        "definition": "고분배 적극 매수. 월 3백만원 목표 달성의 핵심 종목.",
        "trigger": "매월 정기 매수 + 분배 일관성 확인",
        "color": "orange",
        "role": "income",
    },
    {
        "code": "B",
        "label": "Income Balanced",
        "korean": "분배 안정",
        "definition": "안정 분배 + 약간의 자본 성장. A의 보완 역할.",
        "trigger": "매월 정기 매수, 비중 유지",
        "color": "yellow",
        "role": "income",
    },
    {
        "code": "C",
        "label": "Conservative",
        "korean": "안전자산",
        "definition": "채권혼합 / TDF. 30% 안전자산 룰 충족용 (DC/IRP).",
        "trigger": "안전자산 비중 모니터링",
        "color": "green",
        "role": "safety",
    },
    {
        "code": "D",
        "label": "Diversification",
        "korean": "분산",
        "definition": "신규 진입 / 소액 분산. 시험적 비중.",
        "trigger": "비중 5% 이내 유지",
        "color": "blue",
        "role": "diversification",
    },
    {
        "code": "W (Watch)",
        "label": "Watchlist",
        "korean": "관찰",
        "definition": "관찰 중, 매수 보류. 시장/단가 확인 단계.",
        "trigger": "단가 / 시장 확인 후 등급 재분류",
        "color": "gray",
        "role": "watch",
    },
    {
        "code": "X (No Buy)",
        "label": "Hold Only",
        "korean": "매수 금지",
        "definition": "보유만 유지, 신규 매수 X.",
        "trigger": "정기 검토로 매도/등급 변경 판단",
        "color": "default",
        "role": "hold",
    },
    {
        "code": "매도예정",
        "label": "Sell Pending",
        "korean": "매도 계획",
        "definition": "가까운 시일 내 매도 계획. 출구 준비 단계.",
        "trigger": "매도 시점 결정 → 자본 회전 준비",
        "color": "red",
        "role": "exit",
    },
    {
        "code": "부분매도",
        "label": "Partial Sell",
        "korean": "부분 매도",
        "definition": "일부 매도 진행 중. 비중 축소 단계.",
        "trigger": "남은 비중 / 회전 비율 모니터링",
        "color": "purple",
        "role": "exit",
    },
    {
        "code": "매도완료(예수대기)",
        "label": "Sold (Settling)",
        "korean": "정산 대기",
        "definition": "매도 체결, 예수금 정산 대기 (T+2).",
        "trigger": "T+2 후 재배치 가능",
        "color": "pink",
        "role": "exit",
    },
    {
        "code": "매도완료",
        "label": "Sold",
        "korean": "완전 매도",
        "definition": "완전 매도. 포지션 종료, 보유 0.",
        "trigger": "이력만 보존 — 신규 매수 시 등급 재부여",
        "color": "brown",
        "role": "exit",
    },
]

# Quick lookup by code
BUY_TIER_MAP: Dict[str, Dict] = {t["code"]: t for t in BUY_TIERS}


def get_tier(code: Optional[str]) -> Optional[Dict]:
    """Code → tier dict 조회."""
    if not code:
        return None
    return BUY_TIER_MAP.get(code)


def is_growth_tier(code: Optional[str]) -> bool:
    """S 등급 (수익률 driver) 여부."""
    return code == "S"


def is_income_tier(code: Optional[str]) -> bool:
    """A 또는 B 등급 (분배 driver) 여부."""
    return code in ("A", "B")


def is_active_tier(code: Optional[str]) -> bool:
    """현재 보유 중인 (매도 X) 등급 여부."""
    if not code:
        return True
    return code not in ("매도완료", "매도완료(예수대기)")
