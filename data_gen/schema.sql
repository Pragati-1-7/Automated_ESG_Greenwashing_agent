-- data_gen/schema.sql
-- Contract for data/world/world.db (SQLite). mock_sources/ serves ONLY these tables.
-- The benchmark ground truth is NOT in this DB (it lives in data/benchmark/cases.jsonl).
-- All data is synthetic / fictional.

PRAGMA foreign_keys = ON;

CREATE TABLE companies (
    company_id      TEXT PRIMARY KEY,          -- 'CMP-0001'
    cin             TEXT UNIQUE NOT NULL,       -- Indian Corporate Identification Number style
    name            TEXT NOT NULL,
    short_name      TEXT NOT NULL,
    aliases         TEXT NOT NULL,              -- JSON array of strings
    sector          TEXT NOT NULL,
    hq_city         TEXT NOT NULL,
    hq_state        TEXT NOT NULL,
    listing         TEXT NOT NULL,
    market_cap_band TEXT NOT NULL               -- 'Large' | 'Mid' | 'Small'
);

CREATE TABLE facilities (
    facility_id     TEXT PRIMARY KEY,           -- 'FAC-0001'
    company_id      TEXT NOT NULL REFERENCES companies(company_id),
    name            TEXT NOT NULL,
    type            TEXT NOT NULL,
    district        TEXT NOT NULL,
    state           TEXT NOT NULL,
    lat             REAL NOT NULL,
    lon             REAL NOT NULL,
    capacity_value  REAL,
    capacity_unit   TEXT,
    consent_no      TEXT,                       -- SPCB consent-to-operate number
    forest_adjacent INTEGER NOT NULL DEFAULT 0
);

-- SEBI BRSR Core style annual filing. Tier 1.
CREATE TABLE brsr_filings (
    filing_id           TEXT PRIMARY KEY,       -- 'BRSR-CMP-0001-FY2025'
    company_id          TEXT NOT NULL REFERENCES companies(company_id),
    fy                  TEXT NOT NULL,          -- 'FY2020'..'FY2025'
    revenue_cr          REAL NOT NULL,          -- turnover, Rs crore
    scope1_tco2e        REAL NOT NULL,
    scope2_tco2e        REAL NOT NULL,
    ghg_intensity       REAL NOT NULL,          -- (scope1+scope2)/revenue_cr, rounded 1dp
    energy_gj           REAL NOT NULL,
    re_pct              REAL NOT NULL,
    water_withdrawal_kl REAL NOT NULL,
    water_discharge_kl  REAL NOT NULL,
    waste_generated_t   REAL NOT NULL,
    waste_recovered_t   REAL NOT NULL,
    ltifr               REAL NOT NULL,
    fatalities          INTEGER NOT NULL,
    women_wage_pct      REAL NOT NULL,
    msme_sourcing_pct   REAL NOT NULL,
    assurance_type      TEXT NOT NULL,          -- 'none' | 'limited' | 'reasonable'
    assurance_provider  TEXT,
    filed_on            TEXT NOT NULL,          -- ISO date, typically Jul-Sep after FY end
    UNIQUE (company_id, fy)
);

-- Facility-level GHG (EPA GHGRP / Indian PAT style). Tier 1.
CREATE TABLE facility_ghg (
    row_id          TEXT PRIMARY KEY,
    facility_id     TEXT NOT NULL REFERENCES facilities(facility_id),
    fy              TEXT NOT NULL,
    co2_t           REAL NOT NULL,
    ch4_tco2e       REAL NOT NULL,
    n2o_tco2e       REAL NOT NULL,
    total_tco2e     REAL NOT NULL,
    method          TEXT NOT NULL,              -- 'mass balance' | 'emission factor' | 'CEMS'
    verified        INTEGER NOT NULL,
    UNIQUE (facility_id, fy)
);
-- Invariant: sum(total_tco2e) over a company's facilities for a FY == brsr_filings.scope1_tco2e (+/- 0.5%)

