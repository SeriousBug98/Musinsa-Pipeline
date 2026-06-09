package com.musinsa.processor.repository;

import com.musinsa.processor.domain.BrandRanking;
import com.musinsa.processor.dto.RankRawDto;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface BrandRankingRepository extends JpaRepository<BrandRanking, Long> {

    /**
     * rank_change 집계: 최근 7일간 순위 상승 추세(기울기) — 지수 감쇠 가중 최소제곱(WLS).
     * - 하루 med_rank(중앙값)로 일시적 튐 차단
     * - -ln(rank) 로 비율 비교 가능하게 변환
     * - w = exp(-λ·ago): 최근 데이터에 더 높은 가중치 (반감기=ln2/λ일)
     * - WLS 기울기 공식: (Σw·Σwxy - Σwx·Σwy) / (Σw·Σwxx - (Σwx)²)
     *   (PostgreSQL regr_slope 는 가중치 미지원이므로 직접 전개)
     * - NULLIF 가드: 분모=0(관측일 1개 등)이면 NULL → ScoringService 에서 건너뜀
     * - 관측일 minRankDays 미만 브랜드는 제외(HAVING)
     *
     * 컬럼 alias 는 RankRawDto getter 명과 매핑되도록 따옴표로 camelCase 보존.
     */
    @Query(value = """
            WITH daily AS (
                SELECT
                    brand_id,
                    date_trunc('day', collected_at)                        AS d,
                    percentile_cont(0.5) WITHIN GROUP (ORDER BY rank)      AS med_rank
                FROM brand_rankings
                WHERE collected_at >= NOW() - INTERVAL '7 days'
                GROUP BY brand_id, date_trunc('day', collected_at)
            ),
            weighted AS (
                SELECT
                    brand_id,
                    -ln(med_rank)                                                      AS y,
                    EXTRACT(EPOCH FROM d) / 86400.0                                    AS x,
                    EXP(-:decayLambda * EXTRACT(EPOCH FROM (NOW() - d)) / 86400.0)    AS w
                FROM daily
            )
            SELECT
                brand_id                                                               AS "brandId",
                (SUM(w) * SUM(w*x*y) - SUM(w*x) * SUM(w*y))
                    / NULLIF(SUM(w) * SUM(w*x*x) - SUM(w*x) * SUM(w*x), 0)           AS "rankSlope",
                count(*)                                                               AS "daysObserved"
            FROM weighted
            GROUP BY brand_id
            HAVING count(*) >= :minRankDays
            """, nativeQuery = true)
    List<RankRawDto> aggregateRankChange(
            @Param("minRankDays") int minRankDays,
            @Param("decayLambda") double decayLambda);
}
