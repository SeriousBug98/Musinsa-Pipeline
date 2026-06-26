package com.musinsa.processor.service;

import com.musinsa.processor.config.ScoringConfig;
import com.musinsa.processor.domain.BrandScore;
import com.musinsa.processor.repository.BrandFanRepository;
import com.musinsa.processor.repository.BrandRankingRepository;
import com.musinsa.processor.repository.BrandScoreRepository;
import com.musinsa.processor.repository.BrandSnapMentionRepository;
import com.musinsa.processor.repository.NewProductRepository;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 핵심 스코어링 로직.
 *
 * <pre>
 * ① native SQL 4개로 브랜드별 raw 집계값 조회
 * ② brand_id 기준 병합
 * ③ 지표별 백분위 정규화 (0~100, mid-rank)
 * ④ 재정규화 가중합  total = Σ(pct·w) / Σ(w)  (존재하는 지표만)
 * ⑤ brand_scores INSERT (append-only)
 * </pre>
 */
@Service
public class ScoringService {

    private static final Logger log = LoggerFactory.getLogger(ScoringService.class);

    private final BrandRankingRepository rankingRepository;
    private final BrandFanRepository fanRepository;
    private final NewProductRepository newProductRepository;
    private final BrandSnapMentionRepository snapMentionRepository;
    private final BrandScoreRepository scoreRepository;
    private final ScoringConfig config;

    public ScoringService(
            BrandRankingRepository rankingRepository,
            BrandFanRepository fanRepository,
            NewProductRepository newProductRepository,
            BrandSnapMentionRepository snapMentionRepository,
            BrandScoreRepository scoreRepository,
            ScoringConfig config) {
        this.rankingRepository = rankingRepository;
        this.fanRepository = fanRepository;
        this.newProductRepository = newProductRepository;
        this.snapMentionRepository = snapMentionRepository;
        this.scoreRepository = scoreRepository;
        this.config = config;
    }

    /** 한 번의 스코어링 run. 반환값은 INSERT 된 brand_scores 행 수. */
    @Transactional
    public int run() {
        LocalDateTime scoredAt = LocalDateTime.now();
        ScoringConfig.Thresholds t = config.thresholds();

        double lambda = config.decayLambda();

        Map<Long, Double> rankSlopes = new HashMap<>();
        rankingRepository.aggregateRankChange(t.minRankDays(), lambda).forEach(r -> {
            if (r.getRankSlope() != null) {
                rankSlopes.put(r.getBrandId(), r.getRankSlope());
            }
        });

        Map<Long, Double> fanSlopes = new HashMap<>();
        fanRepository.aggregateFanGrowth(t.minFanDays(), t.minFanCount(), lambda).forEach(r -> {
            if (r.getFanSlope() != null) {
                fanSlopes.put(r.getBrandId(), r.getFanSlope());
            }
        });

        Map<Long, Double> soldoutRaws = new HashMap<>();
        newProductRepository.aggregateSoldoutSpeed(t.soldoutHoldHours(), t.soldoutShrinkage())
                .forEach(r -> {
                    if (r.getSoldoutRaw() != null) {
                        soldoutRaws.put(r.getBrandId(), r.getSoldoutRaw());
                    }
                });

        Map<Long, Double> snapSlopes = new HashMap<>();
        snapMentionRepository.aggregateSnapBuzz(t.minSnapDays(), lambda).forEach(r -> {
            if (r.getSnapSlope() != null) {
                snapSlopes.put(r.getBrandId(), r.getSnapSlope());
            }
        });

        Map<Long, Double> reviewRaws = new HashMap<>();
        newProductRepository.aggregateReviewVelocity(t.reviewHoldHours(), t.reviewShrinkage()).forEach(r -> {
            if (r.getReviewVelocityRaw() != null) {
                reviewRaws.put(r.getBrandId(), r.getReviewVelocityRaw());
            }
        });

        List<BrandScore> scores = compute(rankSlopes, fanSlopes, soldoutRaws, snapSlopes, reviewRaws, scoredAt);
        scoreRepository.saveAll(scores);

        log.info("scoring run done: rank={}, fan={}, soldout={}, snap={}, review={}, inserted={}",
                rankSlopes.size(), fanSlopes.size(), soldoutRaws.size(), snapSlopes.size(), reviewRaws.size(), scores.size());
        return scores.size();
    }

