CREATE OR REPLACE VIEW vw_geographic_compliance AS
SELECT
    p.policy_ref,
    p.coverholder_id,
    ch.name                 AS coverholder_name,
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
    END                     AS is_breach
FROM premium_bordereaux p
JOIN coverholders ch ON ch.coverholder_id = p.coverholder_id
WHERE p.coverholder_id = 'CH004'
ORDER BY is_breach DESC, p.bound_month;