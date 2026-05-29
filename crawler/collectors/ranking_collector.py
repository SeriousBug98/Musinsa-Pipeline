"""브랜드 랭킹 수집기.

랭킹 섹션 1066 (gf=A, subPan=brand) 응답에서 (brand, rank) 쌍을 뽑아
brand_rankings 에 스냅샷으로 insert.

응답 구조 (2026-05 기준):
    { "data": { "modules": [
        { "type": "QUERY_UPDATEDAT", ... },         # 메타 1개
        { "type": "RANKING_BRAND",                  # 브랜드 카드 200개
          "title": {
            "rank": "1",
            "title": { "text": "오니츠카타이거" },
            "onClick": { "url": "https://www.musinsa.com/brand/onitsukatiger" },
            ...
          },
          "items": [...]   # 그 브랜드의 상품 캐러셀 — 사용 안 함
        },
        ...
    ] } }

musinsa_brand_id 는 `title.onClick.url` 의 마지막 path segment (브랜드 슬러그) 로 추출.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select

from collectors._http import DEFAULT_TIMEOUT, build_session
from db.connection import get_session
from db.models import Brand, BrandRanking

logger = logging.getLogger(__name__)

RANKING_URL = (
    "https://client.musinsa.com/api/home/web/v5/pans/ranking/sections/1066"
)
RANKING_PARAMS = {"gf": "A", "subPan": "brand"}
RANKING_MODULE_TYPE = "RANKING_BRAND"


def _fetch_ranking() -> Any:
    with build_session() as http:
        resp = http.get(RANKING_URL, params=RANKING_PARAMS, timeout=DEFAULT_TIMEOUT)
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

        # rank 우선 — 명시값이 있고 정수면 사용, 아니면 모듈 위치(metadata 제외) 폴백
        rank_raw = title.get("rank")
        try:
            rank = int(rank_raw) if rank_raw is not None else idx
        except (TypeError, ValueError):
            rank = idx

        # brand slug — title.onClick.url 마지막 segment
        on_click = title.get("onClick") or {}
        slug = _slug_from_url(on_click.get("url") if isinstance(on_click, dict) else "")
        if not slug:
            continue

        out.append((slug, rank))
    return out


def collect_rankings() -> int:
    """랭킹 스냅샷 1건을 brand_rankings 에 적재. 반환값은 insert 된 행 수."""
    logger.info("rankings: fetching %s", RANKING_URL)
    payload = _fetch_ranking()
    ordered = _parse_modules(payload)
    if not ordered:
        logger.warning(
            "rankings: no %s modules parsed (응답 구조 변경 의심)",
            RANKING_MODULE_TYPE,
        )
        return 0

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
            rows.append(
                {"brand_id": pk, "rank": rank, "collected_at": collected_at}
            )

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
