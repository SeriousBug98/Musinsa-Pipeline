-- Tier 1: new_products 에 리뷰/썸네일/할인율 컬럼 추가
-- 전부 NULL 허용이라 기존 행·조회에 영향 없음 (무중단 적용 가능)
ALTER TABLE new_products
    ADD COLUMN IF NOT EXISTS discount_rate      INTEGER,
    ADD COLUMN IF NOT EXISTS review_count       INTEGER,
    ADD COLUMN IF NOT EXISTS first_review_count INTEGER,
    ADD COLUMN IF NOT EXISTS review_score       DECIMAL(3,1),
    ADD COLUMN IF NOT EXISTS thumbnail_url      VARCHAR(500);
