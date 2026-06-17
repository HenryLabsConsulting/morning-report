-- Normalized warehouse for the morning report. One table per source. The
-- pipeline upserts on the natural key, so a rerun is safe and idempotent.

CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    service       TEXT NOT NULL,
    technician    TEXT NOT NULL,
    status        TEXT NOT NULL,
    scheduled_at  TIMESTAMPTZ NOT NULL,
    line_total    NUMERIC(10,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    id         TEXT PRIMARY KEY,
    job_id     TEXT NOT NULL,
    total      NUMERIC(10,2) NOT NULL,
    balance    NUMERIC(10,2) NOT NULL,
    status     TEXT NOT NULL,
    issued_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS calls (
    id            TEXT PRIMARY KEY,
    direction     TEXT NOT NULL,
    duration_sec  INTEGER NOT NULL,
    result        TEXT NOT NULL,
    started_at    TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    id          TEXT PRIMARY KEY,
    rating      INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    text        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_scheduled ON jobs(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_invoices_issued ON invoices(issued_at);
CREATE INDEX IF NOT EXISTS idx_calls_started ON calls(started_at);
CREATE INDEX IF NOT EXISTS idx_reviews_created ON reviews(created_at);
