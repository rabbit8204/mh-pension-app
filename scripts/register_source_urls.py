"""Auto-register source_url frontmatter in Strategy_Notes/Symbols/*.md.

각 종목 노트의 운용사 공식 페이지 URL을 자동 추정하여 frontmatter에 추가.
옵션 γ (운용사 공시 자동 학습) 워크플로우의 Phase 2.

추정 로직:
  1. 종목명에서 운용사 prefix 추출 (KODEX/TIGER/RISE/SOL/PLUS/KIWOOM/ACE/삼성/KB)
  2. 운용사별 검색 URL 패턴 적용
  3. WebSearch로 정확한 종목 페이지 검색 (선택적)
  4. frontmatter에 source_url 필드 추가
"""

import os
import re
import sys
from pathlib import Path

SYMBOLS_DIR = Path(
    "/Users/manhyunglee/Desktop/01_MH_Finance/00_MH_Finance/Strategy_Notes/Symbols"
)

# 운용사별 ETF 검색 URL 베이스
ASSET_MANAGER_SEARCH = {
    "KODEX": "https://www.samsungfund.com/etf/product/list.do?keyword=",
    "TIGER": "https://www.tigeretf.com/ko/product/search/list.do?keyword=",
    "RISE": "https://riseetf.co.kr/prod/finderList?keyword=",
    "SOL": "https://www.soletf.com/ko/fund/etf/search?q=",
    "PLUS": "https://www.plusetf.co.kr/product/list?keyword=",
    "KIWOOM": "https://www.kiwoom.com/h/etf",
    "ACE": "https://www.aceetf.co.kr/fund?keyword=",
    "HANARO": "https://www.hanaroetf.com/product?keyword=",
}

# 펀드 (TDF 등) 운용사
FUND_MANAGER_SEARCH = {
    "KB": "https://www.kbam.co.kr",
    "삼성": "https://www.samsungfund.com",
}


def detect_manager(symbol: str) -> "str | None":
    """종목명에서 운용사 식별."""
    for manager in list(ASSET_MANAGER_SEARCH.keys()) + list(FUND_MANAGER_SEARCH.keys()):
        if symbol.startswith(manager):
            return manager
    return None


def estimate_search_url(symbol: str):
    """종목명 → (manager, search_url_base) 추정."""
    manager = detect_manager(symbol)
    if not manager:
        return None, None
    if manager in ASSET_MANAGER_SEARCH:
        return manager, ASSET_MANAGER_SEARCH[manager]
    return manager, FUND_MANAGER_SEARCH.get(manager)


def update_frontmatter(file_path: Path) -> dict:
    """노트 파일의 frontmatter에 source_url + source_manager 추가."""
    content = file_path.read_text(encoding="utf-8")

    # Extract frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if not fm_match:
        return {"file": file_path.name, "status": "no_frontmatter"}

    fm_text = fm_match.group(1)
    body = fm_match.group(2)

    # Already has source_url?
    if re.search(r"^source_url:", fm_text, re.MULTILINE):
        return {"file": file_path.name, "status": "already_has_url"}

    # Extract symbol from frontmatter
    symbol_match = re.search(r'^symbol:\s*"?([^"\n]+)"?', fm_text, re.MULTILINE)
    if not symbol_match:
        return {"file": file_path.name, "status": "no_symbol"}

    symbol = symbol_match.group(1).strip()
    manager, search_url = estimate_search_url(symbol)

    if not manager:
        return {"file": file_path.name, "symbol": symbol, "status": "unknown_manager"}

    # Add source_manager + placeholder source_url (search URL for now)
    # User can replace with exact product URL after first manual fetch
    new_fm_lines = fm_text.split("\n")
    # Insert after `notion_id` line for grouping
    for i, line in enumerate(new_fm_lines):
        if line.startswith("notion_id:"):
            new_fm_lines.insert(i + 1, f"source_manager: {manager}")
            new_fm_lines.insert(
                i + 2,
                f'source_url: ""  # TODO: replace with exact ETF page URL ({search_url})',
            )
            break

    new_fm_text = "\n".join(new_fm_lines)
    new_content = f"---\n{new_fm_text}\n---\n{body}"

    file_path.write_text(new_content, encoding="utf-8")
    return {
        "file": file_path.name,
        "symbol": symbol,
        "manager": manager,
        "status": "updated",
    }


def main():
    if not SYMBOLS_DIR.exists():
        print(f"❌ Symbols dir not found: {SYMBOLS_DIR}")
        return 1

    md_files = sorted(SYMBOLS_DIR.glob("*.md"))
    print(f"Processing {len(md_files)} symbol notes...\n")

    stats = {"updated": 0, "already_has_url": 0, "unknown_manager": 0, "no_symbol": 0, "no_frontmatter": 0}
    unknown_symbols = []

    for fp in md_files:
        result = update_frontmatter(fp)
        status = result["status"]
        stats[status] = stats.get(status, 0) + 1
        if status == "unknown_manager":
            unknown_symbols.append(result.get("symbol", "?"))
        elif status == "updated":
            print(f"  ✓ {result['manager']:8s} | {fp.name}")

    print(f"\n=== 결과 ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    if unknown_symbols:
        print(f"\n⚠️ 운용사 식별 실패 ({len(unknown_symbols)}개) — 수동 등록 필요:")
        for s in unknown_symbols:
            print(f"  - {s}")

    print(f"\n📝 다음 단계:")
    print(f"  1. 각 노트의 source_url 필드를 실제 ETF 페이지 URL로 교체")
    print(f"  2. (선택) WebSearch / WebFetch로 자동 URL 발견 스크립트 추가")
    print(f"  3. 매월 캡처 사이클에서 source_url 기반 운용사 공시 자동 학습")

    return 0


if __name__ == "__main__":
    sys.exit(main())
