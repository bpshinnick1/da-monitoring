-- View 1: Monthly loss ratios
CREATE OR REPLACE VIEW vw_monthly_loss_ratios AS
WITH monthly AS (
    SELECT
        p.coverholder_id,
        p.bound_month,
        SUM(p.premium)               AS earned_premium,
        COALESCE(SUM(c.incurred), 0) AS incurred_claims
    FROM premium_bordereaux p
    LEFT JOIN claims_bordereaux c
        ON  c.coverholder_id = p.coverholder_id
        AND c.report_month   = p.bound_month
    GROUP BY p.coverholder_id, p.bound_month
),
with_ratio AS (
    SELECT
        m.*,
        ch.name AS coverholder_name,
        CASE WHEN earned_premium > 0
             THEN ROUND((incurred_claims / earned_premium) * 100, 1)
             ELSE NULL END AS loss_ratio_pct,
        AVG(
            CASE WHEN earned_premium > 0
                 THEN (incurred_claims / earned_premium) * 100
                 ELSE NULL END
        ) OVER (
            PARTITION BY m.coverholder_id
            ORDER BY m.bound_month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS rolling_3m_loss_ratio
    FROM monthly m
    JOIN coverholders ch ON ch.coverholder_id = m.coverholder_id
)
SELECT
    coverholder_id,
    coverholder_name,
    bound_month,
    earned_premium,
    incurred_claims,
    ROUND(loss_ratio_pct, 1) AS loss_ratio_pct,
    ROUND(rolling_3m_loss_ratio::NUMERIC, 1) AS rolling_3m_loss_ratio
FROM with_ratio
ORDER BY coverholder_id, bound_month;

-- View 2: Authority utilisation
CREATE OR REPLACE VIEW vw_authority_utilisation AS
SELECT
    p.coverholder_id,
    ch.name AS coverholder_name,
    p.underwriting_year,
    ch.authority_limit,
    SUM(p.premium) AS cumulative_premium,
    ROUND((SUM(p.premium) / ch.authority_limit) * 100, 1) AS utilisation_pct,
    CASE
        WHEN (SUM(p.premium) / ch.authority_limit) >= 0.95 THEN 'BREACH'
        WHEN (SUM(p.premium) / ch.authority_limit) >= 0.80 THEN 'WARNING'
        ELSE 'OK'
    END AS utilisation_status
FROM premium_bordereaux p
JOIN coverholders ch ON ch.coverholder_id = p.coverholder_id
GROUP BY p.coverholder_id, ch.name, p.underwriting_year, ch.authority_limit
ORDER BY p.coverholder_id, p.underwriting_year;

-- View 3: Geographic compliance
CREATE OR REPLACE VIEW vw_geographic_compliance AS
SELECT
    p.policy_ref,
    p.coverholder_id,
    ch.name AS coverholder_name,
    p.insured_name,
    p.postcode,
    p.inception_date,
    p.premium,
    p.bound_month,
    CASE
        WHEN p.coverholder_id = 'CH004'
         AND p.postcode NOT SIMILAR TO
            '(SE|SW|E1|EC|WC|W1|N1|NW|BN|CT|ME|TN|RH|GU|KT|SM|SL|RG|OX|HP|AL|SG|CM|SS|BR|CR|DA|EN|HA|IG|TW|UB)%'
        THEN TRUE
        ELSE FALSE
    END AS is_breach
FROM premium_bordereaux p
JOIN coverholders ch ON ch.coverholder_id = p.coverholder_id
WHERE p.coverholder_id = 'CH004'
ORDER BY is_breach DESC, p.bound_month;

-- View 4: Submission timeliness
CREATE OR REPLACE VIEW vw_submission_timeliness AS
SELECT
    ms.coverholder_id,
    ch.name AS coverholder_name,
    ms.report_month,
    ms.month_end_date,
    ms.submission_date,
    ms.days_from_month_end,
    ms.on_time,
    CASE
        WHEN ms.days_from_month_end > 15 THEN 'LATE'
        ELSE 'ON TIME'
    END AS timeliness_status,
    COUNT(CASE WHEN NOT ms.on_time THEN 1 END)
        OVER (PARTITION BY ms.coverholder_id) AS total_late_submissions
FROM monthly_submissions ms
JOIN coverholders ch ON ch.coverholder_id = ms.coverholder_id
ORDER BY ms.coverholder_id, ms.report_month;

-- View 5: Coverholder scorecard
CREATE OR REPLACE VIEW vw_coverholder_scorecard AS
WITH latest_lr AS (
    SELECT DISTINCT ON (coverholder_id)
        coverholder_id,
        rolling_3m_loss_ratio AS current_rolling_lr,
        bound_month           AS latest_month
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
    ch.name                                     AS coverholder_name,
    ch.class_of_business,
    ch.territory,
    ch.authority_limit,
    ROUND(lr.current_rolling_lr::NUMERIC, 1)    AS rolling_loss_ratio_pct,
    u.utilisation_pct,
    u.utilisation_status,
    COALESCE(g.geo_breach_count, 0)             AS geo_breach_count,
    COALESCE(ls.late_submission_count, 0)       AS late_submission_count,
    CASE
        WHEN lr.current_rolling_lr > 75
          OR u.utilisation_status = 'BREACH'
          OR COALESCE(g.geo_breach_count, 0) > 0     THEN 'RED'
        WHEN lr.current_rolling_lr > 65
          OR u.utilisation_status = 'WARNING'
          OR COALESCE(ls.late_submission_count, 0) > 3 THEN 'AMBER'
        ELSE 'GREEN'
    END AS rag_status
FROM coverholders ch
LEFT JOIN latest_lr  lr ON lr.coverholder_id = ch.coverholder_id
LEFT JOIN latest_util u  ON u.coverholder_id  = ch.coverholder_id
LEFT JOIN geo_flags   g  ON g.coverholder_id  = ch.coverholder_id
LEFT JOIN late_subs   ls ON ls.coverholder_id = ch.coverholder_id
ORDER BY
    CASE rag_status WHEN 'RED' THEN 1 WHEN 'AMBER' THEN 2 ELSE 3 END;