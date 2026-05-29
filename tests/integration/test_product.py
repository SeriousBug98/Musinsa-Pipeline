"""product_collector 통합 테스트.

선행 조건: brands 데이터 + (선택) rankings 또는 tracked_brands.yaml.
독립 실행:
    python tests/integration/test_product.py

검증:
- 카테고리 6종 GET 모두 도달
- 대상 브랜드 집합 비어있지 않음 (랭킹 Top100 ∪ 신규 30일 ∪ is_tracked)
- new_products 에 적재
- 이번 run 에 추가된 행이 모두 대상 브랜드 소속
"""

from __future__ import annotations

import sys
import time as time_mod
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "crawler"))

from sqlalchemy import func, select  # noqa: E402

from collectors._http import build_session  # noqa: E402
from collectors.product_collector import (  # noqa: E402
    CATEGORIES,
    NEW_JOIN_DAYS,
    PRODUCT_URL,
    TOP_RANK_LIMIT,
    _fetch_category,
    _select_target_brands,
    collect_new_products,
)
from db.connection import get_session  # noqa: E402
from db.models import NewProduct  # noqa: E402


def _pass(label: str, msg: str = "") -> bool:
    print(f"[PASS] {label}" + (f" — {msg}" if msg else ""))
    return True


def _fail(label: str, msg: str) -> bool:
    print(f"[FAIL] {label} — {msg}")
    return False


# 모듈 로드 시점을 기준으로 "이번 테스트 run 의 신규 insert" 를 식별
RUN_STARTED_AT = datetime.now()


def test_categories_all_reachable() -> bool:
    http = build_session()
    sizes: dict[str, int] = {}
    failed: list[tuple[str, str]] = []
    try:
        for i, (code, name) in enumerate(CATEGORIES.items()):
            try:
                entries = _fetch_category(http, code)
                sizes[code] = len(entries)
                if not entries:
                    failed.append((f"{code}({name})", "0 entries"))
            except Exception as e:
                failed.append((f"{code}({name})", repr(e)))
            if i < len(CATEGORIES) - 1:
                time_mod.sleep(1.5)  # polite
    finally:
        http.close()

    summary = ", ".join(f"{c}({CATEGORIES[c]}):{n}" for c, n in sizes.items())
    if failed:
        return _fail(
            "categories_all_reachable",
            f"실패: {failed}. URL={PRODUCT_URL}. 통과한 카테고리: {summary}",
        )
    return _pass("categories_all_reachable", summary)


def test_target_set_nonempty() -> bool:
    try:
        with get_session() as s:
            targets = _select_target_brands(s)
    except Exception as e:
        return _fail("target_set_nonempty", f"_select_target_brands 실패: {e!r}")

    if not targets:
        return _fail(
            "target_set_nonempty",
            f"대상 브랜드 0개. 선행 조건 부족: "
            f"(랭킹 1일 내 top {TOP_RANK_LIMIT}) ∪ (입점 {NEW_JOIN_DAYS}일 내) ∪ (is_tracked). "
            f"→ test_brand_list + test_ranking 먼저, 또는 tracked_brands.yaml 채우기.",
        )
    return _pass("target_set_nonempty", f"{len(targets)} target brands")


def test_db_persistence() -> bool:
    try:
        with get_session() as s:
            before = s.execute(select(func.count(NewProduct.id))).scalar() or 0
    except Exception as e:
        return _fail("db_persistence", f"DB 조회 실패: {e!r}")

    try:
        upserted = collect_new_products()
    except Exception:
        traceback.print_exc()
        return _fail("db_persistence", "collect_new_products() 예외 (스택트레이스 위)")

    with get_session() as s:
        after = s.execute(select(func.count(NewProduct.id))).scalar() or 0
        recent = s.execute(
            select(func.count(NewProduct.id)).where(
                NewProduct.first_seen_at >= RUN_STARTED_AT
            )
        ).scalar() or 0

    if upserted == 0:
        return _fail(
            "db_persistence",
            "upsert 0건. 대상 브랜드의 신상품이 응답에 없거나 응답 파싱 실패.",
        )
    return _pass(
        "db_persistence",
        f"upserted={upserted}, new_products {before}→{after}, this_run_inserts={recent}",
    )


def test_only_target_brands() -> bool:
    """이번 run 에 새로 insert 된 행이 모두 현재 대상 브랜드 소속인지 검증.

    on_conflict 로 갱신만 된 행은 first_seen_at 이 보존되므로 자연스럽게 제외된다.
    """
    try:
        with get_session() as s:
            targets = _select_target_brands(s)
            target_pks = set(targets.values())
            rows = s.execute(
                select(NewProduct.id, NewProduct.brand_id, NewProduct.product_name)
                .where(NewProduct.first_seen_at >= RUN_STARTED_AT)
            ).all()
    except Exception as e:
        return _fail("only_target_brands", f"DB 조회 실패: {e!r}")

    if not rows:
        return _fail(
            "only_target_brands",
            "이번 run 신규 insert 0건. db_persistence 통과 후 다시 실행.",
        )

    violations = [(rid, bid, pname) for rid, bid, pname in rows if bid not in target_pks]
    if violations:
        sample = violations[:5]
        return _fail(
            "only_target_brands",
            f"대상 외 brand_id 의 상품 {len(violations)}건 신규 insert. sample={sample}. "
            f"collector 의 대상 필터 버그 의심.",
        )
    return _pass("only_target_brands", f"신규 {len(rows)}행 모두 대상 브랜드")


def main() -> None:
    print(f"=== test_product (categories={list(CATEGORIES.keys())}) ===")
    results = [
        test_categories_all_reachable(),
        test_target_set_nonempty(),
        test_db_persistence(),
        test_only_target_brands(),
    ]
    passed = sum(results)
    print(f"\n==== summary: {passed}/{len(results)} passed ====")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
