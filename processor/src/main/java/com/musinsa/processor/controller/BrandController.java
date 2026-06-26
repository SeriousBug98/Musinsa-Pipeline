package com.musinsa.processor.controller;

import com.musinsa.processor.config.ScoringConfig;
import com.musinsa.processor.dto.BrandManagementProjection;
import com.musinsa.processor.dto.BrandTrendDto;
import com.musinsa.processor.dto.EmergingBrandDto;
import com.musinsa.processor.dto.RisingBrandDto;
import com.musinsa.processor.repository.BrandRepository;
import com.musinsa.processor.repository.BrandScoreRepository;
import com.musinsa.processor.repository.BrandSnapMentionRepository;
import com.musinsa.processor.service.ScoringService;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import org.springframework.data.domain.PageRequest;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/brands")
public class BrandController {

    private static final int TREND_DAYS = 30;
    private static final int EMERGING_DAYS_DEFAULT = 7;

    private final BrandScoreRepository scoreRepository;
    private final BrandRepository brandRepository;
    private final BrandSnapMentionRepository snapMentionRepository;
    private final ScoringConfig config;
    private final ScoringService scoringService;

    public BrandController(
            BrandScoreRepository scoreRepository,
            BrandRepository brandRepository,
            BrandSnapMentionRepository snapMentionRepository,
            ScoringConfig config,
            ScoringService scoringService) {
        this.scoreRepository = scoreRepository;
        this.brandRepository = brandRepository;
        this.snapMentionRepository = snapMentionRepository;
        this.config = config;
        this.scoringService = scoringService;
    }

    /**
     * 가장 최근 배치 기준 모멘텀(상승세) 상위 limit 개.
     * rank/fan/soldout 기울기를 가중합한 점수 기준 — "현재 인기" 브랜드가 아니라 "지금 올라오는 중인" 브랜드.
     */
    @GetMapping("/rising")
    public List<RisingBrandDto> rising(@RequestParam(required = false) Integer limit) {
        int effectiveLimit = limit != null ? limit : config.risingBrandsLimit();
        return scoreRepository.findRisingBrands(PageRequest.of(0, effectiveLimit));
    }

    /** 특정 브랜드의 최근 30일 점수 추이. */
    @GetMapping("/{id}/trend")
    public List<BrandTrendDto> trend(@PathVariable Long id) {
        LocalDateTime since = LocalDateTime.now().minusDays(TREND_DAYS);
        return scoreRepository.findTrend(id, since);
    }

    /** 스코어링 수동 트리거. */
    @PostMapping("/scoring/run")
    public Map<String, Integer> scoringRun() {
        int inserted = scoringService.run();
        return Map.of("inserted", inserted);
    }

    /**
     * 신흥 브랜드 후보 조회 — brands 테이블 미매칭(brand_id=NULL) 스냅 브랜드.
     * 최근 days 일간 누적 mention_count 내림차순. 기본 7일, 기본 limit=risingBrandsLimit.
     */
    @GetMapping("/emerging")
    public List<EmergingBrandDto> emerging(
            @RequestParam(required = false) Integer limit,
            @RequestParam(required = false) Integer days) {
        int effectiveLimit = limit != null ? limit : config.risingBrandsLimit();
        int effectiveDays = days != null ? days : EMERGING_DAYS_DEFAULT;
        LocalDateTime since = LocalDateTime.now().minusDays(effectiveDays);
        return snapMentionRepository.findEmergingBrands(since, PageRequest.of(0, effectiveLimit));
    }

    /** 관리 페이지용 전체 브랜드 목록 (최신 점수 포함). */
    @GetMapping
    public List<BrandManagementProjection> allBrands() {
        return brandRepository.findAllWithLatestScore();
    }

    /** tracked 등록. */
    @PostMapping("/{id}/track")
    public void track(@PathVariable Long id) {
        brandRepository.updateTracked(id, true);
    }

    /** tracked 해제. */
    @DeleteMapping("/{id}/track")
    public void untrack(@PathVariable Long id) {
        brandRepository.updateTracked(id, false);
    }
}
