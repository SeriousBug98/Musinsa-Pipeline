package com.musinsa.processor.dto;

/**
 * snap_buzz 집계 native 쿼리 수령용 인터페이스 프로젝션.
 * RankRawDto 와 동일 형태 — alias("brandId", "snapSlope", "daysObserved")와 getter 이름이 매핑된다.
 * daysObserved 는 14일 창 중 실제 등장한 날(raw_buzz > 0)만 센 값이다.
 */
public interface SnapRawDto {

    Long getBrandId();

    Double getSnapSlope();

    Long getDaysObserved();
}
