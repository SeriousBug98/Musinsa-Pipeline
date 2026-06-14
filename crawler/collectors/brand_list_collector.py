"""브랜드 목록 수집기.

무신사의 정적 브랜드 목록 JSON을 받아 `brands` 테이블에 upsert 한다.
- 적재 대상은 `subCategoryList` 에 "스트릿캐주얼" 이 포함된 브랜드로 한정한다.
- `musinsa_brand_id` 기준 충돌 시 name / english_name / link_url / is_active 갱신
- `joined_at` 은 최초 insert 시점의 값을 보존 (덮어쓰지 않음)
- `is_tracked` 는 DB 를 진실 원천으로 관리 (API/웹 UI 로 직접 토글)
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable

import requests
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db.connection import get_session
from db.models import Brand

logger = logging.getLogger(__name__)

BRAND_LIST_URL = "https://static.msscdn.net/display/brand/brand-list.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 30

# brand-list.json 응답의 subCategoryList 안에 이 정확한 문자열이 포함된 브랜드만 적재.
# 표기 확인: 2026-05 응답 기준 띄어쓰기 없는 '스트릿캐주얼' 로 통일됨.
STREET_CASUAL_LABEL = "스트릿캐주얼"

# joined_at 을 응답에서 파싱하지 못한 브랜드용 sentinel.
# 분석 단계의 "신규 입점 30일 이내" 규칙에 잘못 걸리지 않도록 충분히 과거로 둔다.
UNKNOWN_JOINED_AT = datetime(1970, 1, 1)


def _fetch_brand_list() -> dict | list:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    resp = requests.get(BRAND_LIST_URL, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _iter_brand_entries(payload) -> Iterable[dict]:
    """응답이 초성/알파벳 그룹 dict 형태든, 평탄한 list 형태든 모두 처리한다."""
    root = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(root, dict):
        for group in root.values():
            if isinstance(group, list):
                for item in group:
                    if isinstance(item, dict):
                        yield item
    elif isinstance(root, list):
        for item in root:
            if isinstance(item, dict):
                yield item


def _parse_joined_at(raw) -> datetime | None:
    if raw in (None, ""):
        return None
    if isinstance(raw, (int, float)):
        ts = raw / 1000 if raw > 1e12 else raw
        try:
            return datetime.fromtimestamp(ts)
        except (ValueError, OSError):
            return None
    if isinstance(raw, str):
        s = raw.strip().replace("T", " ")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(s[: len(fmt) + 4], fmt)
            except ValueError:
                continue
    return None


def _pick(entry: dict, *keys: str):
    for k in keys:
        v = entry.get(k)
        if v not in (None, ""):
            return v
    return None


def _is_street_casual(entry: dict) -> bool:
    sub = entry.get("subCategoryList")
    if not isinstance(sub, list):
        return False
    return STREET_CASUAL_LABEL in sub


def _normalize(entry: dict) -> dict | None:
    musinsa_id = _pick(entry, "id", "brandId", "brandLinkUrl", "linkUrl", "brand")
    name = _pick(entry, "name", "brandName", "korName", "kor_name")
    if not musinsa_id or not name:
        return None

    english_name = _pick(
        entry,
        "engName",
        "eng_name",
        "brandEngName",
        "englishName",
        "brandEnglishName",
    )
    link_url = _pick(entry, "link_url", "linkUrl", "brandLinkUrl", "url")
    if link_url and not str(link_url).startswith("http"):
        link_url = f"https://www.musinsa.com/brand/{link_url}"

    joined_at = (
        _parse_joined_at(_pick(entry, "joinDate", "joined_at", "joinedAt"))
        or _parse_joined_at(_pick(entry, "registerDate", "regDate", "createdAt"))
        or UNKNOWN_JOINED_AT
    )

    return {
        "musinsa_brand_id": str(musinsa_id),
        "name": str(name).strip(),
        "english_name": str(english_name).strip() if english_name else None,
        "link_url": link_url,
        "joined_at": joined_at,
    }


def _upsert_brands(rows: list[dict]) -> int:
    for row in rows:
        row["is_tracked"] = False  # 신규 브랜드 기본값; 기존 브랜드는 conflict 시 미갱신
        row["is_active"] = True

    stmt = pg_insert(Brand).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["musinsa_brand_id"],
        set_={
            "name": stmt.excluded.name,
            "english_name": stmt.excluded.english_name,
            "link_url": stmt.excluded.link_url,
            "is_active": stmt.excluded.is_active,
            # is_tracked, joined_at, created_at 은 의도적으로 보존
        },
    )
    with get_session() as session:
        session.execute(stmt)
    return len(rows)


def collect_brand_list() -> int:
    """브랜드 목록을 수집해 upsert 한다. 반환값은 upsert 한 행 수."""
    logger.info("brand_list: fetching %s", BRAND_LIST_URL)
    payload = _fetch_brand_list()

    rows: list[dict] = []
    seen: set[str] = set()
    total = 0
    filtered_out = 0
    skipped = 0
    for entry in _iter_brand_entries(payload):
        total += 1
        if not _is_street_casual(entry):
            filtered_out += 1
            continue
        norm = _normalize(entry)
        if norm is None:
            skipped += 1
            continue
        if norm["musinsa_brand_id"] in seen:
            continue
        seen.add(norm["musinsa_brand_id"])
        rows.append(norm)

    logger.info(
        "brand_list: filter total=%d street_casual=%d filtered_out=%d skipped=%d",
        total,
        len(rows),
        filtered_out,
        skipped,
    )

    if not rows:
        logger.warning("brand_list: no street-casual brands matched")
        return 0

    upserted = _upsert_brands(rows)
    logger.info("brand_list: upserted=%d", upserted)
    return upserted


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    collect_brand_list()
