"""브랜드 랭킹 수집기.

1~200위: RANKING_URL1 (단일 호출)
201위~:  RANKING_URL2 (page/startRank/offset 으로 페이지네이션)
  - offset = startRank - 1 (0-indexed 누적 위치)
  - page=2/startRank=201/offset=200 → 201~400위
  - page=3/startRank=401/offset=400 → 401~600위  ...

두 엔드포인트 응답 구조 동일 (2026-06 기준):
    { "data": { "modules": [
        { "type": "RANKING_BRAND",
          "title": {
            "rank": "1",
            "title": { "text": "오니츠카타이거" },
            "onClick": { "url": "https://www.musinsa.com/brand/onitsukatiger" },
          },
          "items": [...]
        }, ...
    ] } }

musinsa_brand_id 는 title.onClick.url 의 마지막 path segment (브랜드 슬러그) 로 추출.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select

from collectors._http import DEFAULT_TIMEOUT, build_session, polite_sleep
from db.connection import get_session
from db.models import Brand, BrandRanking

logger = logging.getLogger(__name__)

RANKING_URL1 = "https://client.musinsa.com/api/home/web/v5/pans/ranking"
RANKING_URL1_PARAMS = {
    "storeCode": "musinsa",
    "sectionId": "1066",
    "gf": "A",
    "categoryCode": "",
    "ageBand": "AGE_BAND_ALL",
    "subPan": "brand",
}

RANKING_URL2 = "https://client.musinsa.com/api/home/web/v5/pans/ranking/sections/1066"
RANKING_URL2_BASE_PARAMS = {
    "storeCode": "musinsa",
    "gf": "A",
    "ageBand": "AGE_BAND_ALL",
    "period": "REALTIME",
    "eventPeriod": "BASIC_REALTIME",
    "categoryCode": "",
    "contentsId": "",
    "variantValue": "",
}

RANKING_MODULE_TYPE = "RANKING_BRAND"
PAGE_SIZE = 200


def _fetch_page1(http) -> Any:
    resp = http.get(RANKING_URL1, params=RANKING_URL1_PARAMS, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _fetch_page_n(http, page: int, start_rank: int) -> Any:
    params = {
        **RANKING_URL2_BASE_PARAMS,
        "page": page,
        "startRank": start_rank,
        "offset": start_rank - 1,  # 0-indexed 누적 위치
    }
    resp = http.get(RANKING_URL2, params=params, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _slug_from_url(url: str) -> str | None:
    """https://www.musinsa.com/brand/onitsukatiger → 'onitsukatiger'."""
    if not url:
        return None
    tail = url.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    return tail or None


def _parse_modules(payload: Any) -> list[tuple[str, int]]:
    """RANKING_BRAND 모듈에서 (musinsa_brand_id, rank) 쌍 리스트로 반환."""
    data = payload.get("data") if isinstance(payload, dict) else None
    modules = data.get("modules") if isinstance(data, dict) else None
    if not isinstance(modules, list):
        return []

    out: list[tuple[str, int]] = []
    for idx, m in enumerate(modules, start=1):
        if not isinstance(m, dict) or m.get("type") != RANKING_MODULE_TYPE:
            continue
        title = m.get("title") or {}
        if not isinstance(title, dict):
            continue

        rank_raw = title.get("rank")
        try:
            rank = int(rank_raw) if rank_raw is not None else idx
        except (TypeError, ValueError):
            rank = idx

        on_click = title.get("onClick") or {}
        slug = _slug_from_url(on_click.get("url") if isinstance(on_click, dict) else "")
        if not slug:
            continue

        out.append((slug, rank))
    return out


def collect_rankings() -> int:
    """랭킹 스냅샷 1건을 brand_rankings 에 적재. 반환값은 insert 된 행 수."""
    ordered: list[tuple[str, int]] = []

    with build_session() as http:
        # 1~200위
        logger.info("rankings: fetching page=1 (URL1)")
        batch = _parse_modules(_fetch_page1(http))
        if not batch:
            logger.warning("rankings: no %s modules parsed (응답 구조 변경 의심)", RANKING_MODULE_TYPE)
            return 0
        ordered.extend(batch)

        # 201위~
        page, start_rank = 2, 201
        while True:
            polite_sleep()
            logger.info("rankings: fetching page=%d startRank=%d (URL2)", page, start_rank)
            batch = _parse_modules(_fetch_page_n(http, page, start_rank))
            if not batch:
                break
            ordered.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            page += 1
            start_rank += PAGE_SIZE

    collected_at = datetime.now()
    musinsa_ids = [mb_id for mb_id, _ in ordered]

    with get_session() as session:
        id_rows = session.execute(
            select(Brand.id, Brand.musinsa_brand_id).where(
                Brand.musinsa_brand_id.in_(musinsa_ids)
            )
        ).all()
        id_map = {mb_id: pk for pk, mb_id in id_rows}

        rows: list[dict] = []
        missing: list[str] = []
        for mb_id, rank in ordered:
            pk = id_map.get(mb_id)
            if pk is None:
                missing.append(mb_id)
                continue
            rows.append({"brand_id": pk, "rank": rank, "collected_at": collected_at})

        if rows:
            session.bulk_insert_mappings(BrandRanking, rows)

    logger.info(
        "rankings: inserted=%d parsed=%d missing_brand=%d (run brand_list first?)",
        len(rows),
        len(ordered),
        len(missing),
    )
    if missing:
        logger.debug("rankings: missing musinsa_brand_ids sample=%s", missing[:10])
    return len(rows)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    collect_rankings()
