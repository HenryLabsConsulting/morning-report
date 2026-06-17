"""Run the morning report end to end.

    extract -> validate (schema drift) -> transform -> load -> digest -> email

Modes:
    --dry-run     Skip the database. Extract, validate, transform, and build the
                  report straight from memory. Good for a quick local check.
    (default)     Load PostgreSQL, read it back, then build the report.

The HTML report is always written to disk. If an SMTP host is reachable it is
also emailed, which is how the Docker setup delivers it to MailHog for viewing.
"""

import argparse
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

import digest
import extract
import transform
import validate
from sources import SOURCES

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "samples" / "daily_digest.html"

WINDOW_SINCE = "2026-01-01"
WINDOW_UNTIL = "2026-12-31"


def send_email(host: str, port: int, html: str, subject: str) -> bool:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("REPORT_FROM", "reports@morning-report.local")
    msg["To"] = os.environ.get("REPORT_TO", "owner@tri-county-plumbing.local")
    msg.set_content("This report is best viewed as HTML.")
    msg.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(host, port, timeout=8) as smtp:
            smtp.send_message(msg)
        return True
    except OSError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the daily morning report.")
    parser.add_argument("--host", default=os.environ.get("SOURCE_API_HOST", "http://localhost:8077"))
    parser.add_argument("--dry-run", action="store_true", help="Skip the database.")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--smtp-host", default=os.environ.get("SMTP_HOST"))
    parser.add_argument("--smtp-port", type=int, default=int(os.environ.get("SMTP_PORT", "1025")))
    args = parser.parse_args()

    print(f"Extracting from {args.host} ...")
    payloads = extract.extract_all(args.host, WINDOW_SINCE, WINDOW_UNTIL)
    for name, rows in payloads.items():
        print(f"  {name:<20} {len(rows):>6} records")

    print("Checking for schema drift ...")
    try:
        reports = validate.check_all(payloads, SOURCES)
    except validate.SchemaDriftError as err:
        print(err, file=sys.stderr)
        raise SystemExit(2) from err
    warnings = [w for r in reports for w in r.warnings]
    print(f"  no blocking drift. {len(warnings)} warning(s).")

    normalized = transform.normalize(payloads)

    if args.dry_run:
        data = normalized
        print("Dry run: building report from memory (no database).")
    else:
        import load

        conn = load.connect()
        try:
            counts = load.load(conn, normalized)
            print("Loaded:", ", ".join(f"{k}={v}" for k, v in counts.items()))
            data = load.fetch_all(conn)
        finally:
            conn.close()

    target = digest.latest_date(data)
    metrics = digest.compute_metrics(data, target)
    summary, mode = digest.build_summary(metrics)
    html = digest.render_html(metrics, summary, mode)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Report written to {out_path} (summary mode: {mode})")

    if args.smtp_host:
        ok = send_email(args.smtp_host, args.smtp_port, html,
                        f"Morning Report — {target}")
        print(f"Email {'delivered to ' + args.smtp_host if ok else 'skipped (SMTP unreachable)'}")

    print("\n" + summary)


if __name__ == "__main__":
    main()
