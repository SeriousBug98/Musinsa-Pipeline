package com.musinsa.processor.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.musinsa.processor.repository.BrandScoreRepository;
import java.time.LocalDateTime;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * 실 PostgreSQL 통합 테스트. DB_USER 환경변수가 있을 때만 실행된다(게이트).
 * 실행 전: 크롤러 스키마 적용 + 일부 데이터 적재, DB_* 환경변수 설정.
 *
 * 운영용 수동 트리거를 두지 않는 대신, INSERT 경로를 이 테스트로 검증한다.
 */
@SpringBootTest
@EnabledIfEnvironmentVariable(named = "DB_USER", matches = ".+")
class ScoringServiceIntegrationTest {

    @Autowired
    private ScoringService scoringService;

    @Autowired
    private BrandScoreRepository scoreRepository;

    @Test
    void runInsertsBrandScores() {
        LocalDateTime startedAt = LocalDateTime.now();
        long before = scoreRepository.count();

        int inserted = scoringService.run();

        long after = scoreRepository.count();
        assertThat(inserted).isGreaterThanOrEqualTo(0);
        assertThat(after - before).isEqualTo(inserted);

        if (inserted > 0) {
            // 이번 run 의 행이 실제로 적재됐는지 (append-only 이므로 신규 행만 증가)
            assertThat(after).isGreaterThan(before);
            assertThat(scoreRepository.findTrend(
                    scoreRepository.findAll().get(0).getBrandId(), startedAt)).isNotNull();
        }
    }
}
