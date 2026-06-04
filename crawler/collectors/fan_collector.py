"""브랜드 팬수 수집기.

활성 브랜드의 musinsa_brand_id 를 배치로 POST 하여 팬 카운트를 받아 brand_fans 에 스냅샷 적재.

응답 구조 (2026-05):
    { "data": { "contents": { "items": [
        {"likeType": "BRAND", "relationId": "032c", "count": 2378, "liked": false},
        ...
    ] } } }

1일 1회 보장: 진입 시 오늘 collected_at 의 행이 이미 있으면 즉시 return.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time

import requests
from sqlalchemy import func, select

from collectors._http import DEFAULT_TIMEOUT, build_session, polite_sleep
from db.connection import get_session
from db.models import Brand, BrandFan

logger = logging.getLogger(__name__)

FAN_URL = "https://like.musinsa.com/like/api/v2/liketypes/brand/counts"
BATCH_SIZE = 50


def _extract_items(payload) -> list:
    """data.contents.items 우선, 응답 구조 변형도 일부 흡수."""
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if isinstance(data, dict):
        contents = data.get("contents")
        if isinstance(contents, dict) and isinstance(contents.get("items"), list):
            return contents["items"]
        if isinstance(data.get("items"), list):
            return data["items"]
    if isinstance(payload.get("items"), list):
        return payload["items"]
    if isinstance(data, list):
        return data
    return []


def _fetch_counts(
    http: requests.Session, brand_ids: list[str]
) -> dict[str, int]:
    body = {"gf": "A", "relationIds": brand_ids}
    resp = http.post(FAN_URL, json=body, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()

    counts: dict[str, int] = {}
    for item in _extract_items(payload):
        if not isinstance(item, dict):
            continue
        rid = item.get("relationId") or item.get("brandId") or item.get("id")
        cnt = item.get("count")
        if cnt is None:
            cnt = item.get("fanCount") or item.get("likeCount")
        if rid is None or cnt is None:
            continue
        try:
            counts[str(rid)] = int(cnt)
        except (TypeError, ValueError):
            continue
    return counts


def _today_has_rows() -> int:
    today = date.today()
    start = datetime.combine(today, time.min)
    end = datetime.combine(today, time.max)
    with get_session() as session:
        return (
            session.execute(
                select(func.count(BrandFan.id)).where(
                    BrandFan.collected_at >= start,
                    BrandFan.collected_at <= end,
                )
            ).scalar()
            or 0
        )


def collect_fans() -> int:
    """모든 활성 브랜드의 팬수 스냅샷을 적재. 반환값은 insert 된 행 수.

    1일 1회 보장: 오늘 brand_fans 행이 이미 있으면 즉시 0 반환.
    """
    already = _today_has_rows()
    if already > 0:
        logger.info("fans: skip — already collected today (%d rows)", already)
        return 0

    with get_session() as session:
        brand_rows = session.execute(
            select(Brand.id, Brand.musinsa_brand_id).where(Brand.is_active.is_(True))
        ).all()

    if not brand_rows:
        logger.warning("fans: no active brands found")
        return 0

    id_map: dict[str, int] = {mb_id: pk for pk, mb_id in brand_rows}
    musinsa_ids = list(id_map.keys())
    total_batches = (len(musinsa_ids) + BATCH_SIZE - 1) // BATCH_SIZE

    collected_at = datetime.now()
    rows: list[dict] = []
    failures = 0

    with build_session() as http:
        for i in range(0, len(musinsa_ids), BATCH_SIZE):
            batch = musinsa_ids[i : i + BATCH_SIZE]
            try:
                counts = _fetch_counts(http, batch)
            except Exception:
                failures += 1
                logger.exception(
                    "fans: batch %d/%d failed", i // BATCH_SIZE + 1, total_batches
                )
                polite_sleep()
                continue

            for mb_id, cnt in counts.items():
                pk = id_map.get(mb_id)
                if pk is None:
                    continue
                rows.append(
                    {"brand_id": pk, "fan_count": cnt, "collected_at": collected_at}
                )

            if i + BATCH_SIZE < len(musinsa_ids):
                polite_sleep()

    if rows:
        with get_session() as session:
            session.bulk_insert_mappings(BrandFan, rows)

    logger.info(
        "fans: inserted=%d brands=%d batches=%d failures=%d",
        len(rows),
        len(musinsa_ids),
        total_batches,
        failures,
    )
    return len(rows)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    collect_fans()
