package com.musinsa.processor.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * GET /brands/hot 응답 항목. brand_scores 최신 배치 + brands 조인 결과.
 */
public record HotBrandDto(
        Long brandId,
        String musinsaBrandId,
        String name,
        BigDecimal totalScore,
        BigDecimal rankChangeScore,
        BigDecimal fanGrowthScore,
        BigDecimal soldoutSpeedScore,
        LocalDateTime scoredAt) {
}
