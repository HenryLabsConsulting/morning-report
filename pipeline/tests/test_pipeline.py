"""Tests for the pipeline stages: drift detection, transform, and digest math."""

import digest
import pytest
import transform
import validate
from sources import BY_NAME, SOURCES


def test_drift_passes_on_well_formed_records():
    src = BY_NAME["google_reviews"]
    records = [{"id": "GR-1", "rating": 5, "text": "great", "created_at": "2026-06-15T10:00:00Z"}]
    report = validate.check(src, records)
    assert report.ok
    assert not report.warnings


def test_drift_flags_missing_required_field():
    src = BY_NAME["google_reviews"]
    records = [{"id": "GR-1", "rating": 5, "created_at": "2026-06-15T10:00:00Z"}]  # no text
    report = validate.check(src, records)
    assert not report.ok
    assert "text" in report.errors[0]


def test_drift_warns_on_unexpected_field_but_does_not_fail():
    src = BY_NAME["google_reviews"]
    records = [{"id": "GR-1", "rating": 5, "text": "great",
                "created_at": "2026-06-15T10:00:00Z", "sentiment": "positive"}]
    report = validate.check(src, records)
    assert report.ok  # extra fields are warnings, not errors
    assert report.warnings


def test_check_all_raises_on_blocking_drift():
    payloads = {"google_reviews": [{"id": "GR-1", "rating": 5}]}  # missing text + created_at
    with pytest.raises(validate.SchemaDriftError):
        validate.check_all(payloads, [BY_NAME["google_reviews"]])


def test_transform_adds_date_and_coerces_types():
    payloads = {
        "housecall_jobs": [{
            "id": "J1", "customer_name": "A. Reed", "service": "Drain Cleaning",
            "technician": "Marco Ruiz", "status": "completed",
            "scheduled_at": "2026-06-15T09:30:00Z", "line_total": "210.5",
        }],
    }
    out = transform.normalize(payloads)
    job = out["jobs"][0]
    assert job["date"] == "2026-06-15"
    assert isinstance(job["line_total"], float)
    assert job["line_total"] == 210.5


def test_compute_metrics_core_math():
    data = {
        "jobs": [
            {"date": "2026-06-15", "status": "completed", "service": "Drain Cleaning", "line_total": 200.0},
            {"date": "2026-06-15", "status": "completed", "service": "Leak Repair", "line_total": 300.0},
            {"date": "2026-06-15", "status": "canceled", "service": "Leak Repair", "line_total": 0.0},
        ],
        "invoices": [
            {"status": "paid", "balance": 0.0},
            {"status": "overdue", "balance": 150.0},
        ],
        "calls": [
            {"date": "2026-06-15", "result": "booked"},
            {"date": "2026-06-15", "result": "voicemail"},
        ],
        "reviews": [{"date": "2026-06-15", "rating": 4}],
    }
    m = digest.compute_metrics(data, "2026-06-15")
    assert m["revenue"] == 500.0
    assert m["jobs_completed"] == 2
    assert m["jobs_canceled"] == 1
    assert m["booking_rate"] == 0.5
    assert m["outstanding"] == 150.0
    assert m["top_service"] == "Leak Repair"
    assert m["avg_rating"] == 4.0


def test_all_sources_have_required_id():
    for src in SOURCES:
        assert "id" in src.required
