package com.musinsa.processor.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

/**
 * brands 테이블. Python 크롤러가 소유하며 여기서는 읽기 전용으로만 사용한다.
 */
@Entity
@Table(name = "brands")
public class Brand {

    @Id
    private Long id;

    @Column(name = "musinsa_brand_id", nullable = false, unique = true)
    private String musinsaBrandId;

    @Column(nullable = false)
    private String name;

    @Column(name = "english_name")
    private String englishName;

    @Column(name = "link_url")
    private String linkUrl;

    @Column(name = "is_tracked", nullable = false)
    private boolean tracked;

    @Column(name = "is_active", nullable = false)
    private boolean active;

    @Column(name = "joined_at", nullable = false)
    private LocalDateTime joinedAt;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    protected Brand() {
    }

    public Long getId() {
        return id;
    }

    public String getMusinsaBrandId() {
        return musinsaBrandId;
    }

    public String getName() {
        return name;
    }

    public String getEnglishName() {
        return englishName;
    }

    public String getLinkUrl() {
        return linkUrl;
    }

    public boolean isTracked() {
        return tracked;
    }

    public boolean isActive() {
        return active;
    }

    public LocalDateTime getJoinedAt() {
        return joinedAt;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
}
