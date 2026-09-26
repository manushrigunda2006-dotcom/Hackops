"""SQLite round-trips a `DateTime(timezone=True)` column back as a
timezone-*naive* datetime, even though it went in timezone-aware. If
you then compare that against `datetime.now(timezone.utc)` (aware),
Python raises `TypeError: can't compare offset-naive and
offset-aware datetimes` — which FastAPI turns into an unhandled 500,
not the 4xx the deadline-enforcement check expects.

Fix: treat every datetime in this app as naive-but-actually-UTC by
convention. Everything goes through `to_naive_utc` before it's
compared or stored, and `iso_z` re-attaches an explicit UTC marker
only at the JSON boundary, so the frontend still gets an unambiguous
timestamp.
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive datetime, but always UTC — use this instead of
    datetime.now(timezone.utc) or datetime.utcnow() directly, so every
    'now' in the app is normalized the same way.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_naive_utc(dt: datetime | None) -> datetime | None:
    """Normalize any datetime (aware or naive, freshly parsed or
    round-tripped through SQLite) to naive-UTC, so it's always safe
    to compare against `utcnow()`.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def iso_z(dt: datetime | None) -> str | None:
    """Serialize a naive-UTC datetime as an explicit UTC ISO string
    (e.g. '2026-03-01T18:00:00Z') so `new Date(...)` on the frontend
    doesn't misinterpret it as local time.
    """
    dt = to_naive_utc(dt)
    if dt is None:
        return None
    return dt.isoformat() + "Z"
