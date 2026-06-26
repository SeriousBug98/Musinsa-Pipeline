-- brand_scores에 snap_buzz_score 컬럼 추가
-- DEFAULT 0.00 으로 기존 행 백필 → NOT NULL 충족, 무중단 적용 가능
ALTER TABLE brand_scores
    ADD COLUMN IF NOT EXISTS snap_buzz_score DECIMAL(5,2) NOT NULL DEFAULT 0.00;
