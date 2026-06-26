package com.musinsa.processor.repository;

import com.musinsa.processor.domain.BrandSnapMention;
import com.musinsa.processor.dto.EmergingBrandDto;
import com.musinsa.processor.dto.SnapRawDto;
import java.time.LocalDateTime;
import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface BrandSnapMentionRepository extends JpaRepository<BrandSnapMention, Long> {

    /**
     * snap_buzz 집계: 최근 14일간 스냅 UGC 버즈 상승 추세(기울기) — 지수 감쇠 가중 최소제곱(WLS).
     *
     * <p>스냅 랭킹은 하루 단위 변동이 작아(sticky) 단기 slope 신호가 약하다. 이를 보완하기 위해:
     * <ul>
     *   <li>창을 14일로 확대해 느린 추세를 드러낸다.</li>
     *   <li>결측일(스냅에 등장하지 않은 날)을 raw_buzz=0 으로 채운다(zero-fill).
     *       → 신규 진입 브랜드(0에서 솟아오름)가 자동으로 높은 기울기를 받아 "뜨는 신호"가 포착된다.</li>
     * </ul>
     *
     * <p>raw_buzz = mention_count × (101 − best_rank):
     * 상위 스냅(best_rank 낮음)에 등장할수록 버즈 값이 크다 (1위=100배 가중, 100위=1배).
     *
     * <p>WLS 공식: (Σw·Σwxy - Σwx·Σwy) / (Σw·Σwxx - (Σwx)²)
     * (BrandRankingRepository.aggregateRankChange 와 동일 구조)
     *
     * <p>HAVING 절은 14일 달력 중 "실제 등장일(raw_buzz>0)" 기준으로 필터한다.
     * 0채움으로 인해 count(*) 는 항상 14이므로, FILTER(WHERE raw_buzz > 0) 로 구분.
     */
    @Query(value = """
            WITH days AS (
                SELECT generate_series(
                    date_trunc('day', NOW() - INTERVAL '13 days'),
                    date_trunc('day', NOW()),
                    INTERVAL '1 day'
                ) AS d
            ),
            actual AS (
                SELECT brand_id,
                       date_trunc('day', collected_at)              AS d,
                       mention_count * (101 - best_rank)            AS raw_buzz
                FROM brand_snap_mentions
                WHERE collected_at >= NOW() - INTERVAL '14 days'
                  AND brand_id IS NOT NULL
            ),
            brand_days AS (
                SELECT DISTINCT brand_id FROM actual
            ),
            filled AS (
                SELECT bd.brand_id,
                       dd.d,
                       COALESCE(a.raw_buzz, 0)                      AS raw_buzz
                FROM brand_days bd
                CROSS JOIN days dd
                LEFT JOIN actual a ON a.brand_id = bd.brand_id AND a.d = dd.d
            ),
            weighted AS (
                SELECT brand_id,
                       ln(raw_buzz + 1)                                                     AS y,
                       EXTRACT(EPOCH FROM d) / 86400.0                                      AS x,
                       EXP(-:decayLambda * EXTRACT(EPOCH FROM (NOW() - d)) / 86400.0)      AS w,
                       raw_buzz
                FROM filled
            )
            SELECT
                brand_id                                                                    AS "brandId",
                (SUM(w) * SUM(w*x*y) - SUM(w*x) * SUM(w*y))
                    / NULLIF(SUM(w) * SUM(w*x*x) - SUM(w*x) * SUM(w*x), 0)                AS "snapSlope",
                count(*) FILTER (WHERE raw_buzz > 0)                                        AS "daysObserved"
            FROM weighted
            GROUP BY brand_id
            HAVING count(*) FILTER (WHERE raw_buzz > 0) >= :minSnapDays
            """, nativeQuery = true)
    List<SnapRawDto> aggregateSnapBuzz(
            @Param("minSnapDays") int minSnapDays,
            @Param("decayLambda") double decayLambda);

    /**
     * 신흥 브랜드 후보 조회 — brands 테이블 미매칭(brand_id=NULL) 행만.
     * brand_name 으로 묶어 누적 mention_count 내림차순 정렬.
     * idx_brand_snap_mentions_unmatched partial index 활용.
     *
     * <p>주의: 매칭이 한글 정확 일치라 미매칭 중 일부는 표기 흔들림(영문명/띄어쓰기)일 수 있다.
     */
    @Query(value = """
            SELECT
                brand_name                  AS "brandName",
                SUM(mention_count)          AS "totalMentions",
                MIN(best_rank)              AS "bestRank",
                SUM(snap_like_sum)          AS "likeSum",
                MAX(collected_at)           AS "lastSeenAt",
                COUNT(*)                    AS "daysSeen"
            FROM brand_snap_mentions
            WHERE brand_id IS NULL
              AND collected_at >= :since
            GROUP BY brand_name
            ORDER BY SUM(mention_count) DESC
            """, nativeQuery = true)
    List<EmergingBrandDto> findEmergingBrands(
            @Param("since") LocalDateTime since,
            Pageable pageable);
}
