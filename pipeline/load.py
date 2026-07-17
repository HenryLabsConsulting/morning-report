"""Load.

Upserts normalized records into PostgreSQL on the natural key, so reruns never
duplicate. The schema is created on first run.
"""

import os
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

SCHEMA = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

UPSERTS = {
    "jobs": (
        """INSERT INTO jobs (id, customer_name, service, technician, status,
                             scheduled_at, line_total) VALUES %s
           ON CONFLICT (id) DO UPDATE SET
             customer_name = EXCLUDED.customer_name,
             service = EXCLUDED.service,
             technician = EXCLUDED.technician,
             status = EXCLUDED.status,
             scheduled_at = EXCLUDED.scheduled_at,
             line_total = EXCLUDED.line_total""",
        lambda r: (r["id"], r["customer_name"], r["service"], r["technician"],
                   r["status"], r["scheduled_at"], r["line_total"]),
    ),
    "invoices": (
        """INSERT INTO invoices (id, job_id, total, balance, status, issued_at)
           VALUES %s
           ON CONFLICT (id) DO UPDATE SET
             balance = EXCLUDED.balance, status = EXCLUDED.status""",
        lambda r: (r["id"], r["job_id"], r["total"], r["balance"], r["status"],
                   r["issued_at"]),
    ),
    "calls": (
        """INSERT INTO calls (id, direction, duration_sec, result, started_at)
           VALUES %s ON CONFLICT (id) DO NOTHING""",
        lambda r: (r["id"], r["direction"], r["duration_sec"], r["result"],
                   r["started_at"]),
    ),
    "reviews": (
        """INSERT INTO reviews (id, rating, text, created_at) VALUES %s
           ON CONFLICT (id) DO NOTHING""",
        lambda r: (r["id"], r["rating"], r["text"], r["created_at"]),
    ),
}


def connect(retries: int = 30, delay: float = 2.0):
    dsn = os.environ.get("DATABASE_URL")
    last = None
    for attempt in range(1, retries + 1):
        try:
            return psycopg2.connect(dsn) if dsn else psycopg2.connect()
        except psycopg2.OperationalError as err:
            last = err
            print(f"  waiting for database ({attempt}/{retries})...")
            time.sleep(delay)
    raise SystemExit(f"could not connect to database: {last}")


def load(conn, normalized: dict[str, list[dict]]) -> dict[str, int]:
    cur = conn.cursor()
    cur.execute(SCHEMA.read_text(encoding="utf-8"))
    counts = {}
    for table, (sql, row_fn) in UPSERTS.items():
        rows = [row_fn(r) for r in normalized.get(table, [])]
        if rows:
            execute_values(cur, sql, rows)
        counts[table] = len(rows)
    conn.commit()
    cur.close()
    return counts


def fetch_all(conn) -> dict[str, list[dict]]:
    """Read the warehouse back as dicts for the digest."""
    cur = conn.cursor()
    out = {}
    queries = {
        "jobs": "SELECT id, service, technician, status, "
                "to_char(scheduled_at, 'YYYY-MM-DD') AS date, line_total::float8 "
                "FROM jobs",
        "invoices": "SELECT id, job_id, total::float8, balance::float8, status, "
                    "to_char(issued_at, 'YYYY-MM-DD') AS date FROM invoices",
        "calls": "SELECT id, direction, duration_sec, result, "
                 "to_char(started_at, 'YYYY-MM-DD') AS date FROM calls",
        "reviews": "SELECT id, rating, text, "
                   "to_char(created_at, 'YYYY-MM-DD') AS date FROM reviews",
    }
    for table, sql in queries.items():
        cur.execute(sql)
        cols = [c.name for c in cur.description]
        out[table] = [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
    cur.close()
    return out
