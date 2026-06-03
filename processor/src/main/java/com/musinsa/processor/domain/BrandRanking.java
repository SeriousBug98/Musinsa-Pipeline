package com.musinsa.processor.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

/**
 * brand_rankings 테이블 (읽기 전용). 랭킹 스냅샷.
 */
@Entity
@Table(name = "brand_rankings")
public class BrandRanking {

    @Id
    private Long id;

    @Column(name = "brand_id", nullable = false)
    private Long brandId;

    // "rank" 는 SQL 예약어지만 크롤러가 unquoted 로 생성한 컬럼명과 일치시킨다.
    @Column(name = "rank", nullable = false)
    private Integer rank;

    @Column(name = "collected_at", nullable = false)
    private LocalDateTime collectedAt;

    protected BrandRanking() {
    }

    public Long getId() {
        return id;
    }

    public Long getBrandId() {
        return brandId;
    }

    public Integer getRank() {
        return rank;
    }

    public LocalDateTime getCollectedAt() {
        return collectedAt;
    }
}
