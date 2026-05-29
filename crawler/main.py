import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from collectors.brand_list_collector import collect_brand_list
from collectors.fan_collector import collect_fans
from collectors.product_collector import collect_new_products
from collectors.ranking_collector import collect_rankings


LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def setup_logging() -> None:
    log_file = LOG_DIR / f"crawler-{datetime.now().strftime('%Y-%m-%d')}.log"
    handler = logging.handlers.TimedRotatingFileHandler(
        log_file, when="midnight", backupCount=30, encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )
    handler.setFormatter(formatter)

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.addHandler(stream)


def job_brand_list() -> None:
    try:
        collect_brand_list()
    except Exception:
        logging.exception("brand_list job failed")


def job_rankings() -> None:
    try:
        collect_rankings()
    except Exception:
        logging.exception("rankings job failed")


def job_fans() -> None:
    try:
        collect_fans()
    except Exception:
        logging.exception("fans job failed")


def job_products() -> None:
    try:
        collect_new_products()
    except Exception:
        logging.exception("products job failed")


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    scheduler = BlockingScheduler(timezone="Asia/Seoul")

    scheduler.add_job(
        job_brand_list,
        trigger=CronTrigger(hour=3),
        id="brand_list",
        name="브랜드 목록 수집",
    )
    scheduler.add_job(
        job_rankings,
        trigger=IntervalTrigger(hours=3),
        id="rankings",
        name="브랜드 랭킹 수집",
    )
    scheduler.add_job(
        job_fans,
        trigger=CronTrigger(hour=0),
        id="fans",
        name="브랜드 팬수 수집",
    )
    scheduler.add_job(
        job_products,
        trigger=IntervalTrigger(hours=6),
        id="products",
        name="신상품 품절 현황 수집",
    )

    logger.info("scheduler starting with %d jobs", len(scheduler.get_jobs()))
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("scheduler stopped")


if __name__ == "__main__":
    main()
