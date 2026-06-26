package com.musinsa.processor.repository;

import com.musinsa.processor.domain.NewProduct;
import com.musinsa.processor.dto.ReviewVelocityRawDto;
import com.musinsa.processor.dto.SoldoutRawDto;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface NewProductRepository extends JpaRepository<NewProduct, Long> {

    /**
     * soldout_speed 집계: 최근 14일간 신상품이 얼마나 빨리 품절됐는가.
     * - DISTINCT ON (product_id): 같은 상품이 여러 카테고리에 잡혀도 1회만
     * - 감지 후 soldoutHoldHours 미만 미품절 상품은 판정 보류로 제외
     * - 베이지안 수축: (SUM + shrinkage*μ) / (N + shrinkage) 로 소표본 과대평가 방지
     */
    @Query(value = """
            WITH products AS (
                SELECT DISTINCT ON (product_id)
                    brand_id,
                    product_id,
                    is_sold_out,
                    first_seen_at,
                    sold_out_at,
                    EXTRACT(EPOCH FROM (sold_out_at - first_seen_at)) / 3600.0 AS hours_to_soldout
                FROM new_products
                WHERE first_seen_at >= NOW() - INTERVAL '14 days'
                  AND (
                      is_sold_out = TRUE
                      OR (
                          is_sold_out = FALSE
                          AND first_seen_at <= NOW() - (:soldoutHoldHours * INTERVAL '1 hour')
                      )
                  )
                ORDER BY product_id, first_seen_at DESC
            ),
            contrib AS (
                SELECT
                    brand_id,
                    CASE
                        WHEN is_sold_out = FALSE THEN 0.0
                        WHEN hours_to_soldout IS NULL THEN 0.5
                        ELSE GREATEST(0.0, 1.0 - hours_to_soldout / 168.0)
                    END AS contrib
                FROM products
            ),
            global_avg AS (
                SELECT AVG(contrib) AS mu FROM contrib
            )
            SELECT
                c.brand_id                                                              AS "brandId",
                (SUM(c.contrib) + :soldoutShrinkage * g.mu) / (COUNT(*) + :soldoutShrinkage) AS "soldoutRaw",
                COUNT(*)                                                                AS "productCount"
            FROM contrib c, global_avg g
            GROUP BY c.brand_id, g.mu
            """, nativeQuery = true)
    List<SoldoutRawDto> aggregateSoldoutSpeed(
            @Param("soldoutHoldHours") int soldoutHoldHours,
            @Param("soldoutShrinkage") double soldoutShrinkage);

    /**
     * review_velocity 집계: 최근 14일 신상품의 하루 평균 리뷰 증가 속도.
     * - (review_count - first_review_count) / 경과일 = 상품당 일평균 리뷰 증가
     * - 적립금 인센티브로 noisy — 브랜드당 평균 + 베이지안 수축으로 소표본 과대평가 방지
     * - hold-hours 미만 어린 상품 제외 (경과일 < 1 → 0 나눗셈 방지 겸용)
     * - DISTINCT ON (product_id): 동일 상품 여러 카테고리 중복 제거
     */
    @Query(value = """
            WITH products AS (
                SELECT DISTINCT ON (product_id)
                    brand_id,
                    product_id,
                    review_count,
                    first_review_count,
                    EXTRACT(EPOCH FROM (NOW() - first_seen_at)) / 86400.0 AS days_elapsed
                FROM new_products
                WHERE first_seen_at >= NOW() - INTERVAL '14 days'
                  AND first_seen_at <= NOW() - (:reviewHoldHours * INTERVAL '1 hour')
                  AND review_count IS NOT NULL
                  AND first_review_count IS NOT NULL
                ORDER BY product_id, first_seen_at DESC
            ),
            contrib AS (
                SELECT brand_id,
                       GREATEST(0.0, review_count - first_review_count) / days_elapsed AS contrib
                FROM products
            ),
            global_avg AS (
                SELECT AVG(contrib) AS mu FROM contrib
            )
            SELECT
                c.brand_id                                                                   AS "brandId",
                (SUM(c.contrib) + :reviewShrinkage * g.mu) / (COUNT(*) + :reviewShrinkage)  AS "reviewVelocityRaw",
                COUNT(*)                                                                     AS "productCount"
            FROM contrib c, global_avg g
            GROUP BY c.brand_id, g.mu
            """, nativeQuery = true)
    List<ReviewVelocityRawDto> aggregateReviewVelocity(
            @Param("reviewHoldHours") int reviewHoldHours,
            @Param("reviewShrinkage") double reviewShrinkage);
}
