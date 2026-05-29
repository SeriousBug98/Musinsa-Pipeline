"""brand_list_collector 통합 테스트.

실제 brand-list.json + 실제 PostgreSQL 사용. 독립 실행:
    python tests/integration/test_brand_list.py

선행 조건: .env 설정 + db/init.sql 적용.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "crawler"))

from sqlalchemy import func, select  # noqa: E402

from collectors.brand_list_collector import (  # noqa: E402
    BRAND_LIST_URL,
    _fetch_brand_list,
    _iter_brand_entries,
    _normalize,
    collect_brand_list,
)
from db.connection import get_session  # noqa: E402
from db.models import Brand  # noqa: E402


# 응답에 존재할 것으로 기대하는 알려진 스트릿캐주얼 브랜드 슬러그
KNOWN_STREET_BRANDS = [
    "thisisneverthat",
    "covernat",
    "mahagrid",
    "yeseyesee",
]


def _pass(label: str, msg: str = "") -> bool:
    print(f"[PASS] {label}" + (f" — {msg}" if msg else ""))
    return True


def _fail(label: str, msg: str) -> bool:
    print(f"[FAIL] {label} — {msg}")
    return False


def test_api_call() -> bool:
    try:
        payload = _fetch_brand_list()
    except Exception as e:
        return _fail("api_call", f"{BRAND_LIST_URL} 요청 실패: {e!r}")

    entries = list(_iter_brand_entries(payload))
    if not entries:
        return _fail(
            "api_call",
            "응답은 받았으나 brand entry 0건. _iter_brand_entries 그룹 구조 검토 필요.",
        )
    return _pass("api_call", f"{len(entries)} entries 수신")


def test_street_brands_present() -> bool:
    try:
        payload = _fetch_brand_list()
    except Exception as e:
        return _fail("street_brands_present", f"fetch 실패: {e!r}")

    ids = set()
    for entry in _iter_brand_entries(payload):
        norm = _normalize(entry)
        if norm:
            ids.add(norm["musinsa_brand_id"])

    found = [b for b in KNOWN_STREET_BRANDS if b in ids]
    missing = [b for b in KNOWN_STREET_BRANDS if b not in ids]

    if not found:
        sample_ids = list(ids)[:5]
        return _fail(
            "street_brands_present",
            f"알려진 스트릿 브랜드 {KNOWN_STREET_BRANDS} 중 0건. "
            f"실제 brand_id 키 형식이 다를 수 있음. 파싱된 id 샘플={sample_ids}",
        )
    if missing:
        print(f"[WARN] street_brands_present — missing={missing}")
    return _pass(
        "street_brands_present",
        f"found {len(found)}/{len(KNOWN_STREET_BRANDS)}: {found}",
    )


def test_db_persistence() -> bool:
    try:
        with get_session() as s:
            before = s.execute(select(func.count(Brand.id))).scalar() or 0
    except Exception as e:
        return _fail("db_persistence", f"DB 연결 실패 (.env / init.sql 확인): {e!r}")

    try:
        upserted = collect_brand_list()
    except Exception:
        traceback.print_exc()
        return _fail("db_persistence", "collect_brand_list() 예외 (스택트레이스 위)")

    with get_session() as s:
        after = s.execute(select(func.count(Brand.id))).scalar() or 0
        any_street = s.execute(
            select(Brand.musinsa_brand_id).where(
                Brand.musinsa_brand_id.in_(KNOWN_STREET_BRANDS)
            )
        ).scalars().all()

    if upserted == 0:
        return _fail("db_persistence", "collector 반환 0건")
    if after < before:
        return _fail("db_persistence", f"brand 수 감소: {before} → {after}")
    if not any_street:
        return _fail(
            "db_persistence",
            "DB upsert 됐지만 알려진 스트릿 브랜드가 brands 에 없음. id 매핑 의심.",
        )
    return _pass(
        "db_persistence",
        f"upserted={upserted}, brands {before}→{after}, street_in_db={any_street}",
    )


def main() -> None:
    print(f"=== test_brand_list (target: {BRAND_LIST_URL}) ===")
    results = [
        test_api_call(),
        test_street_brands_present(),
        test_db_persistence(),
    ]
    passed = sum(results)
    print(f"\n==== summary: {passed}/{len(results)} passed ====")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
