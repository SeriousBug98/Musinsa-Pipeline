package com.musinsa.processor.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

/**
 * brand_snap_mentions 테이블 (읽기 전용).
 * 무신사 스냅 STREET 랭킹 top 100 에서 수집한 브랜드별 UGC 버즈 스냅샷.
 * brand_id 가 NULL 인 행 = brands 테이블 미매칭(신흥 브랜드 후보).
 */
@Entity
@Table(name = "brand_snap_mentions")
public class BrandSnapMention {

    @Id
    private Long id;

    @Column(name = "brand_id")
    private Long brandId;

    @Column(name = "brand_name", nullable = false)
    private String brandName;

    @Column(name = "mention_count", nullable = false)
    private Integer mentionCount;

    @Column(name = "best_rank", nullable = false)
    private Integer bestRank;

    @Column(name = "snap_like_sum")
    private Integer snapLikeSum;

    @Column(name = "snap_view_sum")
    private Integer snapViewSum;

    @Column(name = "top_snap_id")
    private String topSnapId;

    @Column(name = "period", nullable = false)
    private String period;

    @Column(name = "collected_at", nullable = false)
    private LocalDateTime collectedAt;

    protected BrandSnapMention() {
    }

    public Long getId() {
        return id;
    }

    public Long getBrandId() {
        return brandId;
    }

    public String getBrandName() {
        return brandName;
    }

    public Integer getMentionCount() {
        return mentionCount;
    }

    public Integer getBestRank() {
        return bestRank;
    }

    public Integer getSnapLikeSum() {
        return snapLikeSum;
    }

    public Integer getSnapViewSum() {
        return snapViewSum;
    }

    public String getTopSnapId() {
        return topSnapId;
    }

    public String getPeriod() {
        return period;
    }

    public LocalDateTime getCollectedAt() {
        return collectedAt;
    }
}
