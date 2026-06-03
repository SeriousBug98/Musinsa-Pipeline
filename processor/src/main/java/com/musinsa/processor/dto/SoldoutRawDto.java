package com.musinsa.processor.dto;

/**
 * soldout_speed 집계 native 쿼리 수령용 인터페이스 프로젝션.
 */
public interface SoldoutRawDto {

    Long getBrandId();

    Double getSoldoutRaw();

    Long getProductCount();
}
