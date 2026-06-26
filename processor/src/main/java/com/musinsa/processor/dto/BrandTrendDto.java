package com.musinsa.processor.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * GET /brands/{id}/trend 응답 항목. 특정 브랜드의 점수 추이 한 점.
 */
public record BrandTrendDto(
        BigDecimal totalScore,
        BigDecimal rankChangeScore,
        BigDecimal fanGrowthScore,
        BigDecimal soldoutSpeedScore,
        BigDecimal snapBuzzScore,
        LocalDateTime scoredAt) {
}
