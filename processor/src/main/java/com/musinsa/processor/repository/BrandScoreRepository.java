package com.musinsa.processor.repository;

import com.musinsa.processor.domain.BrandScore;
import com.musinsa.processor.dto.BrandTrendDto;
import com.musinsa.processor.dto.RisingBrandDto;
import java.time.LocalDateTime;
import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface BrandScoreRepository extends JpaRepository<BrandScore, Long> {

    /**
     * 가장 최근 scored_at 배치 기준 모멘텀(상승세) 점수 상위 N개. brands 와 theta-join.
     * 반환 점수는 "현재 인기"가 아니라 rank/fan/soldout 기울기 기반 모멘텀.
     * limit 은 Pageable 로 전달.
     */
    @Query("""
            SELECT new com.musinsa.processor.dto.RisingBrandDto(
                b.id, b.musinsaBrandId, b.name,
                s.totalScore, s.rankChangeScore, s.fanGrowthScore, s.soldoutSpeedScore,
                s.snapBuzzScore, s.scoredAt)
            FROM BrandScore s, Brand b
            WHERE s.brandId = b.id
              AND s.scoredAt = (SELECT MAX(s2.scoredAt) FROM BrandScore s2)
            ORDER BY s.totalScore DESC
            """)
    List<RisingBrandDto> findRisingBrands(Pageable pageable);

    /**
     * 특정 브랜드의 since 이후 점수 추이(오름차순).
     */
    @Query("""
            SELECT new com.musinsa.processor.dto.BrandTrendDto(
                s.totalScore, s.rankChangeScore, s.fanGrowthScore, s.soldoutSpeedScore,
                s.snapBuzzScore, s.scoredAt)
            FROM BrandScore s
            WHERE s.brandId = :brandId
              AND s.scoredAt >= :since
            ORDER BY s.scoredAt
            """)
    List<BrandTrendDto> findTrend(
            @Param("brandId") Long brandId,
            @Param("since") LocalDateTime since);
}
