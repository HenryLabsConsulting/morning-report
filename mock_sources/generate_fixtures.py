"""Build the fixture data the mock vendor APIs serve.

This stands in for three systems a typical service business runs on: a
field-service platform (jobs and invoices), a phone system (calls), and a
reviews platform. The data is synthetic and seeded, so it is the same on every
run. The mock API reads these JSON files and serves them over HTTP, which lets
the pipeline exercise real API-extraction code with no third-party accounts.

    python mock_sources/generate_fixtures.py
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 415
DAYS = 35
END = datetime(2026, 6, 15, 18, 0, 0)

OUT = Path(__file__).resolve().parent / "data"

TECHS = ["Marco Ruiz", "Dana Pratt", "Lewis Kang", "Priya Nair", "Sam Olsen", "Tara Quinn"]
SERVICES = [
    ("Drain Cleaning", 195, 240),
    ("Water Heater Repair", 320, 540),
    ("Leak Repair", 240, 410),
    ("Sump Pump Install", 980, 1450),
    ("Faucet & Fixture", 165, 320),
    ("Emergency Call-Out", 280, 620),
]
CALL_RESULTS = ["booked", "voicemail", "info", "missed", "booked", "booked"]
REVIEW_TEXT = {
    5: ["On time and tidy. Fixed the leak fast.", "Great tech, clear pricing.",
        "Booked same day, solved it in one visit."],
    4: ["Good work, slight wait for parts.", "Fair price, friendly tech."],
    3: ["Got it done but took two trips.", "Communication could be better."],
    2: ["Had to call back about the same issue.", "Quote changed at the door."],
    1: ["Still leaking after the visit.", "Long wait to get scheduled."],
}


def iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat() + "Z"


def main() -> None:
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    jobs, invoices, calls, reviews = [], [], [], []
    job_seq = invoice_seq = call_seq = review_seq = 0

    for day_offset in range(DAYS, -1, -1):
        day = END - timedelta(days=day_offset)
        weekend = day.weekday() >= 5
        volume = rng.randint(4, 7) if weekend else rng.randint(9, 16)

        # Phone calls lead the day; some convert to jobs.
        for _ in range(int(volume * rng.uniform(1.4, 2.0))):
            call_seq += 1
            start = day.replace(hour=rng.randint(7, 18), minute=rng.randint(0, 59))
            calls.append({
                "id": f"RC-{call_seq:05d}",
                "direction": rng.choices(["inbound", "outbound"], weights=[78, 22])[0],
                "from_number": f"+1616555{rng.randint(1000, 9999)}",
                "duration_sec": max(15, int(rng.gauss(190, 80))),
                "result": rng.choice(CALL_RESULTS),
                "started_at": iso(start),
            })

        for _ in range(volume):
            job_seq += 1
            service, lo, hi = rng.choice(SERVICES)
            scheduled = day.replace(hour=rng.randint(8, 16), minute=rng.choice([0, 30]))
            status = rng.choices(["completed", "completed", "completed", "canceled", "scheduled"],
                                 weights=[70, 0, 0, 12, 18])[0]
            total = round(rng.uniform(lo, hi), 2) if status == "completed" else 0.0
            jobs.append({
                "id": f"HCP-J-{job_seq:05d}",
                "customer_name": f"{rng.choice(['A.', 'B.', 'C.', 'D.', 'E.'])} {rng.choice(['Reed', 'Cole', 'Maddox', 'Vance', 'Pope', 'Frost'])}",
                "service": service,
                "technician": rng.choice(TECHS),
                "status": status,
                "scheduled_at": iso(scheduled),
                "line_total": total,
            })

            if status == "completed":
                invoice_seq += 1
                bal = 0.0 if rng.random() < 0.72 else round(total, 2)
                invoices.append({
                    "id": f"HCP-I-{invoice_seq:05d}",
                    "job_id": f"HCP-J-{job_seq:05d}",
                    "total": total,
                    "balance": bal,
                    "status": "paid" if bal == 0 else rng.choice(["open", "overdue"]),
                    "issued_at": iso(scheduled + timedelta(hours=2)),
                })

                if rng.random() < 0.30:
                    review_seq += 1
                    rating = rng.choices([5, 4, 3, 2, 1], weights=[48, 27, 13, 7, 5])[0]
                    reviews.append({
                        "id": f"GR-{review_seq:05d}",
                        "rating": rating,
                        "text": rng.choice(REVIEW_TEXT[rating]),
                        "created_at": iso(day.replace(hour=rng.randint(9, 20))),
                    })

    _dump("housecall_jobs.json", jobs)
    _dump("housecall_invoices.json", invoices)
    _dump("ringcentral_calls.json", calls)
    _dump("google_reviews.json", reviews)

    print(f"jobs={len(jobs)} invoices={len(invoices)} calls={len(calls)} reviews={len(reviews)}")


def _dump(name: str, rows: list) -> None:
    (OUT / name).write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
