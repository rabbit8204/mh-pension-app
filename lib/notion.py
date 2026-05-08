"""Notion API client wrapper.

Wraps notion-client SDK to fetch the three Pension databases
(Accounts / Holdings / Cashflow Monthly) as pandas DataFrames.

Requires NOTION_TOKEN environment variable (in .env).
"""

import os
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()


def _read_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """로컬(.env) 또는 Streamlit Cloud(st.secrets) 양쪽에서 환경 변수 읽기.

    1) os.getenv (로컬 .env 또는 시스템 환경변수)
    2) st.secrets (Streamlit Cloud 대시보드의 Secrets 설정)
    """
    val = os.getenv(key)
    if val:
        return val
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return default


NOTION_TOKEN = _read_secret("NOTION_TOKEN")

# Database IDs (URL 기반 — 사람이 보기 쉬운 ID)
ACCOUNTS_DB_ID = _read_secret(
    "NOTION_ACCOUNTS_DB", "a0e1d6ea-a31a-4576-8fa2-a9eead17d0af"
)
HOLDINGS_DB_ID = _read_secret(
    "NOTION_HOLDINGS_DB", "fb793b41-72e3-49f7-9184-c1ac3598235f"
)
CASHFLOW_DB_ID = _read_secret(
    "NOTION_CASHFLOW_DB", "3e03524a-32cb-4c6b-911a-9a943fb88f0b"
)

# Data Source IDs (Notion 2025-09 API에서 query에 사용)
# 노션이 한 데이터베이스 안에 여러 data source(=collection)를 둘 수 있게 변경.
# 우리 DB는 모두 single data source라 첫 번째를 사용.
ACCOUNTS_DS_ID_FALLBACK = "642b8023-192e-4eac-a58f-38eae0f240ef"
HOLDINGS_DS_ID_FALLBACK = "ea2a5bde-8e94-4296-875f-d4ef9baaef45"
CASHFLOW_DS_ID_FALLBACK = "74c74680-17cc-41a6-beba-19f552b366e3"


def get_client() -> Client:
    if not NOTION_TOKEN or NOTION_TOKEN.startswith("ntn_여기에"):
        raise ValueError(
            "NOTION_TOKEN이 .env 파일에 설정되지 않았습니다. "
            ".env.example을 참고하여 .env 파일을 만드세요."
        )
    return Client(auth=NOTION_TOKEN)


# data_source_id 캐싱 (DB ID → data source ID)
_DS_ID_CACHE: Dict[str, str] = {}


def _resolve_data_source_id(database_id: str, fallback: Optional[str] = None) -> str:
    """Database ID로부터 첫 번째 data source ID를 찾아 반환.

    1) 캐시 확인
    2) databases.retrieve 호출해 data_sources[0].id 추출
    3) 실패 시 fallback 사용
    """
    if database_id in _DS_ID_CACHE:
        return _DS_ID_CACHE[database_id]

    try:
        client = get_client()
        db = client.databases.retrieve(database_id=database_id)
        sources = db.get("data_sources") or []
        if sources:
            ds_id = sources[0]["id"]
            _DS_ID_CACHE[database_id] = ds_id
            return ds_id
    except Exception:
        pass

    if fallback:
        _DS_ID_CACHE[database_id] = fallback
        return fallback
    raise ValueError(f"data_source_id를 찾을 수 없습니다: database_id={database_id}")


def _query_db(database_id: str, fallback_ds_id: Optional[str] = None,
              page_size: int = 100) -> List[Dict[str, Any]]:
    """Notion 2025-09 API 기준으로 data source를 query."""
    client = get_client()
    ds_id = _resolve_data_source_id(database_id, fallback_ds_id)

    results: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    while True:
        kwargs: Dict[str, Any] = {"data_source_id": ds_id, "page_size": page_size}
        if cursor:
            kwargs["start_cursor"] = cursor
        response = client.data_sources.query(**kwargs)
        results.extend(response["results"])
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    return results


def _extract_property(prop: Dict[str, Any]) -> Any:
    """Extract a flat Python value from a Notion property object."""
    if not prop:
        return None
    ptype = prop.get("type")
    if ptype == "title":
        items = prop.get("title", [])
        return "".join(item.get("plain_text", "") for item in items)
    if ptype == "rich_text":
        items = prop.get("rich_text", [])
        return "".join(item.get("plain_text", "") for item in items)
    if ptype == "number":
        return prop.get("number")
    if ptype == "select":
        sel = prop.get("select")
        return sel["name"] if sel else None
    if ptype == "multi_select":
        return [s["name"] for s in prop.get("multi_select", [])]
    if ptype == "date":
        d = prop.get("date")
        return d["start"] if d else None
    if ptype == "relation":
        return [r["id"] for r in prop.get("relation", [])]
    if ptype == "checkbox":
        return prop.get("checkbox")
    if ptype == "url":
        return prop.get("url")
    if ptype == "email":
        return prop.get("email")
    if ptype == "files":
        return [f.get("name") for f in prop.get("files", [])]
    return None


def _parse_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for page in pages:
        row: Dict[str, Any] = {
            "_page_id": page["id"],
            "_url": page.get("url"),
        }
        for name, prop in page.get("properties", {}).items():
            row[name] = _extract_property(prop)
        rows.append(row)
    return rows


@st.cache_data(ttl=300)
def get_accounts_df() -> pd.DataFrame:
    """Fetch Accounts DB (6 계좌)."""
    rows = _parse_pages(_query_db(ACCOUNTS_DB_ID, ACCOUNTS_DS_ID_FALLBACK))
    df = pd.DataFrame(rows)
    return df


@st.cache_data(ttl=300)
def get_holdings_df() -> pd.DataFrame:
    """Fetch Holdings DB (~70 종목)."""
    rows = _parse_pages(_query_db(HOLDINGS_DB_ID, HOLDINGS_DS_ID_FALLBACK))
    df = pd.DataFrame(rows)
    return df


@st.cache_data(ttl=300)
def get_cashflow_df() -> pd.DataFrame:
    """Fetch Cashflow Monthly DB (12 months projection)."""
    rows = _parse_pages(_query_db(CASHFLOW_DB_ID, CASHFLOW_DS_ID_FALLBACK))
    df = pd.DataFrame(rows)
    return df


def clear_cache() -> None:
    """Force re-fetch on next call."""
    get_accounts_df.clear()
    get_holdings_df.clear()
    get_cashflow_df.clear()