-- CPCB OCEMS style exceedance events. Tier 2.
CREATE TABLE ocems_exceedances (
    event_id        TEXT PRIMARY KEY,
    facility_id     TEXT NOT NULL REFERENCES facilities(facility_id),
    date            TEXT NOT NULL,              -- ISO date
    parameter       TEXT NOT NULL,              -- 'PM' | 'SO2' | 'NOx' | 'BOD' | 'COD' | 'TSS'
    limit_value     REAL NOT NULL,
    reading         REAL NOT NULL,              -- > limit_value
    unit            TEXT NOT NULL,              -- 'mg/Nm3' | 'mg/L'
    duration_h      REAL NOT NULL,
    reported_to     TEXT NOT NULL               -- e.g. 'CPCB', 'OSPCB'
);

-- NGT / CPCB / SPCB / SEBI actions. Tier 2.
CREATE TABLE regulatory_actions (
    action_id       TEXT PRIMARY KEY,
    company_id      TEXT NOT NULL REFERENCES companies(company_id),
    facility_id     TEXT REFERENCES facilities(facility_id),
    authority       TEXT NOT NULL,              -- 'NGT' | 'CPCB' | 'SPCB name' | 'SEBI' | 'MoEFCC'
    case_no         TEXT NOT NULL,
    order_type      TEXT NOT NULL,              -- 'show_cause' | 'closure_direction' | 'environmental_compensation' | 'penalty' | 'consent_revoked' | 'warning'
    date            TEXT NOT NULL,
    penalty_inr     REAL NOT NULL DEFAULT 0,
    status          TEXT NOT NULL,
    summary         TEXT NOT NULL
);

-- GFW integrated-alert style forest loss alerts. Tier 3.
CREATE TABLE land_alerts (
    alert_id            TEXT PRIMARY KEY,
    lat                 REAL NOT NULL,
    lon                 REAL NOT NULL,
    alert_date          TEXT NOT NULL,
    area_ha             REAL NOT NULL,
    confidence          TEXT NOT NULL,          -- 'nominal' | 'high' | 'highest'
    source              TEXT NOT NULL,          -- 'GLAD-L' | 'GLAD-S2' | 'RADD'
    nearest_facility_id TEXT REFERENCES facilities(facility_id),
    distance_km         REAL
);

-- REC / I-REC registry. Tier 3.
CREATE TABLE re_certificates (
    cert_id         TEXT PRIMARY KEY,
    company_id      TEXT NOT NULL REFERENCES companies(company_id),
    registry        TEXT NOT NULL,              -- 'I-REC' | 'REC Registry India'
    mwh             REAL NOT NULL,
    vintage_year    INTEGER NOT NULL,
    status          TEXT NOT NULL,              -- 'retired' | 'active' | 'transferred'
    retired_on      TEXT
);

-- External auditor / assurance statements. Tier 3.
CREATE TABLE audited_reports (
    report_id       TEXT PRIMARY KEY,
    company_id      TEXT NOT NULL REFERENCES companies(company_id),
    fy              TEXT NOT NULL,
    auditor         TEXT NOT NULL,
    assurance_type  TEXT NOT NULL,              -- must equal brsr_filings.assurance_type
    opinion         TEXT NOT NULL,              -- 'unmodified' | 'qualified' | 'adverse'
    scope_covered   TEXT NOT NULL,
    qualified_items TEXT,
    text            TEXT NOT NULL               -- 120-300 word assurance statement
);

-- News + company press releases. Tier 4 (PR) / 5 (news).
CREATE TABLE news_articles (
    article_id      TEXT PRIMARY KEY,
    company_id      TEXT REFERENCES companies(company_id),
    outlet          TEXT NOT NULL,
    outlet_tier     INTEGER NOT NULL,           -- 4 = company PR, 5 = news
    published_on    TEXT NOT NULL,
    headline        TEXT NOT NULL,
    body            TEXT NOT NULL,              -- 250-600 words
    topics          TEXT NOT NULL               -- JSON array, e.g. ["emissions","regulatory"]
);

CREATE INDEX idx_fac_company ON facilities(company_id);
CREATE INDEX idx_brsr_company ON brsr_filings(company_id);
CREATE INDEX idx_ocems_fac ON ocems_exceedances(facility_id, date);
CREATE INDEX idx_reg_company ON regulatory_actions(company_id, date);
CREATE INDEX idx_alert_fac ON land_alerts(nearest_facility_id, alert_date);
CREATE INDEX idx_rec_company ON re_certificates(company_id);
CREATE INDEX idx_news_company ON news_articles(company_id, published_on);
