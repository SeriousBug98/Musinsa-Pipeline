package com.musinsa.processor.dto;

/**
 * review_velocity 집계 native 쿼리 수령용 인터페이스 프로젝션.
 */
public interface ReviewVelocityRawDto {

    Long getBrandId();

    Double getReviewVelocityRaw();

    Long getProductCount();
}
