CREATE OR REPLACE VIEW vw_monthly_loss_ratios AS
WITH monthly_claims AS (
    SELECT
        coverholder_id,
        report_month,
        SUM(reserve_amount) AS incurred_claims
    FROM claims_bordereaux
    GROUP BY coverholder_id, report_month
),
monthly_premium AS (
    SELECT
        coverholder_id,
        bound_month,
        SUM(premium) AS earned_premium
    FROM premium_bordereaux
    GROUP BY coverholder_id, bound_month
),
combined AS (
    SELECT
        mp.coverholder_id,
        mp.bound_month,
        mp.earned_premium,
        COALESCE(mc.incurred_claims, 0) AS incurred_claims
    FROM monthly_premium mp
    LEFT JOIN monthly_claims mc
        ON  mc.coverholder_id = mp.coverholder_id
        AND mc.report_month   = mp.bound_month
)
SELECT
    c.coverholder_id,
    ch.name                                                          AS coverholder_name,
    c.bound_month,
    c.earned_premium,
    c.incurred_claims,
    ROUND((c.incurred_claims / NULLIF(c.earned_premium,0)) * 100, 1) AS loss_ratio_pct,
    ROUND(AVG((c.incurred_claims / NULLIF(c.earned_premium,0)) * 100)
        OVER (
            PARTITION BY c.coverholder_id
            ORDER BY c.bound_month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        )::NUMERIC, 1)                                               AS rolling_3m_loss_ratio
FROM combined c
JOIN coverholders ch ON ch.coverholder_id = c.coverholder_id
ORDER BY c.coverholder_id, c.bound_month;