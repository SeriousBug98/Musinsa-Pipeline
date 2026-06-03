"""ranking_collector 통합 테스트.

선행 조건: brands 테이블에 데이터 존재 (test_brand_list 먼저 실행 권장).
독립 실행:
    python tests/integration/test_ranking.py
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "crawler"))

from sqlalchemy import func, select  # noqa: E402

from collectors._http import build_session  # noqa: E402
from collectors.ranking_collector import (  # noqa: E402
    RANKING_MODULE_TYPE,
    RANKING_URL1,
    RANKING_URL1_PARAMS,
    _fetch_page1,
    _parse_modules,
    collect_rankings,
)
from db.connection import get_session  # noqa: E402
from db.models import BrandRanking  # noqa: E402


def _pass(label: str, msg: str = "") -> bool:
    print(f"[PASS] {label}" + (f" — {msg}" if msg else ""))
    return True


def _fail(label: str, msg: str) -> bool:
    print(f"[FAIL] {label} — {msg}")
    return False


def test_api_call() -> bool:
    try:
        with build_session() as http:
            payload = _fetch_page1(http)
    except Exception as e:
        return _fail(
            "api_call",
            f"{RANKING_URL1} params={RANKING_URL1_PARAMS} 요청 실패: {e!r}",
        )
    if not payload:
        return _fail("api_call", "응답 body 비어있음")
    return _pass("api_call", "200 OK")


def test_response_fields() -> bool:
    try:
        with build_session() as http:
            payload = _fetch_page1(http)
    except Exception as e:
        return _fail("response_fields", f"fetch 실패: {e!r}")

    parsed = _parse_modules(payload)
    if not parsed:
        return _fail(
            "response_fields",
            f"{RANKING_MODULE_TYPE} 모듈 파싱 0건. 응답 구조 변경 의심.",
        )

    sample_id, sample_rank = parsed[0]
    # rank 가 1부터 시작하고 단조 증가/유의미한지 가벼운 검증
    ranks = [r for _, r in parsed]
    if min(ranks) < 1:
        return _fail("response_fields", f"rank<1 존재 (min={min(ranks)})")
    if len(set(ranks)) < len(ranks) * 0.9:
        return _fail(
            "response_fields",
            f"rank 중복이 과다 (unique={len(set(ranks))}/{len(ranks)})",
        )
    return _pass(
        "response_fields",
        f"parsed={len(parsed)}, sample(id={sample_id!r}, rank={sample_rank}), "
        f"rank_range={min(ranks)}~{max(ranks)}",
    )


def test_db_snapshot() -> bool:
    try:
        with get_session() as s:
            before = s.execute(select(func.count(BrandRanking.id))).scalar() or 0
    except Exception as e:
        return _fail("db_snapshot", f"DB 조회 실패: {e!r}")

    started_at = datetime.now()
    try:
        inserted = collect_rankings()
    except Exception:
        traceback.print_exc()
        return _fail("db_snapshot", "collect_rankings() 예외 (스택트레이스 위)")

    with get_session() as s:
        after = s.execute(select(func.count(BrandRanking.id))).scalar() or 0
        recent = s.execute(
            select(func.count(BrandRanking.id)).where(
                BrandRanking.collected_at >= started_at
            )
        ).scalar() or 0

    if inserted == 0:
        return _fail(
            "db_snapshot",
            "insert 0건. brands 에 대상 musinsa_brand_id 가 없거나 응답 파싱 실패. "
            "→ test_brand_list 먼저 실행",
        )
    if recent < inserted:
        return _fail("db_snapshot", f"이번 run 새 행={recent} < 반환={inserted}")
    return _pass(
        "db_snapshot",
        f"inserted={inserted}, brand_rankings {before}→{after}",
    )


def main() -> None:
    print("=== test_ranking ===")
    results = [
        test_api_call(),
        test_response_fields(),
        test_db_snapshot(),
    ]
    passed = sum(results)
    print(f"\n==== summary: {passed}/{len(results)} passed ====")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