    /**
     * 순수 계산부 (DB 비의존, 단위 테스트 가능).
     * 입력 맵의 key 는 brand_id, value 는 각 지표의 raw 값.
     */
    public List<BrandScore> compute(
            Map<Long, Double> rankSlopes,
            Map<Long, Double> fanSlopes,
            Map<Long, Double> soldoutRaws,
            Map<Long, Double> snapSlopes,
            Map<Long, Double> reviewRaws,
            LocalDateTime scoredAt) {

        Map<Long, Double> rankPct = toPercentiles(rankSlopes);
        Map<Long, Double> fanPct = toPercentiles(fanSlopes);
        Map<Long, Double> soldoutPct = toPercentiles(soldoutRaws);
        Map<Long, Double> snapPct = toPercentiles(snapSlopes);
        Map<Long, Double> reviewPct = toPercentiles(reviewRaws);

        ScoringConfig.Weights w = config.weights();

        Set<Long> candidates = new LinkedHashSet<>();
        candidates.addAll(rankSlopes.keySet());
        candidates.addAll(fanSlopes.keySet());
        candidates.addAll(soldoutRaws.keySet());
        candidates.addAll(snapSlopes.keySet());
        candidates.addAll(reviewRaws.keySet());

        List<BrandScore> result = new ArrayList<>();
        for (Long brandId : candidates) {
            Double rp = rankPct.get(brandId);
            Double fp = fanPct.get(brandId);
            Double sp = soldoutPct.get(brandId);
            Double np = snapPct.get(brandId);
            Double rvp = reviewPct.get(brandId);

            // 지표가 하나도 없으면 신뢰도 없는 점수 → INSERT 안 함
            if (rp == null && fp == null && sp == null && np == null && rvp == null) {
                continue;
            }

            double weightedSum = 0.0;
            double weightTotal = 0.0;
            if (rp != null) {
                weightedSum += rp * w.rank();
                weightTotal += w.rank();
            }
            if (fp != null) {
                weightedSum += fp * w.fan();
                weightTotal += w.fan();
            }
            if (sp != null) {
                weightedSum += sp * w.soldout();
                weightTotal += w.soldout();
            }
            if (np != null) {
                weightedSum += np * w.snap();
                weightTotal += w.snap();
            }
            if (rvp != null) {
                weightedSum += rvp * w.reviewVelocity();
                weightTotal += w.reviewVelocity();
            }
            double total = weightTotal > 0 ? weightedSum / weightTotal : 0.0;

            // 결손 지표의 per-metric 점수는 NOT NULL 컬럼이므로 0.00 으로 저장.
            // (total 은 위에서 재정규화로 이미 제외 처리됨)
            result.add(new BrandScore(
                    brandId,
                    score(rp),
                    score(fp),
                    score(sp),
                    score(np),
                    score(rvp),
                    score(total),
                    scoredAt));
        }
        return result;
    }

    /**
     * 모집단 내 mid-rank 백분위(0~100). O(n log n).
     * pct = (lo + (hi-lo)/2.0 + 0.5) / n * 100. 동점은 인덱스 구간으로 처리하여
     * double == 비교를 사용하지 않으므로 부동소수점 오판 위험이 없다.
     */
    private static Map<Long, Double> toPercentiles(Map<Long, Double> values) {
        Map<Long, Double> out = new HashMap<>();
        int n = values.size();
        if (n == 0) {
            return out;
        }

        // 값 기준 오름차순 정렬
        List<Map.Entry<Long, Double>> sorted = new ArrayList<>(values.entrySet());
        sorted.sort(Comparator.comparingDouble(Map.Entry::getValue));

        // 동점 구간 [lo, hi] 을 한 번의 순회로 계산
        int i = 0;
        while (i < n) {
            double v = sorted.get(i).getValue();
            int lo = i;
            // 같은 값이 이어지는 구간 끝 탐색
            while (i < n && sorted.get(i).getValue() == v) {
                i++;
            }
            int hi = i - 1; // 동점 구간: [lo, hi]
            double pct = (lo + (hi - lo) / 2.0 + 0.5) / n * 100.0;
            for (int j = lo; j <= hi; j++) {
                out.put(sorted.get(j).getKey(), pct);
            }
        }
        return out;
    }

    /** [0,100] 클램프 후 소수 2자리 반올림. null 은 0.00 으로. */
    private static BigDecimal score(Double v) {
        double d = v == null ? 0.0 : Math.max(0.0, Math.min(100.0, v));
        return BigDecimal.valueOf(d).setScale(2, RoundingMode.HALF_UP);
    }
}
