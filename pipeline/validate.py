"""Schema-drift detection.

Compares each record against its source contract. A missing required field is
an error and stops the run. An unexpected extra field is a warning, surfaced
in the report but not fatal. This is the early-warning system: when a vendor
changes their API, the morning run flags it instead of loading bad data.
"""

from dataclasses import dataclass, field

from sources import Source


@dataclass
class DriftReport:
    source: str
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


class SchemaDriftError(Exception):
    """Raised when required fields are missing from a source payload."""


def check(source: Source, records: list[dict]) -> DriftReport:
    report = DriftReport(source=source.name)
    required = set(source.required)

    for i, record in enumerate(records):
        keys = set(record.keys())
        missing = required - keys
        if missing:
            report.errors.append(
                f"record {i} ({record.get('id', '?')}) missing: {', '.join(sorted(missing))}"
            )
        extra = keys - required
        if extra:
            report.warnings.append(
                f"record {i} ({record.get('id', '?')}) unexpected fields: {', '.join(sorted(extra))}"
            )

    # Collapse repeated extra-field warnings into one line per field set.
    if report.warnings:
        unique = sorted(set(w.split('unexpected fields: ')[1] for w in report.warnings))
        report.warnings = [f"unexpected fields seen: {' | '.join(unique)}"]

    return report


def check_all(payloads: dict[str, list[dict]], sources) -> list[DriftReport]:
    reports = [check(s, payloads.get(s.name, [])) for s in sources]
    failed = [r for r in reports if not r.ok]
    if failed:
        lines = []
        for r in failed:
            lines.append(f"[{r.source}] " + "; ".join(r.errors[:3]))
        raise SchemaDriftError("schema drift detected:\n  " + "\n  ".join(lines))
    return reports
