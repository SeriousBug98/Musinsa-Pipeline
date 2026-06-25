-- Tier 2: 스냅 STREET 랭킹 UGC 버즈 수집용 테이블 신설
-- 신규 테이블이라 기존 행/쿼리에 영향 없음 (무중단 적용 가능)
CREATE TABLE IF NOT EXISTS brand_snap_mentions (
    id              BIGSERIAL PRIMARY KEY,
    brand_id        BIGINT REFERENCES brands(id),
    brand_name      VARCHAR(200) NOT NULL,
    mention_count   INTEGER NOT NULL,
    best_rank       INTEGER NOT NULL,
    snap_like_sum   INTEGER,
    snap_view_sum   INTEGER,
    top_snap_id     VARCHAR(100),
    period          VARCHAR(10) NOT NULL DEFAULT 'DAILY',
    collected_at    TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_brand_snap_mentions_brand_id
    ON brand_snap_mentions(brand_id);
CREATE INDEX IF NOT EXISTS idx_brand_snap_mentions_collected_at
    ON brand_snap_mentions(collected_at);
CREATE INDEX IF NOT EXISTS idx_brand_snap_mentions_brand_name
    ON brand_snap_mentions(brand_name);
CREATE INDEX IF NOT EXISTS idx_brand_snap_mentions_unmatched
    ON brand_snap_mentions(mention_count DESC, best_rank)
    WHERE brand_id IS NULL;
