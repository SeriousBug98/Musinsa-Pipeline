ALTER TABLE brand_scores
    ADD COLUMN IF NOT EXISTS review_velocity_score DECIMAL(5,2) NOT NULL DEFAULT 0.00;
