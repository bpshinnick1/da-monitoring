-- ── Drop tables if rebuilding from scratch ─────────────────────────────────
DROP TABLE IF EXISTS flags_log CASCADE;
DROP TABLE IF EXISTS monthly_submissions CASCADE;
DROP TABLE IF EXISTS claims_bordereaux CASCADE;
DROP TABLE IF EXISTS premium_bordereaux CASCADE;
DROP TABLE IF EXISTS coverholders CASCADE;

-- ── Coverholders reference table ───────────────────────────────────────────
CREATE TABLE coverholders (
    coverholder_id      VARCHAR(10)     PRIMARY KEY,
    name                VARCHAR(100)    NOT NULL,
    class_of_business   VARCHAR(50)     NOT NULL,
    territory           VARCHAR(50)     NOT NULL,
    authority_limit     NUMERIC(12,2)   NOT NULL,
    baa_start_date      DATE            NOT NULL DEFAULT '2024-01-01'
);

INSERT INTO coverholders VALUES
    ('CH001', 'Avonbridge Underwriting',    'Commercial Property',   'UK-wide',            2000000.00, '2024-01-01'),
    ('CH002', 'Meridian Risk Solutions',    'EL/PL Liability',       'UK-wide',            1500000.00, '2024-01-01'),
    ('CH003', 'Fortis Professional Risks',  'Professional Indemnity','UK-wide',            1000000.00, '2024-01-01'),
    ('CH004', 'Southgate Property Partners','Commercial Property',   'South East',          500000.00, '2024-01-01'),
    ('CH005', 'Ironclad Construction Risks','EL/PL Liability',       'Construction sector', 750000.00, '2024-01-01');

-- ── Premium bordereaux ─────────────────────────────────────────────────────
CREATE TABLE premium_bordereaux (
    policy_ref          VARCHAR(30)     PRIMARY KEY,
    coverholder_id      VARCHAR(10)     NOT NULL REFERENCES coverholders(coverholder_id),
    coverholder_name    VARCHAR(100),
    inception_date      DATE            NOT NULL,
    expiry_date         DATE            NOT NULL,
    class_of_business   VARCHAR(50),
    insured_name        VARCHAR(150),
    postcode            VARCHAR(10),
    premium             NUMERIC(10,2)   NOT NULL,
    sum_insured         NUMERIC(14,2),
    underwriting_year   SMALLINT,
    bound_month         VARCHAR(7)      -- format: YYYY-MM
);

-- ── Claims bordereaux ──────────────────────────────────────────────────────
CREATE TABLE claims_bordereaux (
    claim_ref           VARCHAR(30)     PRIMARY KEY,
    policy_ref          VARCHAR(30)     REFERENCES premium_bordereaux(policy_ref),
    coverholder_id      VARCHAR(10)     NOT NULL REFERENCES coverholders(coverholder_id),
    coverholder_name    VARCHAR(100),
    class_of_business   VARCHAR(50),
    date_of_loss        DATE,
    date_reported       DATE,
    reserve_amount      NUMERIC(12,2),
    paid_amount         NUMERIC(12,2),
    incurred            NUMERIC(12,2),
    claim_status        VARCHAR(20),
    report_month        VARCHAR(7)
);

-- ── Monthly submissions ────────────────────────────────────────────────────
CREATE TABLE monthly_submissions (
    id                  SERIAL          PRIMARY KEY,
    coverholder_id      VARCHAR(10)     NOT NULL REFERENCES coverholders(coverholder_id),
    coverholder_name    VARCHAR(100),
    report_month        VARCHAR(7)      NOT NULL,
    month_end_date      DATE,
    submission_date     DATE,
    days_from_month_end INTEGER,
    on_time             BOOLEAN,
    UNIQUE (coverholder_id, report_month)
);

-- ── Flags log (written to by monitoring engine) ────────────────────────────
CREATE TABLE flags_log (
    id                  SERIAL          PRIMARY KEY,
    run_date            TIMESTAMP       DEFAULT NOW(),
    coverholder_id      VARCHAR(10)     REFERENCES coverholders(coverholder_id),
    coverholder_name    VARCHAR(100),
    flag_type           VARCHAR(50),
    severity            VARCHAR(10),    -- High / Medium / Low
    detail              TEXT,
    period              VARCHAR(7)      -- YYYY-MM where relevant
);