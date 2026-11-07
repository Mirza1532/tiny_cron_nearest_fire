"""Public surface for tiny_cron_nearest_fire.

Only :func:`next_fire` and :class:`CronError` are exported. Keeping the
surface tiny makes the package easy to audit and keeps callers from
depending on internals that may move.
"""

from .core import CronError, next_fire

__all__ = ["next_fire", "CronError"]
