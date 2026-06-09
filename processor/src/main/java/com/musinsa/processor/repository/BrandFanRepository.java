package com.musinsa.processor.repository;

import com.musinsa.processor.domain.BrandFan;
import com.musinsa.processor.dto.FanRawDto;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface BrandFanRepository extends JpaRepository<BrandFan, Long> {

    /**
     * fan_growth 집계: 최근 14일간 팬수 비율 성장 추세(기울기) — 지수 감쇠 가중 최소제곱(WLS).
     * - 하루 med_fan(중앙값)으로 수집 주기 변화에 의한 가중치 불균형 차단 (rank_change 와 동일 패턴)
     * - ln(med_fan) 으로 절댓값이 아닌 비율 성장 측정 (fan_count > 0 가드로 ln(0) 방지)
     * - w = exp(-λ·ago): 최근 데이터에 더 높은 가중치 (rank_change 와 동일 λ)
     * - WLS 기울기 공식: (Σw·Σwxy - Σwx·Σwy) / (Σw·Σwxx - (Σwx)²)
     * - NULLIF 가드: 분모=0이면 NULL → ScoringService 에서 건너뜀
     * - HAVING count(*) 는 daily CTE 기준이므로 정확히 "관측된 날 수" 를 셈
     * - 관측일 minFanDays 미만 또는 max 팬수 minFanCount 미만 브랜드는 제외(HAVING)
     */
    @Query(value = """
            WITH daily AS (
                SELECT
                    brand_id,
                    date_trunc('day', collected_at)                        AS d,
                    percentile_cont(0.5) WITHIN GROUP (ORDER BY fan_count) AS med_fan
                FROM brand_fans
                WHERE collected_at >= NOW() - INTERVAL '14 days'
                  AND fan_count > 0
                GROUP BY brand_id, date_trunc('day', collected_at)
            ),
            weighted AS (
                SELECT
                    brand_id,
                    med_fan,
                    ln(med_fan)                                                        AS y,
                    EXTRACT(EPOCH FROM d) / 86400.0                                    AS x,
                    EXP(-:decayLambda * EXTRACT(EPOCH FROM (NOW() - d)) / 86400.0)    AS w
                FROM daily
            )
            SELECT
                brand_id                                                               AS "brandId",
                (SUM(w) * SUM(w*x*y) - SUM(w*x) * SUM(w*y))
                    / NULLIF(SUM(w) * SUM(w*x*x) - SUM(w*x) * SUM(w*x), 0)           AS "fanSlope",
                count(*)                                                               AS "daysObserved"
            FROM weighted
            GROUP BY brand_id
            HAVING count(*) >= :minFanDays
               AND max(med_fan) >= :minFanCount
            """, nativeQuery = true)
    List<FanRawDto> aggregateFanGrowth(
            @Param("minFanDays") int minFanDays,
            @Param("minFanCount") int minFanCount,
            @Param("decayLambda") double decayLambda);
}
