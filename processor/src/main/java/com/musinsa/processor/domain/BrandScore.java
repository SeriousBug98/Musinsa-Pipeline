package com.musinsa.processor.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * brand_scores 테이블. 이 모듈이 유일하게 쓰기(INSERT)하는 테이블이다. append-only.
 */
@Entity
@Table(name = "brand_scores")
public class BrandScore {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "brand_id", nullable = false)
    private Long brandId;

    @Column(name = "rank_change_score", nullable = false)
    private BigDecimal rankChangeScore;

    @Column(name = "fan_growth_score", nullable = false)
    private BigDecimal fanGrowthScore;

    @Column(name = "soldout_speed_score", nullable = false)
    private BigDecimal soldoutSpeedScore;

    @Column(name = "total_score", nullable = false)
    private BigDecimal totalScore;

    @Column(name = "scored_at", nullable = false)
    private LocalDateTime scoredAt;

    protected BrandScore() {
    }

    public BrandScore(
            Long brandId,
            BigDecimal rankChangeScore,
            BigDecimal fanGrowthScore,
            BigDecimal soldoutSpeedScore,
            BigDecimal totalScore,
            LocalDateTime scoredAt) {
        this.brandId = brandId;
        this.rankChangeScore = rankChangeScore;
        this.fanGrowthScore = fanGrowthScore;
        this.soldoutSpeedScore = soldoutSpeedScore;
        this.totalScore = totalScore;
        this.scoredAt = scoredAt;
    }

    public Long getId() {
        return id;
    }

    public Long getBrandId() {
        return brandId;
    }

    public BigDecimal getRankChangeScore() {
        return rankChangeScore;
    }

    public BigDecimal getFanGrowthScore() {
        return fanGrowthScore;
    }

    public BigDecimal getSoldoutSpeedScore() {
        return soldoutSpeedScore;
    }

    public BigDecimal getTotalScore() {
        return totalScore;
    }

    public LocalDateTime getScoredAt() {
        return scoredAt;
    }
}
