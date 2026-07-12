-- reviewScore는 별점(0~5) x 20 = 0~100 스케일. DECIMAL(3,1)(최대 99.9)에서
-- 만점(100.0) 상품이 있으면 numeric field overflow로 upsert 전체가 롤백되던 버그 수정.
ALTER TABLE new_products
    ALTER COLUMN review_score TYPE DECIMAL(4,1);
