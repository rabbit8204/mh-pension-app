"""Pure data transformations on the fetched DataFrames."""

from typing import Dict, List

import pandas as pd


def compute_account_kpis(accounts_df: pd.DataFrame, holdings_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate Holdings by Account → matched to Accounts DB.

    Returns: DataFrame with one row per account, columns:
      account_name, broker, account_type, monthly_contribution,
      n_holdings, sum_purchase_cost, sum_market_value, sum_pl, return_rate
    """
    if accounts_df.empty:
        return pd.DataFrame()

    acc = accounts_df.copy()
    acc["_id_short"] = acc["_page_id"].str.replace("-", "")

    h = holdings_df.copy() if not holdings_df.empty else pd.DataFrame()

    if h.empty:
        # No holdings yet, return accounts with zeros
        out = acc[["Account Name", "Broker", "Account Type", "Monthly Contribution (원)"]].copy()
        out["n_holdings"] = 0
        out["sum_purchase_cost"] = 0
        out["sum_market_value"] = 0
        out["sum_pl"] = 0
        out["return_rate"] = 0
        return out

    # Account relation can be a list of page urls or page ids
    def _account_match(account_field, acc_id_short: str, acc_url: str) -> bool:
        if not account_field:
            return False
        if isinstance(account_field, list):
            for ref in account_field:
                if not ref:
                    continue
                if isinstance(ref, str):
                    if acc_id_short in ref.replace("-", ""):
                        return True
        elif isinstance(account_field, str):
            if acc_id_short in account_field.replace("-", ""):
                return True
        return False

    # Holdings store Account as JSON array of page URLs in our schema
    def _account_match_str(account_value, acc_id_short: str) -> bool:
        if account_value is None:
            return False
        if isinstance(account_value, str):
            return acc_id_short in account_value.replace("-", "")
        if isinstance(account_value, list):
            return any(
                acc_id_short in (str(x) or "").replace("-", "")
                for x in account_value
            )
        return False

    rows = []
    for _, account in acc.iterrows():
        acc_id_short = account["_id_short"]

        if "Account" in h.columns:
            mask = h["Account"].apply(lambda v: _account_match_str(v, acc_id_short))
            sub = h[mask]
        else:
            sub = h.iloc[0:0]

        purchase_cost = sub["Purchase Cost"].fillna(0).sum() if "Purchase Cost" in sub else 0
        market_value = sub["Market Value"].fillna(0).sum() if "Market Value" in sub else 0
        pl = market_value - purchase_cost
        ret = (pl / purchase_cost * 100) if purchase_cost > 0 else 0
        cash = account.get("Cash Balance") or 0
        total_assets = market_value + cash

        rows.append({
            "account_name": account.get("Account Name") or "?",
            "broker": account.get("Broker") or "?",
            "account_type": account.get("Account Type") or "?",
            "monthly_contribution": account.get("Monthly Contribution (원)") or 0,
            "n_holdings": len(sub),
            "sum_purchase_cost": purchase_cost,
            "sum_market_value": market_value,
            "cash_balance": cash,
            "total_assets": total_assets,
            "sum_pl": pl,
            "return_rate": ret,
        })

    return pd.DataFrame(rows)


def compute_total_kpis(account_kpis: pd.DataFrame) -> Dict[str, float]:
    if account_kpis.empty:
        return {
            "total_purchase": 0,
            "total_market_value": 0,
            "total_cash": 0,
            "total_assets": 0,
            "total_pl": 0,
            "weighted_return": 0,
            "monthly_contribution_total": 0,
        }
    total_purchase = account_kpis["sum_purchase_cost"].sum()
    total_market = account_kpis["sum_market_value"].sum()
    total_cash = account_kpis["cash_balance"].sum() if "cash_balance" in account_kpis else 0
    total_pl = total_market - total_purchase
    weighted_ret = (total_pl / total_purchase * 100) if total_purchase > 0 else 0
    monthly = account_kpis["monthly_contribution"].sum()
    return {
        "total_purchase": total_purchase,
        "total_market_value": total_market,
        "total_cash": total_cash,
        "total_assets": total_market + total_cash,
        "total_pl": total_pl,
        "weighted_return": weighted_ret,
        "monthly_contribution_total": monthly,
    }


def compute_distribution_cycle(holdings_df: pd.DataFrame) -> pd.DataFrame:
    """Sum Period Dividend grouped by Pay Cycle."""
    if holdings_df.empty or "Pay Cycle" not in holdings_df.columns:
        return pd.DataFrame(columns=["Pay Cycle", "Period Dividend"])
    out = (
        holdings_df.groupby("Pay Cycle", dropna=False)["Period Dividend"]
        .sum()
        .reset_index()
        .sort_values("Period Dividend", ascending=False)
    )
    return out


def filter_active_holdings(holdings_df: pd.DataFrame) -> pd.DataFrame:
    """Exclude sold/cleared holdings (Buy Tier = 매도완료 etc)."""
    if holdings_df.empty or "Buy Tier" not in holdings_df.columns:
        return holdings_df
    excluded = ["매도완료", "매도완료(예수대기)"]
    return holdings_df[~holdings_df["Buy Tier"].isin(excluded)].copy()


def annualize_period_dividend(row: pd.Series) -> float:
    """1회 분배금 → 연간 분배금 환산."""
    period_div = row.get("Period Dividend") or 0
    freq = row.get("Pay Frequency")
    if freq == "Monthly":
        return period_div * 12
    if freq == "Quarterly":
        return period_div * 4
    if freq == "Annual":
        return period_div * 1
    return 0


def compute_account_yields(
    holdings_df: pd.DataFrame, accounts_df: pd.DataFrame
) -> pd.DataFrame:
    """각 계좌의 현재 implicit dividend yield 계산.

    Returns: DataFrame with columns:
      account_name, account_id, market_value, annual_dividend, dividend_yield
    """
    if accounts_df.empty:
        return pd.DataFrame()

    rows = []
    for _, account in accounts_df.iterrows():
        acc_id_short = str(account["_page_id"]).replace("-", "")

        if "Account" in holdings_df.columns:
            mask = holdings_df["Account"].apply(
                lambda v: v is not None
                and acc_id_short in str(v).replace("-", "")
            )
            sub = holdings_df[mask].copy()
        else:
            sub = holdings_df.iloc[0:0]

        # Exclude sold
        if "Buy Tier" in sub.columns:
            sub = sub[~sub["Buy Tier"].isin(["매도완료", "매도완료(예수대기)"])]

        market_value = sub["Market Value"].fillna(0).sum() if "Market Value" in sub else 0
        annual_div = sub.apply(annualize_period_dividend, axis=1).sum() if not sub.empty else 0
        yield_rate = (annual_div / market_value) if market_value > 0 else 0

        rows.append({
            "account_name": account.get("Account Name") or "?",
            "account_id": account["_page_id"],
            "monthly_contribution": account.get("Monthly Contribution (원)") or 0,
            "market_value": market_value,
            "annual_dividend": annual_div,
            "monthly_dividend": annual_div / 12,
            "dividend_yield": yield_rate * 100,  # in %
        })

    return pd.DataFrame(rows)


# 자산 클래스별 추정 연 NAV 성장률 (시세 손익, 분배금 별도)
# 기준: TDF 28% (실제 관측), 주식형 10% (장기 평균), 커버드콜 -3% (NAV 침식),
#       채권혼합 3%, REITs 5%
DEFAULT_NAV_GROWTH_BY_CLASS: Dict[str, float] = {
    "TDF": 28.0,
    "주식형": 10.0,
    "커버드콜": -3.0,
    "채권혼합": 3.0,
    "REITs": 5.0,
}


def compute_account_nav_growth(
    holdings_df: pd.DataFrame, accounts_df: pd.DataFrame,
    growth_by_class: Dict[str, float] = None,
) -> pd.DataFrame:
    """각 계좌의 가중 평균 NAV 성장률 계산.

    Asset Class 비중 × 클래스별 성장률 가중 평균.

    Returns: DataFrame with columns:
      account_name, account_id, market_value, weighted_nav_growth_pct
    """
    if growth_by_class is None:
        growth_by_class = DEFAULT_NAV_GROWTH_BY_CLASS

    if accounts_df.empty:
        return pd.DataFrame()

    rows = []
    for _, account in accounts_df.iterrows():
        acc_id_short = str(account["_page_id"]).replace("-", "")

        if "Account" in holdings_df.columns:
            mask = holdings_df["Account"].apply(
                lambda v: v is not None and acc_id_short in str(v).replace("-", "")
            )
            sub = holdings_df[mask].copy()
        else:
            sub = holdings_df.iloc[0:0]

        # Exclude sold
        if "Buy Tier" in sub.columns:
            sub = sub[~sub["Buy Tier"].isin(["매도완료", "매도완료(예수대기)"])]

        if sub.empty or "Market Value" not in sub.columns:
            rows.append({
                "account_name": account.get("Account Name") or "?",
                "account_id": account["_page_id"],
                "market_value": 0,
                "weighted_nav_growth_pct": 0,
            })
            continue

        # Asset Class별 비중
        sub_valid = sub[sub["Market Value"].notna() & (sub["Market Value"] > 0)]
        total = sub_valid["Market Value"].sum()
        weighted = 0.0
        for asset_class, group in sub_valid.groupby("Asset Class", dropna=False):
            class_value = group["Market Value"].sum()
            class_growth = growth_by_class.get(asset_class, 5.0)  # 모르면 5% 기본
            weighted += (class_value / total) * class_growth if total else 0

        rows.append({
            "account_name": account.get("Account Name") or "?",
            "account_id": account["_page_id"],
            "market_value": total,
            "weighted_nav_growth_pct": weighted,
        })

    return pd.DataFrame(rows)


def safety_asset_ratio(holdings_df: pd.DataFrame, account_id_short: str) -> float:
    """Calculate the % of safety assets (채권혼합/TDF) in a given account."""
    if holdings_df.empty:
        return 0.0
    h = holdings_df.copy()
    if "Account" not in h.columns:
        return 0.0

    def match(v):
        if v is None:
            return False
        s = str(v).replace("-", "")
        return account_id_short in s

    sub = h[h["Account"].apply(match)]
    if sub.empty or "Market Value" not in sub.columns:
        return 0.0
    total = sub["Market Value"].fillna(0).sum()
    if total == 0:
        return 0.0
    safe_classes = ["채권혼합", "TDF"]
    safe = sub[sub["Asset Class"].isin(safe_classes)]
    safe_total = safe["Market Value"].fillna(0).sum() if not safe.empty else 0
    return safe_total / total * 100
