package com.musinsa.processor.scheduler;

import com.musinsa.processor.service.ScoringService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

/**
 * batch 프로필: 스코어링 1회 실행 후 종료 (GitHub Actions cron용).
 * 실패 시 예외가 그대로 전파돼 비정상 종료(exit 1)된다.
 * 스케줄러 스레드가 JVM을 붙잡지 않도록 성공 시에도 명시적으로 exit 한다.
 */
@Component
@Profile("batch")
public class ScoringBatchRunner implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(ScoringBatchRunner.class);

    private final ScoringService scoringService;
    private final ConfigurableApplicationContext context;

    public ScoringBatchRunner(ScoringService scoringService, ConfigurableApplicationContext context) {
        this.scoringService = scoringService;
        this.context = context;
    }

    @Override
    public void run(ApplicationArguments args) {
        int inserted = scoringService.run();
        log.info("batch scoring done: inserted={}", inserted);
        System.exit(SpringApplication.exit(context));
    }
}
