package com.musinsa.processor.scheduler;

import com.musinsa.processor.service.ScoringService;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 매일 01:00 (Asia/Seoul) 스코어링 실행.
 * 팬수 수집이 자정(00:00)에 완료되므로 그 이후에 돌린다.
 */
@Component
public class ScoringScheduler {

    private final ScoringService scoringService;

    public ScoringScheduler(ScoringService scoringService) {
        this.scoringService = scoringService;
    }

    @Scheduled(cron = "0 0 1 * * *", zone = "Asia/Seoul")
    public void runScoring() {
        scoringService.run();
    }
}
