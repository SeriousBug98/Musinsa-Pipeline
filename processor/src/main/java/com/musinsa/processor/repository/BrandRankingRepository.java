package com.musinsa.processor.repository;

import com.musinsa.processor.domain.BrandRanking;
import com.musinsa.processor.dto.RankRawDto;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface BrandRankingRepository extends JpaRepository<BrandRanking, Long> {

    /**
     * rank_change 집계: 최근 7일간 순위 상승 추세(기울기).
     * - 하루 med_rank(중앙값)로 일시적 튐 차단
     * - -ln(rank) 로 비율 비교 가능하게 변환 후 일 단위 시간축으로 regr_slope
     * - 관측일 minRankDays 미만 브랜드는 제외(HAVING)
     *
     * 컬럼 alias 는 RankRawDto getter 명과 매핑되도록 따옴표로 camelCase 보존.
     */
    @Query(value = """
            WITH daily AS (
                SELECT
                    brand_id,
                    date_trunc('day', collected_at)                    AS d,
                    percentile_cont(0.5) WITHIN GROUP (ORDER BY rank)  AS med_rank
                FROM brand_rankings
                WHERE collected_at >= NOW() - INTERVAL '7 days'
                GROUP BY brand_id, date_trunc('day', collected_at)
            )
            SELECT
                brand_id                                                       AS "brandId",
                regr_slope(-ln(med_rank), EXTRACT(EPOCH FROM d) / 86400.0)      AS "rankSlope",
                count(*)                                                       AS "daysObserved"
            FROM daily
            GROUP BY brand_id
            HAVING count(*) >= :minRankDays
            """, nativeQuery = true)
    List<RankRawDto> aggregateRankChange(@Param("minRankDays") int minRankDays);
}
