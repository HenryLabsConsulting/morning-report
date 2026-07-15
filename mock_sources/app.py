"""Mock vendor APIs.

Three endpoints that imitate the systems a service business actually runs on:
a field-service platform, a phone system, and a reviews feed. Each serves the
committed fixture data over HTTP, filtered by date range, so the pipeline can
run real extraction code against real HTTP calls with no vendor accounts.

Run standalone for local testing:
    python mock_sources/app.py
"""

import json
from pathlib import Path

from flask import Flask, jsonify, request

DATA = Path(__file__).resolve().parent / "data"
app = Flask(__name__)


def _load(name: str) -> list:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _window(rows: list, date_field: str) -> list:
    """Filter rows whose date_field falls in the optional since/until window.

    since/until are inclusive day boundaries (YYYY-MM-DD). Comparing the raw
    ISO timestamp against a bare date string is lexicographically wrong on
    the until side (any timestamp on the until day sorts greater than the
    bare date and gets dropped), so both bounds compare on the date portion
    of the timestamp instead.
    """
    since = request.args.get("since")
    until = request.args.get("until")
    out = []
    for row in rows:
        ts_date = row[date_field][:10]
        if since and ts_date < since:
            continue
        if until and ts_date > until:
            continue
        out.append(row)
    return out


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/housecall/v1/jobs")
def jobs():
    return jsonify({"data": _window(_load("housecall_jobs.json"), "scheduled_at")})


@app.get("/housecall/v1/invoices")
def invoices():
    return jsonify({"data": _window(_load("housecall_invoices.json"), "issued_at")})


@app.get("/ringcentral/v1/calls")
def calls():
    return jsonify({"records": _window(_load("ringcentral_calls.json"), "started_at")})


@app.get("/reviews/v1/reviews")
def reviews():
    return jsonify({"reviews": _window(_load("google_reviews.json"), "created_at")})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8077)
