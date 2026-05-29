"""신상품 품절 현황 수집기.

대상 브랜드는 (랭킹 Top 100 최근 1일) ∪ (신규 입점 30일 이내) ∪ (is_tracked).
대상 브랜드 × 6개 카테고리 조합으로 PLP 신상품(page=1)을 호출해 new_products 에 upsert.
총 호출 수 = len(targets) × len(CATEGORIES).

PLP brand 필터 (2026-05 기준):
- `brand=<musinsa_brand_id>` 파라미터로 그 브랜드 상품만 반환됨 (caller=CATEGORY 유지)
- `brandIds` 키는 무시됨, `caller=BRAND` 로 바꾸면 응답 구조 변경됨

품절 전이 로직:
- 신규: 응답이 sold_out 이면 sold_out_at = now() 로 기록
- 기존 행: false → true 전이 시점에만 sold_out_at = now() 로 채움
- 기존 행: true → false 로 돌아오면 sold_out_at = NULL 로 클리어
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import requests
from sqlalchemy import and_, case, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from collectors._http import DEFAULT_TIMEOUT, build_session, polite_sleep
from db.connection import get_session
from db.models import Brand, BrandRanking, NewProduct

logger = logging.getLogger(__name__)

PRODUCT_URL = "https://api.musinsa.com/api2/dp/v2/plp/goods"

CATEGORIES: dict[str, str] = {
    "001": "상의",
    "002": "아우터",
    "003": "바지",
    "004": "가방",
    "101": "소품",
    "103": "신발",
}

# PLP 필수 baseline 파라미터.
# storeCode, caller 가 없으면 DISPLAY_000_0001 (잘못된 파라미터) 로 400.
# isSoldOut=true 가 빠지면 응답에서 품절 상품이 제외됨 — 품절 현황 수집 목적상 필수.
PRODUCT_BASE_PARAMS: dict[str, str | int] = {
    "gf": "A",
    "storeCode": "musinsa",
    "caller": "CATEGORY",
    "sort": "NEW_PRODUCT",
    "size": 30,
    "isSoldOut": "true",
}

TOP_RANK_LIMIT = 100
NEW_JOIN_DAYS = 30
PAGE = 1  # CLAUDE.md: page=2 이상은 hmacId 필요. 1 고정.


def _select_target_brands(session) -> dict[str, int]:
    """수집 대상 musinsa_brand_id → brand.id 매핑."""
    now = datetime.now()
    cutoff_rank = now - timedelta(days=1)
    cutoff_join = now - timedelta(days=NEW_JOIN_DAYS)

    recent_top_brand_ids = select(BrandRanking.brand_id).where(
        BrandRanking.collected_at >= cutoff_rank,
        BrandRanking.rank <= TOP_RANK_LIMIT,
    )

    rows = session.execute(
        select(Brand.id, Brand.musinsa_brand_id).where(
            Brand.is_active.is_(True),
            (
                Brand.id.in_(recent_top_brand_ids)
                | (Brand.joined_at >= cutoff_join)
                | (Brand.is_tracked.is_(True))
            ),
        )
    ).all()

    return {mb_id: pk for pk, mb_id in rows}


def _fetch_brand_category(
    http: requests.Session, brand_id: str, category_code: str
) -> list[dict]:
    params = {
        **PRODUCT_BASE_PARAMS,
        "category": category_code,
        "page": PAGE,
        "brand": brand_id,
    }
    resp = http.get(PRODUCT_URL, params=params, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    payload: Any = resp.json()

    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(data, dict):
        for key in ("list", "goodsList", "items", "goods", "contents"):
            v = data.get(key)
            if isinstance(v, list):
                return v
        inner = data.get("data")
        if isinstance(inner, dict):
            for key in ("list", "goodsList", "items", "goods", "contents"):
                v = inner.get(key)
                if isinstance(v, list):
                    return v
    elif isinstance(data, list):
        return data
    return []


def _pick(d: dict, *keys: str):
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return None


def _to_int(v) -> int | None:
    if v in (None, ""):
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _normalize(entry: dict, category_code: str) -> dict | None:
    """brand 식별은 호출부에서 결정 (brand=mb_id 로 요청) 하므로 여기선 미관여."""
    pid = _pick(entry, "goodsNo", "productId", "id", "goodsId")
    pname = _pick(entry, "goodsName", "productName", "name")
    if not pid or not pname:
        return None

    price = _to_int(_pick(entry, "normalPrice", "price"))
    final_price = _to_int(_pick(entry, "salePrice", "finalPrice", "price"))

    is_sold_out = bool(
        entry.get("isSoldOut")
        or entry.get("soldOut")
        or entry.get("isOutOfStock")
        or entry.get("saleStatus") == "SOLD_OUT"
    )

    return {
        "product_id": str(pid),
        "product_name": str(pname).strip()[:300],
        "category_code": category_code,
        "price": price,
        "final_price": final_price,
        "is_sold_out": is_sold_out,
    }


def collect_new_products() -> int:
    with get_session() as session:
        targets = _select_target_brands(session)

    if not targets:
        logger.warning("products: no target brands selected")
        return 0

    cats = list(CATEGORIES.items())
    brand_items = list(targets.items())
    total_requests = len(brand_items) * len(cats)
    logger.info(
        "products: target_brands=%d categories=%d total_requests=%d",
        len(brand_items),
        len(cats),
        total_requests,
    )

    now = datetime.now()
    rows: list[dict] = []
    failures = 0
    http = build_session()

    try:
        for b_idx, (mb_id, pk) in enumerate(brand_items, start=1):
            brand_matched = 0
            for cat_code, _ in cats:
                try:
                    entries = _fetch_brand_category(http, mb_id, cat_code)
                except Exception:
                    failures += 1
                    logger.exception(
                        "products: fetch failed brand=%s category=%s",
                        mb_id,
                        cat_code,
                    )
                    continue

                for entry in entries:
                    norm = _normalize(entry, cat_code)
                    if norm is None:
                        continue
                    rows.append(
                        {
                            "brand_id": pk,
                            "first_seen_at": now,
                            "sold_out_at": now if norm["is_sold_out"] else None,
                            **norm,
                        }
                    )
                    brand_matched += 1

            if b_idx % 10 == 0 or b_idx == len(brand_items):
                logger.info(
                    "products: progress %d/%d brands rows=%d failures=%d",
                    b_idx,
                    len(brand_items),
                    len(rows),
                    failures,
                )

            if b_idx < len(brand_items):
                polite_sleep()
    finally:
        http.close()

    if not rows:
        logger.info("products: nothing to upsert (failures=%d)", failures)
        return 0

    # (product_id, category_code) 기준 중복 제거 — 같은 배치 내 충돌 방지
    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for r in rows:
        key = (r["product_id"], r["category_code"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    stmt = pg_insert(NewProduct).values(deduped)
    stmt = stmt.on_conflict_do_update(
        index_elements=["product_id", "category_code"],
        set_={
            "product_name": stmt.excluded.product_name,
            "price": stmt.excluded.price,
            "final_price": stmt.excluded.final_price,
            "is_sold_out": stmt.excluded.is_sold_out,
            "sold_out_at": case(
                (
                    and_(
                        stmt.excluded.is_sold_out,
                        NewProduct.sold_out_at.is_(None),
                    ),
                    func.now(),
                ),
                (stmt.excluded.is_sold_out.is_(False), None),
                else_=NewProduct.sold_out_at,
            ),
            # brand_id, first_seen_at 은 보존
        },
    )

    with get_session() as session:
        session.execute(stmt)

    logger.info(
        "products: upserted=%d dedup_dropped=%d failures=%d",
        len(deduped),
        len(rows) - len(deduped),
        failures,
    )
    return len(deduped)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    collect_new_products()
