package com.musinsa.processor.controller;

import com.musinsa.processor.config.ScoringConfig;
import com.musinsa.processor.dto.BrandTrendDto;
import com.musinsa.processor.dto.HotBrandDto;
import com.musinsa.processor.repository.BrandScoreRepository;
import com.musinsa.processor.service.ScoringService;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import org.springframework.data.domain.PageRequest;
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

    private final BrandScoreRepository scoreRepository;
    private final ScoringConfig config;
    private final ScoringService scoringService;

    public BrandController(BrandScoreRepository scoreRepository, ScoringConfig config, ScoringService scoringService) {
        this.scoreRepository = scoreRepository;
        this.config = config;
        this.scoringService = scoringService;
    }

    /** 가장 최근 배치 기준 핫 브랜드 상위 limit 개. */
    @GetMapping("/hot")
    public List<HotBrandDto> hot(@RequestParam(required = false) Integer limit) {
        int effectiveLimit = limit != null ? limit : config.hotBrandsLimit();
        return scoreRepository.findHotBrands(PageRequest.of(0, effectiveLimit));
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
}
