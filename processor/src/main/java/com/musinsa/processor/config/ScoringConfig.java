package com.musinsa.processor.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * scoring.* 설정값 외부 주입. 가중치/임계값은 데이터가 쌓이면 조정될 수 있으므로 하드코딩하지 않는다.
 */
@ConfigurationProperties(prefix = "scoring")
public record ScoringConfig(
        Weights weights,
        Thresholds thresholds,
        double decayLambda,
        int risingBrandsLimit) {

    public record Weights(double rank, double fan, double soldout, double snap) {
    }

    public record Thresholds(
            int minFanCount,
            int minRankDays,
            int minFanDays,
            int soldoutHoldHours,
            double soldoutShrinkage,
            int minSnapDays) {
    }
}
