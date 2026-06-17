"""Source contracts.

Each external system has an expected shape. The pipeline checks incoming
records against these contracts before loading anything, so a vendor changing
their payload shows up as a drift report instead of silently corrupting the
warehouse.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    name: str
    path: str           # API path on the mock host
    envelope: str       # JSON key the records live under
    date_field: str     # field used for the extraction window
    required: tuple     # fields every record must carry


SOURCES = (
    Source(
        name="housecall_jobs",
        path="/housecall/v1/jobs",
        envelope="data",
        date_field="scheduled_at",
        required=("id", "customer_name", "service", "technician", "status",
                  "scheduled_at", "line_total"),
    ),
    Source(
        name="housecall_invoices",
        path="/housecall/v1/invoices",
        envelope="data",
        date_field="issued_at",
        required=("id", "job_id", "total", "balance", "status", "issued_at"),
    ),
    Source(
        name="ringcentral_calls",
        path="/ringcentral/v1/calls",
        envelope="records",
        date_field="started_at",
        required=("id", "direction", "duration_sec", "result", "started_at"),
    ),
    Source(
        name="google_reviews",
        path="/reviews/v1/reviews",
        envelope="reviews",
        date_field="created_at",
        required=("id", "rating", "text", "created_at"),
    ),
)

BY_NAME = {s.name: s for s in SOURCES}
