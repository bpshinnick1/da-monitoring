CREATE OR REPLACE VIEW vw_submission_timeliness AS
SELECT
    ms.coverholder_id,
    ch.name                                         AS coverholder_name,
    ms.report_month,
    ms.month_end_date,
    ms.submission_date,
    ms.days_from_month_end,
    ms.on_time,
    CASE
        WHEN ms.days_from_month_end > 15 THEN 'LATE'
        ELSE 'ON TIME'
    END                                             AS timeliness_status,
    COUNT(CASE WHEN NOT ms.on_time THEN 1 END)
        OVER (PARTITION BY ms.coverholder_id)       AS total_late_submissions
FROM monthly_submissions ms
JOIN coverholders ch ON ch.coverholder_id = ms.coverholder_id
ORDER BY ms.coverholder_id, ms.report_month;