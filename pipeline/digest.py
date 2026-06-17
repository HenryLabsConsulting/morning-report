"""Digest.

Turns the warehouse into one day's numbers, a written summary, and an HTML
email. The metric math is a pure function, so it is easy to test and easy to
trust. The summary comes from Claude when ANTHROPIC_API_KEY is set, and from a
committed template otherwise, so the pipeline produces a report for anyone.
"""

import os
from datetime import date, timedelta


def _money(v: float) -> str:
    return f"${v:,.0f}"


def _pct(cur: float, prior: float) -> float:
    return (cur - prior) / prior if prior else 0.0


def _signed(v: float) -> str:
    return f"{'+' if v >= 0 else ''}{v * 100:.0f}%"


def latest_date(data: dict) -> str:
    days = [r["date"] for r in data["jobs"]]
    return max(days) if days else date.today().isoformat()


def compute_metrics(data: dict, target: str) -> dict:
    # Compare the day against its trailing 7-day average rather than the single
    # prior day. This smooths the weekend dip so the report flags real changes,
    # not the normal Monday-after-Sunday swing.
    target_d = date.fromisoformat(target)
    trailing = [(target_d - timedelta(days=n)).isoformat() for n in range(1, 8)]

    def jobs_on(d):
        return [j for j in data["jobs"] if j["date"] == d]

    def revenue(d):
        return sum(j["line_total"] for j in jobs_on(d) if j["status"] == "completed")

    def completed(d):
        return sum(1 for j in jobs_on(d) if j["status"] == "completed")

    def avg(fn):
        vals = [fn(d) for d in trailing]
        return sum(vals) / len(vals) if vals else 0.0

    cur_rev, prior_rev = revenue(target), avg(revenue)
    cur_done, prior_done = completed(target), avg(completed)

    day_calls = [c for c in data["calls"] if c["date"] == target]
    booked = sum(1 for c in day_calls if c["result"] == "booked")
    booking_rate = booked / len(day_calls) if day_calls else 0.0

    day_reviews = [r for r in data["reviews"] if r["date"] == target]
    avg_rating = sum(r["rating"] for r in day_reviews) / len(day_reviews) if day_reviews else 0.0

    outstanding = sum(i["balance"] for i in data["invoices"]
                      if i["status"] in ("open", "overdue"))

    by_service = {}
    for j in jobs_on(target):
        if j["status"] == "completed":
            by_service[j["service"]] = by_service.get(j["service"], 0.0) + j["line_total"]
    top_service = max(by_service.items(), key=lambda kv: kv[1]) if by_service else ("n/a", 0.0)

    return {
        "date": target,
        "revenue": cur_rev,
        "revenue_delta": _pct(cur_rev, prior_rev),
        "jobs_completed": cur_done,
        "jobs_delta": _pct(cur_done, prior_done),
        "jobs_canceled": sum(1 for j in jobs_on(target) if j["status"] == "canceled"),
        "calls": len(day_calls),
        "booked": booked,
        "booking_rate": booking_rate,
        "new_reviews": len(day_reviews),
        "avg_rating": avg_rating,
        "outstanding": outstanding,
        "top_service": top_service[0],
        "top_service_revenue": top_service[1],
    }


def build_summary_demo(m: dict) -> str:
    rev_dir = "up" if m["revenue_delta"] > 0 else "down" if m["revenue_delta"] < 0 else "flat"
    lead = {
        "up": f"Yesterday booked {_money(m['revenue'])} in completed work, {_signed(m['revenue_delta'])} against the 7-day average.",
        "down": f"Yesterday came in at {_money(m['revenue'])} in completed work, {_signed(m['revenue_delta'])} below the 7-day average.",
        "flat": f"Yesterday held at {_money(m['revenue'])} in completed work, in line with the 7-day average.",
    }[rev_dir]
    body = (
        f"The team closed {m['jobs_completed']} jobs and canceled {m['jobs_canceled']}. "
        f"{m['top_service']} led the day at {_money(m['top_service_revenue'])}. "
        f"The phones took {m['calls']} calls and booked {m['booked']} of them, "
        f"a {m['booking_rate'] * 100:.0f}% booking rate."
    )
    quality = (
        f"{m['new_reviews']} new reviews came in at an average of {m['avg_rating']:.1f} stars. "
        if m["new_reviews"] else "No new reviews landed yesterday. "
    )
    cash = f"Open invoice balance stands at {_money(m['outstanding'])}."
    watch = (
        "Booking rate is the lever today: a few more booked calls turns into tomorrow's revenue."
        if m["booking_rate"] < 0.55
        else "Booking is healthy. Keep the schedule full and the cash collected."
    )
    return " ".join([lead, body, quality + cash, watch])


