package com.musinsa.processor.repository;

import com.musinsa.processor.domain.BrandFan;
import com.musinsa.processor.dto.FanRawDto;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface BrandFanRepository extends JpaRepository<BrandFan, Long> {

    /**
     * fan_growth 집계: 최근 14일간 팬수 비율 성장 추세(기울기).
     * - ln(fan_count) 로 절댓값이 아닌 비율 성장 측정 (fan_count > 0 가드로 ln(0) 방지)
     * - 관측일 minFanDays 미만 또는 max 팬수 minFanCount 미만 브랜드는 제외(HAVING)
     */
    @Query(value = """
            SELECT
                brand_id                                                                 AS "brandId",
                regr_slope(ln(fan_count), EXTRACT(EPOCH FROM collected_at) / 86400.0)     AS "fanSlope",
                count(*)                                                                 AS "daysObserved"
            FROM brand_fans
            WHERE collected_at >= NOW() - INTERVAL '14 days'
              AND fan_count > 0
            GROUP BY brand_id
            HAVING count(*) >= :minFanDays
               AND max(fan_count) >= :minFanCount
            """, nativeQuery = true)
    List<FanRawDto> aggregateFanGrowth(
            @Param("minFanDays") int minFanDays,
            @Param("minFanCount") int minFanCount);
}
