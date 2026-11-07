"""Find the next instant a cron expression will fire.

The implementation deliberately supports the classic five-field cron
syntax (minute, hour, day-of-month, month, day-of-week) plus the common
``*``, ranges (``a-b``), lists (``a,b,c``), and step (``*/n``) forms.
Anything beyond that (names like ``MON``, ``@reboot``, seconds) is out of
scope and rejected with :class:`CronError` so callers are never silently
surprised by a schedule that never matches.

Day-of-month and day-of-week follow the POSIX rule: when both are
restricted, a day matches if *either* field matches. This is the rule
most users expect from ``crontab(5)`` and is the interpretation this
library commits to.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Iterable, List, Sequence, Tuple


class CronError(ValueError):
    """Raised when a cron expression is malformed or unsupported."""


_FIELD_NAMES = ("minute", "hour", "day-of-month", "month", "day-of-week")

# Inclusive valid range for each of the five fields.
_RANGES: Tuple[Tuple[int, int], ...] = (
    (0, 59),
    (0, 23),
    (1, 31),
    (1, 12),
    (0, 6),
)


def _parse_field(text: str, index: int) -> Tuple[int, ...]:
    """Parse one cron field into a sorted tuple of allowed values.

    ``index`` selects the valid range and the human-readable name used in
error messages. The empty string is rejected rather than treated as
``*`` because an empty field almost always means the expression was
split incorrectly.
    """
    name = _FIELD_NAMES[index]
    lo, hi = _RANGES[index]
    if text == "":
        raise CronError(f"empty {name} field")

    allowed: List[int] = []
    for part in text.split(","):
        if part == "":
            raise CronError(f"empty element in {name} field: {text!r}")

        step = 1
        body = part
        if "/" in part:
            body, _, step_text = part.partition("/")
            if not step_text.isdigit() or int(step_text) < 1:
                raise CronError(f"invalid step in {name} field: {part!r}")
            step = int(step_text)

        if body == "*":
            start, end = lo, hi
        elif "-" in body:
            start_text, _, end_text = body.partition("-")
            if not start_text.isdigit() or not end_text.isdigit():
                raise CronError(f"invalid range in {name} field: {body!r}")
            start, end = int(start_text), int(end_text)
            if start > end:
                raise CronError(f"reversed range in {name} field: {body!r}")
        elif body.isdigit():
            start = end = int(body)
        else:
            raise CronError(f"invalid value in {name} field: {body!r}")

        if start < lo or end > hi:
            raise CronError(
                f"value out of range [{lo}, {hi}] in {name} field: {body!r}"
            )

        allowed.extend(range(start, end + 1, step))

    return tuple(sorted(set(allowed)))


def _parse(expression: str) -> Tuple[Tuple[int, ...], ...]:
    """Split ``expression`` into the five parsed fields."""
    if not isinstance(expression, str):
        raise CronError("cron expression must be a string")
    fields = expression.split()
    if len(fields) != 5:
        raise CronError(
            f"expected 5 fields, got {len(fields)}: {expression!r}"
        )
    return tuple(_parse_field(fields[i], i) for i in range(5))


def _dom_dow_match(
    day: int, weekday: int, dom: Sequence[int], dow: Sequence[int]
) -> bool:
    """Apply the POSIX day-of-month / day-of-week OR rule.

    ``weekday`` uses Python's Monday=0 convention; cron uses Sunday=0, so
the caller maps it before calling. When either field is ``*`` we treat
that field as unrestricted, which reduces to the plain AND rule.
    """
    dom_restricted = tuple(dom) != tuple(range(1, 32))
    dow_restricted = tuple(dow) != tuple(range(0, 7))

    if dom_restricted and dow_restricted:
        return day in dom or weekday in dow
    if dom_restricted:
        return day in dom
    if dow_restricted:
        return weekday in dow
    return True


def _advance_minute(dt: datetime) -> datetime:
    """Return the start of the next minute, discarding seconds/microseconds."""
    return dt.replace(second=0, microsecond=0) + timedelta(minutes=1)


def next_fire(
    expression: str,
    after: datetime | None = None,
    *,
    now: Callable[[], datetime] | None = None,
) -> datetime:
    """Return the next datetime strictly after ``after`` that matches.

    ``after`` defaults to ``now()`` when supplied, otherwise to
    ``datetime.now()``. Passing ``now`` makes the function deterministic in
tests without monkey-patching the clock. The returned value always has
zero seconds and microseconds because cron has minute resolution.

    Raises :class:`CronError` for malformed expressions and
    :class:`OverflowError` if no match is found within four years, which
    covers every non-empty schedule in the supported grammar.
    """
    minutes, hours, dom, months, dow = _parse(expression)

    if after is None:
        after = now() if now is not None else datetime.now()
    if not isinstance(after, datetime):
        raise CronError("after must be a datetime")

    current = _advance_minute(after)
    # Four years guarantees a leap year is included, so any schedule that
    # can ever fire will fire within this window.
    limit = current + timedelta(days=366 * 4)

    while current < limit:
        if current.month not in months:
            # Jump to the first minute of the next month.
            if current.month == 12:
                current = current.replace(
                    year=current.year + 1, month=1, day=1, hour=0, minute=0
                )
            else:
                current = current.replace(
                    month=current.month + 1, day=1, hour=0, minute=0
                )
            continue

        # Python weekday(): Monday=0..Sunday=6. cron: Sunday=0..Saturday=6.
        cron_weekday = (current.weekday() + 1) % 7
        if not _dom_dow_match(current.day, cron_weekday, dom, dow):
            current = current.replace(hour=0, minute=0) + timedelta(days=1)
            continue

        if current.hour not in hours:
            current = current.replace(minute=0) + timedelta(hours=1)
            continue

        if current.minute not in minutes:
            current = current + timedelta(minutes=1)
            continue

        return current

    raise OverflowError(f"no fire time found within four years for {expression!r}")
