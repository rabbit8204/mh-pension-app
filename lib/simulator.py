"""Forward-projection simulator.

Given current account state and per-account monthly contributions, project:
- Monthly capital growth
- Monthly dividend flow
- Time to reach target

Model (단순 — 빠른 반응속도 + 직관적):
  capital(t+1) = capital(t) + contribution + (dividend(t) × reinvest_rate)
  dividend(t+1) = capital(t+1) × yield / 12

Yield is held constant at the account's current implicit yield.
"""

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd


@dataclass
class AccountState:
    name: str
    capital: float  # 평가금액 (현재)
    annual_yield_pct: float  # 연 분배율 % (현재 implicit)
    annual_nav_growth_pct: float  # 연 NAV 성장률 % (시세 손익, TDF/주식형 등)
    monthly_contribution: float  # 월 신규 입금 (사용자 가변)


def project(
    accounts: List[AccountState],
    months: int,
    reinvest_rate: float = 1.0,
    target_monthly_dividend: float = 3_000_000,
) -> pd.DataFrame:
    """Run forward projection for given accounts and time horizon.

    Model:
      capital(t+1) = capital(t) × (1 + nav_growth/12)   ← NAV 성장 (TDF, 주식형)
                   + contribution                       ← 월 신규 입금
                   + dividend(t) × reinvest_rate        ← 분배금 재투자
      dividend(t)  = capital(t) × yield / 12

    Two return components:
      - dividend (현금 흐름) — yield 기반
      - NAV (capital appreciation) — nav_growth_pct 기반
    Total return = both combined.
    """
    rows = []

    state: Dict[str, Dict[str, float]] = {}
    for acc in accounts:
        state[acc.name] = {
            "capital": acc.capital,
            "yield": acc.annual_yield_pct / 100.0,
            "nav_growth": acc.annual_nav_growth_pct / 100.0,
            "contribution": acc.monthly_contribution,
            "initial_capital": acc.capital,
        }

    target_reached_month = None

    for t in range(months + 1):
        row = {"month": t}
        total_cap = 0.0
        total_div_monthly = 0.0
        for name, s in state.items():
            row[f"capital_{name}"] = s["capital"]
            monthly_div = s["capital"] * s["yield"] / 12.0
            row[f"div_{name}"] = monthly_div
            total_cap += s["capital"]
            total_div_monthly += monthly_div

        row["total_capital"] = total_cap
        row["total_monthly_dividend"] = total_div_monthly
        row["target_reached"] = total_div_monthly >= target_monthly_dividend
        rows.append(row)

        if total_div_monthly >= target_monthly_dividend and target_reached_month is None:
            target_reached_month = t

        # Advance one month
        if t < months:
            for name, s in state.items():
                month_div = s["capital"] * s["yield"] / 12.0
                # NAV 성장 → 자본에 곱셈 (월 단위 환산)
                s["capital"] = (
                    s["capital"] * (1 + s["nav_growth"] / 12.0)
                    + s["contribution"]
                    + month_div * reinvest_rate
                )

    df = pd.DataFrame(rows)
    df.attrs["target_reached_month"] = target_reached_month
    return df


def compare_scenarios(
    base_accounts: List[AccountState],
    scenarios: Dict[str, Dict[str, float]],
    months: int,
    reinvest_rate: float = 1.0,
) -> Dict[str, pd.DataFrame]:
    """Run multiple scenarios and return dict of name → projection DataFrame."""
    results = {}
    for scen_name, contrib_map in scenarios.items():
        accounts_for_scen = [
            AccountState(
                name=a.name,
                capital=a.capital,
                annual_yield_pct=a.annual_yield_pct,
                annual_nav_growth_pct=a.annual_nav_growth_pct,
                monthly_contribution=contrib_map.get(a.name, a.monthly_contribution),
            )
            for a in base_accounts
        ]
        results[scen_name] = project(accounts_for_scen, months, reinvest_rate)
    return results
