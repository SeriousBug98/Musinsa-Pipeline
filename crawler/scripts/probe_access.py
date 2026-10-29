"""무신사 API 접근 가능 여부 점검 (DB 미사용).

각 수집기의 실제 fetch 함수를 1회씩 호출해 응답 건수만 출력한다.
하나라도 실패하면 exit 1.

    python scripts/probe_access.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors import (  # noqa: E402
    brand_list_collector,
    fan_collector,
    product_collector,
    ranking_collector,
    snap_collector,
)
from collectors._http import build_session, polite_sleep  # noqa: E402


def main() -> int:
    http = build_session()
    failed = 0

    def check(name: str, fn) -> object:
        nonlocal failed
        try:
            result = fn()
            print(f"OK   {name}: {result if isinstance(result, str) else len(result)}")
            return result
        except Exception as e:  # 원인 파악용으로 전부 출력
            failed += 1
            print(f"FAIL {name}: {type(e).__name__}: {e}")
            return None
        finally:
            polite_sleep()

    check("brand_list", lambda: list(
        brand_list_collector._iter_brand_entries(brand_list_collector._fetch_brand_list())
    ))
    ranking = check("ranking", lambda: ranking_collector._parse_modules(
        ranking_collector._fetch_page1(http)
    ))
    brand_ids = [b for b, _ in ranking][:5] if ranking else ["musinsastandard"]
    check("fans", lambda: fan_collector._fetch_counts(http, brand_ids))
    check("products", lambda: product_collector._fetch_brand_category(
        http, brand_ids[0], "001"
    ))
    snaps = check("snap_rankings", lambda: snap_collector._fetch_rankings_page(http, 1))
    goods = [str(g.get("goodsNo")) for s in (snaps or []) for g in s.get("goods", [])][:5]
    # _fetch_goods_brands 는 내부에서 예외를 삼키므로 빈 결과를 실패로 간주
    check("snap_goods", lambda: snap_collector._fetch_goods_brands(http, goods) or 1 / 0)

    print(f"\n{'ALL OK' if not failed else f'{failed} FAILED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
