package com.musinsa.processor.dto;

import java.time.LocalDateTime;

/**
 * GET /brands/emerging 응답 항목 — 네이티브 쿼리 인터페이스 프로젝션.
 * brands 테이블에 없는(brand_id=NULL) 신흥 브랜드 후보.
 * 매칭은 한글 브랜드명 정확 일치라 미매칭 중 일부는 표기 흔들림일 수 있음 (Phase 2 퍼지 매칭 예정).
 */
public interface EmergingBrandDto {

    String getBrandName();

    Long getTotalMentions();

    Integer getBestRank();

    Long getLikeSum();

    LocalDateTime getLastSeenAt();

    Long getDaysSeen();
}
