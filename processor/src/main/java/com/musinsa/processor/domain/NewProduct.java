package com.musinsa.processor.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

/**
 * new_products 테이블 (읽기 전용). 신상품 품절 현황.
 */
@Entity
@Table(name = "new_products")
public class NewProduct {

    @Id
    private Long id;

    @Column(name = "brand_id", nullable = false)
    private Long brandId;

    @Column(name = "product_id", nullable = false)
    private String productId;

    @Column(name = "product_name", nullable = false)
    private String productName;

    @Column(name = "category_code", nullable = false)
    private String categoryCode;

    @Column(name = "price")
    private Integer price;

    @Column(name = "final_price")
    private Integer finalPrice;

    @Column(name = "is_sold_out", nullable = false)
    private boolean soldOut;

    @Column(name = "first_seen_at", nullable = false)
    private LocalDateTime firstSeenAt;

    @Column(name = "sold_out_at")
    private LocalDateTime soldOutAt;

    protected NewProduct() {
    }

    public Long getId() {
        return id;
    }

    public Long getBrandId() {
        return brandId;
    }

    public String getProductId() {
        return productId;
    }

    public String getProductName() {
        return productName;
    }

    public String getCategoryCode() {
        return categoryCode;
    }

    public Integer getPrice() {
        return price;
    }

    public Integer getFinalPrice() {
        return finalPrice;
    }

    public boolean isSoldOut() {
        return soldOut;
    }

    public LocalDateTime getFirstSeenAt() {
        return firstSeenAt;
    }

    public LocalDateTime getSoldOutAt() {
        return soldOutAt;
    }
}
