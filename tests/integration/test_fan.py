"""fan_collector 통합 테스트.

선행 조건: brands 테이블에 활성 브랜드 존재.
독립 실행:
    python tests/integration/test_fan.py

주의: "1일 1회 보장" 테스트는 현재 collector 가 dedup 로직을 갖고 있지 않아
실패할 수 있다. 실패하면 collector 측에 진입 가드(오늘 행 존재 시 skip) 또는
(brand_id, DATE(collected_at)) UNIQUE 제약 도입을 검토.
"""

from __future__ import annotations

import sys
import traceback
from datetime import date, datetime, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "crawler"))

from sqlalchemy import func, select  # noqa: E402

from collectors._http import build_session  # noqa: E402
from collectors.fan_collector import (  # noqa: E402
    FAN_URL,
    _fetch_counts,
    collect_fans,
)
from db.connection import get_session  # noqa: E402
from db.models import Brand, BrandFan  # noqa: E402


def _pass(label: str, msg: str = "") -> bool:
    print(f"[PASS] {label}" + (f" — {msg}" if msg else ""))
    return True


def _fail(label: str, msg: str) -> bool:
    print(f"[FAIL] {label} — {msg}")
    return False


def _today_bounds() -> tuple[datetime, datetime]:
    today = date.today()
    return datetime.combine(today, time.min), datetime.combine(today, time.max)


def _count_today() -> int:
    start, end = _today_bounds()
    with get_session() as s:
        return s.execute(
            select(func.count(BrandFan.id)).where(
                BrandFan.collected_at >= start,
                BrandFan.collected_at <= end,
            )
        ).scalar() or 0


def test_api_call() -> bool:
    try:
        with get_session() as s:
            sample = list(
                s.execute(
                    select(Brand.musinsa_brand_id)
                    .where(Brand.is_active.is_(True))
                    .limit(3)
                ).scalars().all()
            )
    except Exception as e:
        return _fail("api_call", f"DB 조회 실패: {e!r}")

    if not sample:
        return _fail(
            "api_call",
            "활성 브랜드 0개. → test_brand_list 먼저 실행",
        )

    http = build_session()
    try:
        try:
            counts = _fetch_counts(http, sample)
        except Exception as e:
            return _fail("api_call", f"{FAN_URL} POST 실패: {e!r}")
    finally:
        http.close()

    if not counts:
        return _fail(
            "api_call",
            f"POST 200 이지만 fan count 파싱 0건. 응답 구조(relationId/count 등) 검토 필요. "
            f"보낸 brand_ids={sample}",
        )
    return _pass("api_call", f"{len(counts)}/{len(sample)} brands 의 count 파싱")


def test_today_persistence() -> bool:
    try:
        before = _count_today()
    except Exception as e:
        return _fail("today_persistence", f"DB 조회 실패: {e!r}")

    try:
        inserted = collect_fans()
    except Exception:
        traceback.print_exc()
        return _fail("today_persistence", "collect_fans() 예외 (스택트레이스 위)")

    after = _count_today()
    if after <= before:
        return _fail(
            "today_persistence",
            f"오늘 행수 증가 없음: before={before}, after={after}, 반환={inserted}",
        )
    return _pass(
        "today_persistence",
        f"오늘 brand_fans rows {before}→{after} (+{after - before}), collector 반환={inserted}",
    )


def test_no_duplicate_per_day() -> bool:
    first = _count_today()
    if first == 0:
        return _fail(
            "no_duplicate_per_day",
            "오늘 행이 0개. 선행 today_persistence 가 통과해야 함.",
        )

    try:
        collect_fans()
    except Exception as e:
        return _fail("no_duplicate_per_day", f"재실행 실패: {e!r}")

    second = _count_today()
    if second > first:
        return _fail(
            "no_duplicate_per_day",
            f"같은 날 재실행 시 행수 증가함: {first} → {second}. "
            f"1일 1회 보장이 collector 측에 미구현. "
            f"권장 (택1): "
            f"(a) collect_fans() 진입 시 오늘 행 존재하면 즉시 return, "
            f"(b) brand_fans 에 (brand_id, DATE(collected_at)) UNIQUE 제약 추가 후 ON CONFLICT DO NOTHING.",
        )
    return _pass("no_duplicate_per_day", f"행수 유지: {first} == {second}")


def main() -> None:
    print("=== test_fan ===")
    results = [
        test_api_call(),
        test_today_persistence(),
        test_no_duplicate_per_day(),
    ]
    passed = sum(results)
    print(f"\n==== summary: {passed}/{len(results)} passed ====")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
