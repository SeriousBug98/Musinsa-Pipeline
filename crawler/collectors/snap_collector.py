"""무신사 스냅 STREET 랭킹 UGC 버즈 수집기.

무신사 스냅 STREET 스타일 랭킹(DAILY)에서 상위 N개 스냅을 수집하고,
각 스냅에 태그된 상품의 브랜드를 집계해 brand_snap_mentions 에 append-only 적재.

brand_id = NULL 인 행: 우리 brands 테이블에 없는 신흥 브랜드 추적 후보.
brand_id 연결된 행: 기존 추적 중인 스트릿 브랜드 → 향후 점수 반영 대상.

API 흐름 (2026-06-25 검증):
  1. rankings/DAILY?filter=STREET → 스냅별 rank, goodsNo[], aggregations
  2. goods?goodsIds=MUSINSA:... → goodsNo → brandName(한글) 배치 변환
  3. brands.name ↔ brandName 매칭 → brand_id 세팅
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

import requests
from sqlalchemy import select

from collectors._http import DEFAULT_TIMEOUT, build_session, polite_sleep
from db.connection import get_session
from db.models import Brand, BrandSnapMention

logger = logging.getLogger(__name__)

RANKINGS_URL = "https://content.musinsa.com/api2/content/snap/v1/rankings/DAILY"
GOODS_URL = "https://content.musinsa.com/api2/content/snap/v1/goods"

RANK_FILTER = "STREET"
GENDER = "ALL"
PAGES = 5
PAGE_SIZE = 20
GOODS_BATCH = 20
PERIOD = "DAILY"


def _fetch_rankings_page(http: requests.Session, page: int) -> list[dict]:
    params = {
        "filter": RANK_FILTER,
        "gender": GENDER,
        "page": page,
        "size": PAGE_SIZE,
    }
    resp = http.get(RANKINGS_URL, params=params, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    payload: Any = resp.json()
    return payload.get("data", {}).get("list", [])


def _fetch_goods_brands(
    http: requests.Session, goods_nos: list[str]
) -> dict[str, str]:
    """goodsNo → brandName(한글) 맵 반환. 배치 단위로 호출."""
    result: dict[str, str] = {}
    for i in range(0, len(goods_nos), GOODS_BATCH):
        chunk = goods_nos[i : i + GOODS_BATCH]
        ids = ",".join(f"MUSINSA:{g}" for g in chunk)
        try:
            resp = http.get(
                GOODS_URL, params={"goodsIds": ids}, timeout=DEFAULT_TIMEOUT
            )
            resp.raise_for_status()
            payload: Any = resp.json()
            items = payload.get("data", {}).get("list", [])
            for item in items:
                gno = str(item.get("goodsNo") or "").strip()
                bname = (item.get("brandName") or "").strip()
                if gno and bname:
                    result[gno] = bname
        except Exception:
            logger.exception("snaps: goods fetch failed chunk_start=%d", i)
        if i + GOODS_BATCH < len(goods_nos):
            polite_sleep()
    return result


def _load_brand_name_map(session) -> dict[str, int]:
    """brands.name(한글) → brands.id 맵."""
    rows = session.execute(
        select(Brand.id, Brand.name).where(Brand.is_active.is_(True))
    ).all()
    return {name.strip(): pk for pk, name in rows}


def collect_snap_mentions() -> int:
    http = build_session()
    try:
        # 1. 랭킹 수집
        snaps: list[dict] = []
        for page in range(1, PAGES + 1):
            try:
                items = _fetch_rankings_page(http, page)
            except Exception:
                logger.exception("snaps: rankings fetch failed page=%d", page)
                break
            snaps.extend(items)
            logger.debug("snaps: page=%d fetched=%d cumulative=%d", page, len(items), len(snaps))
            if page < PAGES:
                polite_sleep()

        if not snaps:
            logger.warning("snaps: no ranking data fetched")
            return 0

        logger.info("snaps: ranked=%d pages_attempted=%d", len(snaps), min(PAGES, len(snaps) // PAGE_SIZE + 1))

        # 2. goodsNo 수집 + goods API로 brandName 변환
        all_goods: list[str] = []
        seen_goods: set[str] = set()
        for snap in snaps:
            for g in snap.get("goods", []):
                gno = str(g.get("goodsNo") or "").strip()
                if gno and gno not in seen_goods:
                    seen_goods.add(gno)
                    all_goods.append(gno)

        goods_brand_map = _fetch_goods_brands(http, all_goods)
        logger.info(
            "snaps: goods_resolved=%d/%d", len(goods_brand_map), len(all_goods)
        )
    finally:
        http.close()

    # 3. 브랜드별 집계
    # brand_name → {mention_count, best_rank, like_sum, view_sum, top_snap_id}
    agg: dict[str, dict] = defaultdict(lambda: {
        "mention_count": 0,
        "best_rank": 9999,
        "like_sum": 0,
        "view_sum": 0,
        "top_snap_id": None,
    })

    for snap in snaps:
        rank = snap.get("ranking", {}).get("rank") or 9999
        snap_id = str(snap.get("id") or "")
        agg_data = snap.get("aggregations") or {}
        likes = int(agg_data.get("likeCount") or 0)
        views = int(agg_data.get("viewCount") or 0)

        # 스냅 내 브랜드 중복 제거
        seen_in_snap: set[str] = set()
        for g in snap.get("goods", []):
            gno = str(g.get("goodsNo") or "").strip()
            bname = goods_brand_map.get(gno)
            if not bname or bname in seen_in_snap:
                continue
            seen_in_snap.add(bname)
            a = agg[bname]
            a["mention_count"] += 1
            a["like_sum"] += likes
            a["view_sum"] += views
            if rank < a["best_rank"]:
                a["best_rank"] = rank
                a["top_snap_id"] = snap_id

    if not agg:
        logger.warning("snaps: no brand aggregations produced")
        return 0

    # 4. brands 테이블 매칭
    with get_session() as session:
        name_to_id = _load_brand_name_map(session)

    matched = 0
    unmatched = 0
    now = datetime.now()
    rows: list[dict] = []

    for bname, a in agg.items():
        brand_id = name_to_id.get(bname)
        if brand_id:
            matched += 1
        else:
            unmatched += 1
        rows.append({
            "brand_id": brand_id,
            "brand_name": bname,
            "mention_count": a["mention_count"],
            "best_rank": a["best_rank"],
            "snap_like_sum": a["like_sum"],
            "snap_view_sum": a["view_sum"],
            "top_snap_id": a["top_snap_id"],
            "period": PERIOD,
            "collected_at": now,
        })

    # 5. bulk insert (append-only)
    with get_session() as session:
        session.bulk_insert_mappings(BrandSnapMention, rows)

    logger.info(
        "snaps: inserted=%d matched=%d unmatched=%d",
        len(rows),
        matched,
        unmatched,
    )
    if unmatched:
        top_unmatched = sorted(
            [r["brand_name"] for r in rows if r["brand_id"] is None],
        )[:10]
        logger.info("snaps: top unmatched brands (추적 후보): %s", top_unmatched)

    return len(rows)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    collect_snap_mentions()
