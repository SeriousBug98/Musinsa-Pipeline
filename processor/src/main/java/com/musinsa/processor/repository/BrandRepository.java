package com.musinsa.processor.repository;

import com.musinsa.processor.domain.Brand;
import com.musinsa.processor.dto.BrandManagementProjection;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;

public interface BrandRepository extends JpaRepository<Brand, Long> {

    @Modifying
    @Transactional
    @Query("UPDATE Brand b SET b.tracked = :tracked WHERE b.id = :id")
    void updateTracked(@Param("id") Long id, @Param("tracked") boolean tracked);

    @Query(value = """
            SELECT b.id, b.name, b.musinsa_brand_id, b.link_url, b.is_tracked,
                   bs.total_score
            FROM brands b
            LEFT JOIN brand_scores bs ON bs.brand_id = b.id
              AND bs.scored_at = (SELECT MAX(scored_at) FROM brand_scores)
            WHERE b.is_active = TRUE
            ORDER BY bs.total_score DESC NULLS LAST
            """, nativeQuery = true)
    List<BrandManagementProjection> findAllWithLatestScore();
}
