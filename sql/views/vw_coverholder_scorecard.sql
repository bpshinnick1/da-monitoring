DROP VIEW IF EXISTS vw_coverholder_scorecard CASCADE;

CREATE VIEW vw_coverholder_scorecard AS
SELECT * FROM (
    WITH latest_lr AS (
        SELECT DISTINCT ON (coverholder_id)
            coverholder_id,
            rolling_3m_loss_ratio AS current_rolling_lr
        FROM vw_monthly_loss_ratios
        ORDER BY coverholder_id, bound_month DESC
    ),
    latest_util AS (
        SELECT DISTINCT ON (coverholder_id)
            coverholder_id,
            utilisation_pct,
            utilisation_status
        FROM vw_authority_utilisation
        ORDER BY coverholder_id, underwriting_year DESC
    ),
    geo_flags AS (
        SELECT coverholder_id, COUNT(*) AS geo_breach_count
        FROM vw_geographic_compliance
        WHERE is_breach = TRUE
        GROUP BY coverholder_id
    ),
    late_subs AS (
        SELECT coverholder_id, COUNT(*) AS late_submission_count
        FROM vw_submission_timeliness
        WHERE timeliness_status = 'LATE'
        GROUP BY coverholder_id
    )
    SELECT
        ch.coverholder_id,
        ch.name AS coverholder_name,
        ch.class_of_business,
        ch.territory,
        ch.authority_limit,
        ROUND(lr.current_rolling_lr::NUMERIC, 1) AS rolling_loss_ratio_pct,
        u.utilisation_pct,
        u.utilisation_status,
        COALESCE(g.geo_breach_count, 0) AS geo_breach_count,
        COALESCE(ls.late_submission_count, 0) AS late_submission_count,
        CASE
            WHEN lr.current_rolling_lr > 75
              OR u.utilisation_status = 'BREACH'
              OR COALESCE(g.geo_breach_count, 0) > 0
            THEN 'RED'
            WHEN lr.current_rolling_lr > 65
              OR u.utilisation_status = 'WARNING'
              OR COALESCE(ls.late_submission_count, 0) > 3
            THEN 'AMBER'
            ELSE 'GREEN'
        END AS rag_status
    FROM coverholders ch
    LEFT JOIN latest_lr lr ON lr.coverholder_id = ch.coverholder_id
    LEFT JOIN latest_util u ON u.coverholder_id = ch.coverholder_id
    LEFT JOIN geo_flags g ON g.coverholder_id = ch.coverholder_id
    LEFT JOIN late_subs ls ON ls.coverholder_id = ch.coverholder_id
) sub
ORDER BY CASE rag_status WHEN 'RED' THEN 1 WHEN 'AMBER' THEN 2 ELSE 3 END;