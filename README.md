# tiny_cron_nearest_fire

Find the next time a five-field cron expression will fire.

```python
from datetime import datetime
from tiny_cron_nearest_fire import next_fire

next_fire("*/15 9-17 * * 1-5", datetime(2024, 1, 1, 9, 0))
# datetime.datetime(2024, 1, 1, 9, 15)
```

The public surface is exactly two names:

- `next_fire(expression, after=None, *, now=None) -> datetime`
- `CronError`

`next_fire` accepts the classic five fields (minute, hour, day-of-month,
month, day-of-week) with `*`, ranges, lists, and `*/n` steps. It returns
the first matching minute strictly after `after`. When `after` is omitted
it uses `now()` if given, otherwise `datetime.now()`. The result always
has zero seconds and microseconds because cron has minute resolution.

## Why this exists

Most cron libraries either pull in a parser generator or accept a large
grammar (names, `@reboot`, seconds, `L`, `#`). For scheduling a single job
inside a small service, that is more surface than the problem needs. This
library commits to one interpretation: the POSIX five-field grammar with
numeric values only. Anything outside that grammar raises `CronError`
rather than silently matching nothing.

## The awkward edge

When both day-of-month and day-of-week are restricted, this library
follows the POSIX rule: a day matches if *either* field matches. So
`0 0 1 * 2` fires on the 1st of the month and on every Tuesday. If you
want the intersection, restrict only one of the two fields. This is the
single most common source of confusion with cron, and the rule is stated
here rather than hidden in a comment.

## Determinism

`next_fire` takes an optional `now` callable so tests can supply a fake
clock. There is no sleeping and no wall-clock dependency in the test
suite.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

## Limitations

Values are coerced to floats, so very large integers lose precision. If you need
exact integer aggregates over a window, this is the wrong tool.

