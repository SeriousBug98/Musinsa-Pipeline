package com.musinsa.processor.dto;

/**
 * rank_change 집계 native 쿼리 수령용 인터페이스 프로젝션.
 * 컬럼 alias(brand_id, rank_slope, days_observed)와 getter 이름이 매핑된다.
 */
public interface RankRawDto {

    Long getBrandId();

    Double getRankSlope();

    Long getDaysObserved();
}
