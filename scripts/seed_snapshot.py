"""Seed Holdings Snapshots from current Holdings DB.

Usage: python scripts/seed_snapshot.py [YYYY-MM]
  - YYYY-MM: target snapshot month (default = current month, e.g. 2026-05)

매월 1회 실행하여 Holdings → Holdings Snapshots 복사.
스냅샷 시점의 Purchase Cost / Market Value / Return Rate 값을 freeze.
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib import notion as nx

SNAPSHOTS_DB_ID = "4a5c9648-52e2-40b5-a390-a7aa9bbe041b"
SNAPSHOTS_DS_ID = "91cf87de-86cc-4cc1-aeb6-6ac96b638d54"


def _txt(value):
    if value is None:
        return ""
    return str(value)


def _num(value):
    if value is None:
        return 0
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0
    # Guard against NaN / Infinity (pandas turns missing numerics into NaN)
    import math
    if math.isnan(f) or math.isinf(f):
        return 0
    return f


def build_snapshot_props(row, snapshot_month: str, snapshot_date_iso: str) -> dict:
    """Build Notion property payload for one snapshot row from a Holdings row."""
    props = {
        "Symbol": {"title": [{"text": {"content": _txt(row.get("Symbol")) or "?"}}]},
        "Snapshot Month": {
            "rich_text": [{"text": {"content": snapshot_month}}]
        },
        "Snapshot Date": {"date": {"start": snapshot_date_iso}},
        "Quantity": {"number": _num(row.get("Quantity"))},
        "Avg Price": {"number": _num(row.get("Avg Price"))},
        "Current Price": {"number": _num(row.get("Current Price"))},
        "Per-Share Dividend": {"number": _num(row.get("Per-Share Dividend"))},
        "Period Dividend": {"number": _num(row.get("Period Dividend"))},
        "Purchase Cost": {"number": _num(row.get("Purchase Cost"))},
        "Market Value": {"number": _num(row.get("Market Value"))},
        "Return Rate": {"number": _num(row.get("Return Rate"))},
    }

    # Optional select fields
    for col, prop in [
        ("Manager", "Manager"),
        ("Pay Frequency", "Pay Frequency"),
        ("Pay Cycle", "Pay Cycle"),
        ("Strategy Tag", "Strategy Tag"),
        ("Asset Class", "Asset Class"),
        ("Buy Tier", "Buy Tier"),
    ]:
        v = row.get(col)
        if v:
            props[prop] = {"select": {"name": str(v)}}

    # Pay month (multi-select)
    pm = row.get("Pay month")
    if isinstance(pm, list) and pm:
        props["Pay month"] = {
            "multi_select": [{"name": str(x)} for x in pm if x]
        }

    # Account relation (list of page IDs)
    acc = row.get("Account")
    if isinstance(acc, list) and acc:
        props["Account"] = {"relation": [{"id": str(x)} for x in acc if x]}

    # Notes
    notes = row.get("Notes")
    if notes:
        props["Notes"] = {"rich_text": [{"text": {"content": str(notes)[:2000]}}]}

    return props


def main():
    month = sys.argv[1] if len(sys.argv) > 1 else date.today().strftime("%Y-%m")
    snap_date = date.today().isoformat()
    print(f"Seeding snapshot: month={month}, date={snap_date}")

    client = nx.get_client()

    # 0) Archive any existing snapshot rows for this month (idempotent re-run)
    print(f"Clearing existing {month} snapshots...")
    cleared = 0
    cursor = None
    while True:
        kwargs = {
            "data_source_id": SNAPSHOTS_DS_ID,
            "page_size": 100,
            "filter": {
                "property": "Snapshot Month",
                "rich_text": {"equals": month},
            },
        }
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = client.data_sources.query(**kwargs)
        for p in resp.get("results", []):
            client.pages.update(page_id=p["id"], archived=True)
            cleared += 1
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    print(f"  Archived {cleared} stale rows.")

    # 1) Pull current Holdings via Streamlit lib (bypassing cache)
    nx.get_holdings_df.clear()
    holdings = nx.get_holdings_df()
    print(f"Holdings to copy: {len(holdings)}")
    if holdings.empty:
        print("No holdings found — aborting.")
        return 1

    created, errors = 0, 0
    for idx, row in holdings.iterrows():
        try:
            props = build_snapshot_props(row, month, snap_date)
            client.pages.create(
                parent={"data_source_id": SNAPSHOTS_DS_ID},
                properties=props,
            )
            created += 1
            print(f"  [{created}/{len(holdings)}] {row.get('Symbol')}")
        except Exception as exc:
            errors += 1
            print(f"  ERROR on {row.get('Symbol')}: {type(exc).__name__}: {exc}")

    print(f"\nDone. created={created}, errors={errors}")
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
