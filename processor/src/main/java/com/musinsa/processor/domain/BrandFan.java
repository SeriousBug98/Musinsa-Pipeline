package com.musinsa.processor.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

/**
 * brand_fans 테이블 (읽기 전용). 팬수 스냅샷.
 */
@Entity
@Table(name = "brand_fans")
public class BrandFan {

    @Id
    private Long id;

    @Column(name = "brand_id", nullable = false)
    private Long brandId;

    @Column(name = "fan_count", nullable = false)
    private Integer fanCount;

    @Column(name = "collected_at", nullable = false)
    private LocalDateTime collectedAt;

    protected BrandFan() {
    }

    public Long getId() {
        return id;
    }

    public Long getBrandId() {
        return brandId;
    }

    public Integer getFanCount() {
        return fanCount;
    }

    public LocalDateTime getCollectedAt() {
        return collectedAt;
    }
}
