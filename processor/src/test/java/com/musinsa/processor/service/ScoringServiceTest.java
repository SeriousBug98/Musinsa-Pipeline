package com.musinsa.processor.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.musinsa.processor.config.ScoringConfig;
import com.musinsa.processor.domain.BrandScore;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * compute() 순수 단위 테스트 — DB 불필요.
 * 백분위(mid-rank), 재정규화 가중합, 결손 지표 0.00 저장, 반올림을 검증한다.
 */
class ScoringServiceTest {

    private static final LocalDateTime AT = LocalDateTime.of(2026, 6, 3, 1, 0);

    private ScoringService service() {
        ScoringConfig config = new ScoringConfig(
                new ScoringConfig.Weights(0.45, 0.35, 0.20, 0.20),
                new ScoringConfig.Thresholds(500, 3, 4, 24, 5.0, 3),
                0.231,   // decayLambda — 단위 테스트는 compute()만 호출하므로 실제 사용 안 됨
                20);
        return new ScoringService(null, null, null, null, null, config);
    }

    private BrandScore byBrand(List<BrandScore> scores, long brandId) {
        return scores.stream()
                .filter(s -> s.getBrandId() == brandId)
                .findFirst()
                .orElseThrow(() -> new AssertionError("brand " + brandId + " not scored"));
    }

    @Test
    void singletonMetricGetsMidRank50AndRenormalizesToItself() {
        List<BrandScore> scores = service().compute(
                Map.of(1L, 0.5), Map.of(), Map.of(), Map.of(), AT);

        BrandScore s = byBrand(scores, 1L);
        // 단일 모집단 mid-rank = (0 + 0.5*1)/1*100 = 50
        assertThat(s.getRankChangeScore()).isEqualByComparingTo("50.00");
        assertThat(s.getFanGrowthScore()).isEqualByComparingTo("0.00");
        assertThat(s.getSoldoutSpeedScore()).isEqualByComparingTo("0.00");
        // soldout/fan 결손 → rank 만으로 재정규화: (50*0.45)/0.45 = 50
        assertThat(s.getTotalScore()).isEqualByComparingTo("50.00");
        assertThat(s.getScoredAt()).isEqualTo(AT);
    }

    @Test
    void renormalizesWhenSoldoutMissing() {
        // rank: brand2 = 중앙값 → 50, fan: brand2 = 상위 → 75, soldout/snap 없음
        List<BrandScore> scores = service().compute(
                Map.of(1L, 10.0, 2L, 20.0, 3L, 30.0),
                Map.of(2L, 5.0, 4L, 1.0),
                Map.of(),
                Map.of(),
                AT);

        BrandScore s = byBrand(scores, 2L);
        assertThat(s.getRankChangeScore()).isEqualByComparingTo("50.00");
        assertThat(s.getFanGrowthScore()).isEqualByComparingTo("75.00");
        assertThat(s.getSoldoutSpeedScore()).isEqualByComparingTo("0.00");
        // (50*0.45 + 75*0.35) / 0.80 = 48.75/0.80 = 60.9375 → 60.94
        assertThat(s.getTotalScore()).isEqualByComparingTo("60.94");
    }

    @Test
    void weightsAllThreePresent() {
        List<BrandScore> scores = service().compute(
                Map.of(1L, 10.0, 2L, 20.0, 3L, 30.0),
                Map.of(2L, 5.0, 4L, 1.0),
                Map.of(2L, 9.0, 5L, 1.0),
                Map.of(),
                AT);

        BrandScore s = byBrand(scores, 2L);
        assertThat(s.getSoldoutSpeedScore()).isEqualByComparingTo("75.00");
        // (50*0.45 + 75*0.35 + 75*0.20) / 1.0 = 63.75
        assertThat(s.getTotalScore()).isEqualByComparingTo("63.75");
    }

    @Test
    void unionOfAllBrandsIsScored() {
        List<BrandScore> scores = service().compute(
                Map.of(1L, 1.0),
                Map.of(2L, 1.0),
                Map.of(3L, 1.0),
                Map.of(),
                AT);
        assertThat(scores).hasSize(3);
        assertThat(scores.stream().map(BrandScore::getBrandId))
                .containsExactlyInAnyOrder(1L, 2L, 3L);
    }

    @Test
    void snapBuzzContributesToTotalAndRenormalizesCorrectly() {
        // brand1: rank=50(유일), snap=75(유일). soldout/fan 없음.
        // total = (50*0.45 + 75*0.20) / (0.45+0.20) = (22.5+15) / 0.65 = 37.5/0.65 = 57.69...
        List<BrandScore> scores = service().compute(
                Map.of(1L, 1.0),
                Map.of(),
                Map.of(),
                Map.of(1L, 5.0, 2L, 1.0),  // brand1=상위(75점), brand2=하위(25점)
                AT);

        BrandScore s = byBrand(scores, 1L);
        assertThat(s.getSnapBuzzScore()).isEqualByComparingTo("75.00");
        assertThat(s.getRankChangeScore()).isEqualByComparingTo("50.00");
        assertThat(s.getFanGrowthScore()).isEqualByComparingTo("0.00");
        assertThat(s.getSoldoutSpeedScore()).isEqualByComparingTo("0.00");
        // (50*0.45 + 75*0.20) / (0.45+0.20) = 57.6923... → 57.69
        assertThat(s.getTotalScore()).isEqualByComparingTo("57.69");
    }

    @Test
    void snapOnlyBrandGetsZeroOnOtherMetrics() {
        // snap 데이터만 있는 브랜드 → 나머지 점수 0.00, total 은 snap 단독 재정규화
        List<BrandScore> scores = service().compute(
                Map.of(),
                Map.of(),
                Map.of(),
                Map.of(10L, 1.0),
                AT);

        BrandScore s = byBrand(scores, 10L);
        assertThat(s.getSnapBuzzScore()).isEqualByComparingTo("50.00");
        assertThat(s.getRankChangeScore()).isEqualByComparingTo("0.00");
        assertThat(s.getTotalScore()).isEqualByComparingTo("50.00");
    }
}
