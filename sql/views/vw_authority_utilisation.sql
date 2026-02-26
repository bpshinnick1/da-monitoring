CREATE OR REPLACE VIEW vw_authority_utilisation AS
SELECT
    p.coverholder_id,
    ch.name                                         AS coverholder_name,
    p.underwriting_year,
    ch.authority_limit,
    SUM(p.premium)                                  AS cumulative_premium,
    ROUND((SUM(p.premium) / ch.authority_limit) * 100, 1) AS utilisation_pct,
    CASE
        WHEN (SUM(p.premium) / ch.authority_limit) >= 0.95 THEN 'BREACH'
        WHEN (SUM(p.premium) / ch.authority_limit) >= 0.80 THEN 'WARNING'
        ELSE 'OK'
    END                                             AS utilisation_status
FROM premium_bordereaux p
JOIN coverholders ch ON ch.coverholder_id = p.coverholder_id
GROUP BY p.coverholder_id, ch.name, p.underwriting_year, ch.authority_limit
ORDER BY p.coverholder_id, p.underwriting_year;