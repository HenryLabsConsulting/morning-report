"""Transform.

Normalizes the raw vendor payloads into clean records the warehouse and the
digest both use. Numeric fields are coerced, and each record gets a plain date
derived from its timestamp so the digest can group by day without parsing
timestamps everywhere.
"""


def _date(ts: str) -> str:
    return ts[:10]


def normalize(payloads: dict[str, list[dict]]) -> dict[str, list[dict]]:
    jobs = [
        {
            "id": r["id"],
            "customer_name": r["customer_name"],
            "service": r["service"],
            "technician": r["technician"],
            "status": r["status"],
            "scheduled_at": r["scheduled_at"],
            "date": _date(r["scheduled_at"]),
            "line_total": float(r["line_total"]),
        }
        for r in payloads.get("housecall_jobs", [])
    ]

    invoices = [
        {
            "id": r["id"],
            "job_id": r["job_id"],
            "total": float(r["total"]),
            "balance": float(r["balance"]),
            "status": r["status"],
            "issued_at": r["issued_at"],
            "date": _date(r["issued_at"]),
        }
        for r in payloads.get("housecall_invoices", [])
    ]

    calls = [
        {
            "id": r["id"],
            "direction": r["direction"],
            "duration_sec": int(r["duration_sec"]),
            "result": r["result"],
            "started_at": r["started_at"],
            "date": _date(r["started_at"]),
        }
        for r in payloads.get("ringcentral_calls", [])
    ]

    reviews = [
        {
            "id": r["id"],
            "rating": int(r["rating"]),
            "text": r["text"],
            "created_at": r["created_at"],
            "date": _date(r["created_at"]),
        }
        for r in payloads.get("google_reviews", [])
    ]

    return {"jobs": jobs, "invoices": invoices, "calls": calls, "reviews": reviews}
