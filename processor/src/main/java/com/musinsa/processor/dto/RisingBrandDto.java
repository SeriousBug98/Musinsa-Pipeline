package com.musinsa.processor.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * GET /brands/rising 응답 항목.
 * rank/fan/soldout/snap 지표의 기울기(모멘텀) 기반 점수 — "현재 인기"가 아니라 "상승 중인" 브랜드.
 * brand_scores 최신 배치 + brands 조인 결과.
 */
public record RisingBrandDto(
        Long brandId,
        String musinsaBrandId,
        String name,
        BigDecimal totalScore,
        BigDecimal rankChangeScore,
        BigDecimal fanGrowthScore,
        BigDecimal soldoutSpeedScore,
        BigDecimal snapBuzzScore,
        BigDecimal reviewVelocityScore,
        LocalDateTime scoredAt) {
}
