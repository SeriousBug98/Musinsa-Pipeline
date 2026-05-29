-- 브랜드 기준 테이블
CREATE TABLE brands (
    id                BIGSERIAL PRIMARY KEY,
    musinsa_brand_id  VARCHAR(100) NOT NULL UNIQUE,
    name              VARCHAR(200) NOT NULL,
    english_name      VARCHAR(200),
    link_url          VARCHAR(500),
    is_tracked        BOOLEAN NOT NULL DEFAULT FALSE,
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    joined_at         TIMESTAMP NOT NULL,
    created_at        TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_brands_is_tracked ON brands(is_tracked) WHERE is_tracked = TRUE;
CREATE INDEX idx_brands_joined_at ON brands(joined_at);

-- 랭킹 스냅샷
CREATE TABLE brand_rankings (
    id           BIGSERIAL PRIMARY KEY,
    brand_id     BIGINT NOT NULL REFERENCES brands(id),
    rank         INTEGER NOT NULL,
    collected_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_brand_rankings_brand_id ON brand_rankings(brand_id);
CREATE INDEX idx_brand_rankings_collected_at ON brand_rankings(collected_at);

-- 팬수 스냅샷
CREATE TABLE brand_fans (
    id           BIGSERIAL PRIMARY KEY,
    brand_id     BIGINT NOT NULL REFERENCES brands(id),
    fan_count    INTEGER NOT NULL,
    collected_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_brand_fans_brand_id ON brand_fans(brand_id);
CREATE INDEX idx_brand_fans_collected_at ON brand_fans(collected_at);

-- 신상품 품절 현황
CREATE TABLE new_products (
    id            BIGSERIAL PRIMARY KEY,
    brand_id      BIGINT NOT NULL REFERENCES brands(id),
    product_id    VARCHAR(100) NOT NULL,
    product_name  VARCHAR(300) NOT NULL,
    category_code VARCHAR(10) NOT NULL,
    price         INTEGER,
    final_price   INTEGER,
    is_sold_out   BOOLEAN NOT NULL DEFAULT FALSE,
    first_seen_at TIMESTAMP NOT NULL,
    sold_out_at   TIMESTAMP,
    UNIQUE(product_id, category_code)
);

CREATE INDEX idx_new_products_brand_id ON new_products(brand_id);
CREATE INDEX idx_new_products_first_seen_at ON new_products(first_seen_at);
CREATE INDEX idx_new_products_is_sold_out ON new_products(is_sold_out);

-- 분석 결과 (Spring Boot Processor가 저장)
CREATE TABLE brand_scores (
    id                  BIGSERIAL PRIMARY KEY,
    brand_id            BIGINT NOT NULL REFERENCES brands(id),
    rank_change_score   DECIMAL(5,2) NOT NULL,
    fan_growth_score    DECIMAL(5,2) NOT NULL,
    soldout_speed_score DECIMAL(5,2) NOT NULL,
    total_score         DECIMAL(5,2) NOT NULL,
    scored_at           TIMESTAMP NOT NULL
);

CREATE INDEX idx_brand_scores_brand_id ON brand_scores(brand_id);
CREATE INDEX idx_brand_scores_total_score ON brand_scores(total_score DESC);
CREATE INDEX idx_brand_scores_scored_at ON brand_scores(scored_at);