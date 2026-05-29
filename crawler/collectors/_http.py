"""Collector 공통 HTTP 유틸. User-Agent, 요청 간 1.5~3초 정중한 딜레이."""

from __future__ import annotations

import random
import time

import requests

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 30
DELAY_RANGE = (1.5, 3.0)


def build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        }
    )
    return s


def polite_sleep() -> None:
    time.sleep(random.uniform(*DELAY_RANGE))
