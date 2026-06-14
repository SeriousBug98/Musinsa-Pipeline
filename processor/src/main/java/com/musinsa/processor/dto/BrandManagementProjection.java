package com.musinsa.processor.dto;

import java.math.BigDecimal;

public interface BrandManagementProjection {
    Long getId();
    String getName();
    String getMusinsaBrandId();
    String getLinkUrl();
    boolean getIsTracked();
    BigDecimal getTotalScore();
}
