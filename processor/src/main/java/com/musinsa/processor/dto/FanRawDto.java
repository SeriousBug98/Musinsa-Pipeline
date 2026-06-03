package com.musinsa.processor.dto;

/**
 * fan_growth 집계 native 쿼리 수령용 인터페이스 프로젝션.
 */
public interface FanRawDto {

    Long getBrandId();

    Double getFanSlope();

    Long getDaysObserved();
}