def _prompt(m: dict) -> str:
    return (
        "You are an operations analyst for a plumbing service business. Write a short "
        "morning summary (4 to 6 sentences) of yesterday's numbers for the owner. "
        "Lead with revenue. State what moved and why it matters. End with one thing to "
        "watch today. No markdown, no bullet points, no em dashes. Short sentences.\n\n"
        f"Date: {m['date']}\n"
        f"Completed revenue: {_money(m['revenue'])} ({_signed(m['revenue_delta'])} vs 7-day average)\n"
        f"Jobs completed: {m['jobs_completed']} ({_signed(m['jobs_delta'])} vs 7-day average), canceled: {m['jobs_canceled']}\n"
        f"Calls: {m['calls']}, booked: {m['booked']} ({m['booking_rate'] * 100:.0f}% booking rate)\n"
        f"New reviews: {m['new_reviews']} at {m['avg_rating']:.1f} stars\n"
        f"Open invoice balance: {_money(m['outstanding'])}\n"
        f"Top service: {m['top_service']} at {_money(m['top_service_revenue'])}"
    )


def build_summary(m: dict) -> tuple[str, str]:
    """Return (summary, mode). mode is 'live' or 'demo'."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return build_summary_demo(m), "demo"
    try:
        import anthropic

        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=1024,
            system="You are a precise operations analyst who writes plain, useful morning briefings.",
            messages=[{"role": "user", "content": _prompt(m)}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        return (text or build_summary_demo(m)), "live"
    except Exception:
        return build_summary_demo(m), "demo"


def render_html(m: dict, summary: str, mode: str) -> str:
    def stat(label, value, sub=""):
        sub_html = f'<div style="font-size:12px;color:#7a8699;margin-top:2px">{sub}</div>' if sub else ""
        return (
            f'<td style="padding:14px 16px;background:#ffffff;border:1px solid #e6e9ef;'
            f'border-radius:10px" valign="top">'
            f'<div style="font-size:12px;color:#7a8699;text-transform:uppercase;'
            f'letter-spacing:.04em">{label}</div>'
            f'<div style="font-size:24px;font-weight:700;color:#16202e;margin-top:6px">{value}</div>'
            f'{sub_html}</td>'
        )

    badge = ("AI LIVE", "#0f8a55", "#e6f6ee") if mode == "live" else ("SAMPLE", "#2a66d9", "#eaf1ff")

    return f"""<!doctype html>
<html><body style="margin:0;background:#eef1f6;font-family:Segoe UI,Helvetica,Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:28px 12px">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px">
  <tr><td style="padding:4px 4px 18px">
    <div style="font-size:13px;color:#7a8699">MORNING REPORT</div>
    <div style="font-size:22px;font-weight:700;color:#16202e">Tri-County Plumbing &middot; {m['date']}</div>
  </td></tr>
  <tr><td style="padding:18px 20px;background:#16202e;border-radius:12px">
    <table width="100%"><tr>
      <td><span style="display:inline-block;font-size:11px;font-weight:700;color:{badge[1]};
        background:{badge[2]};padding:3px 9px;border-radius:999px">{badge[0]}</span></td>
    </tr></table>
    <p style="color:#dfe5ee;font-size:15px;line-height:1.65;margin:12px 0 0">{summary}</p>
  </td></tr>
  <tr><td style="height:14px"></td></tr>
  <tr><td>
    <table width="100%" cellspacing="8"><tr>
      {stat("Revenue", _money(m['revenue']), _signed(m['revenue_delta']) + " vs 7-day avg")}
      {stat("Jobs Completed", str(m['jobs_completed']), f"{m['jobs_canceled']} canceled")}
    </tr><tr>
      {stat("Calls Booked", f"{m['booked']} / {m['calls']}", f"{m['booking_rate']*100:.0f}% booking rate")}
      {stat("Open Balance", _money(m['outstanding']), f"{m['new_reviews']} new reviews, {m['avg_rating']:.1f}★")}
    </tr></table>
  </td></tr>
  <tr><td style="padding:18px 4px;color:#7a8699;font-size:12px">
    Generated by the morning-report pipeline from field-service, phone, and review data.
    {"Summary written live by Claude." if mode == "live" else "Set ANTHROPIC_API_KEY for a live Claude summary."}
  </td></tr>
</table>
</td></tr></table>
</body></html>"""
