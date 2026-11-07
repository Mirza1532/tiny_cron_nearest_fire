import unittest
from datetime import datetime

from tiny_cron_nearest_fire import CronError, next_fire


class ParseTests(unittest.TestCase):
    def test_wrong_field_count(self):
        with self.assertRaises(CronError):
            next_fire("* * * *")
        with self.assertRaises(CronError):
            next_fire("* * * * * *")

    def test_empty_field(self):
        with self.assertRaises(CronError):
            next_fire("* * * * ")

    def test_out_of_range(self):
        with self.assertRaises(CronError):
            next_fire("60 * * * *")
        with self.assertRaises(CronError):
            next_fire("* 24 * * *")
        with self.assertRaises(CronError):
            next_fire("* * 0 * *")
        with self.assertRaises(CronError):
            next_fire("* * * 13 *")
        with self.assertRaises(CronError):
            next_fire("* * * * 7")

    def test_reversed_range(self):
        with self.assertRaises(CronError):
            next_fire("10-5 * * * *")

    def test_bad_step(self):
        with self.assertRaises(CronError):
            next_fire("*/0 * * * *")
        with self.assertRaises(CronError):
            next_fire("*/x * * * *")

    def test_names_rejected(self):
        with self.assertRaises(CronError):
            next_fire("* * * JAN *")
        with self.assertRaises(CronError):
            next_fire("* * * * MON")


class FireTimeTests(unittest.TestCase):
    def test_every_minute(self):
        start = datetime(2024, 1, 1, 0, 0, 30)
        self.assertEqual(next_fire("* * * * *", start), datetime(2024, 1, 1, 0, 1))

    def test_specific_minute_and_hour(self):
        start = datetime(2024, 1, 1, 0, 0)
        self.assertEqual(next_fire("30 14 * * *", start), datetime(2024, 1, 1, 14, 30))

    def test_strictly_after(self):
        start = datetime(2024, 1, 1, 14, 30)
        self.assertEqual(next_fire("30 14 * * *", start), datetime(2024, 1, 2, 14, 30))

    def test_rolls_into_next_day(self):
        start = datetime(2024, 1, 1, 23, 59)
        self.assertEqual(next_fire("0 0 * * *", start), datetime(2024, 1, 2, 0, 0))

    def test_step_minutes(self):
        start = datetime(2024, 1, 1, 0, 0)
        self.assertEqual(next_fire("*/15 * * * *", start), datetime(2024, 1, 1, 0, 15))
        self.assertEqual(
            next_fire("*/15 * * * *", datetime(2024, 1, 1, 0, 15)),
            datetime(2024, 1, 1, 0, 30),
        )

    def test_list(self):
        start = datetime(2024, 1, 1, 0, 0)
        self.assertEqual(next_fire("5,10,15 * * * *", start), datetime(2024, 1, 1, 0, 5))

    def test_range(self):
        start = datetime(2024, 1, 1, 0, 0)
        self.assertEqual(next_fire("0-5 * * * *", start), datetime(2024, 1, 1, 0, 1))

    def test_day_of_month(self):
        start = datetime(2024, 1, 31, 0, 0)
        self.assertEqual(next_fire("0 0 15 * *", start), datetime(2024, 2, 15, 0, 0))

    def test_month_rollover(self):
        start = datetime(2024, 11, 30, 0, 0)
        self.assertEqual(next_fire("0 0 1 12 *", start), datetime(2024, 12, 1, 0, 0))

    def test_day_of_week(self):
        # 2024-01-01 is a Monday; cron Sunday=0, so Monday is 1.
        start = datetime(2024, 1, 1, 0, 0)
        self.assertEqual(next_fire("0 0 * * 1", start), datetime(2024, 1, 8, 0, 0))

    def test_dom_and_dow_or_rule(self):
        # 2024-01-01 is Monday. "1st of month OR Tuesday" should fire
        # on 2024-01-02, the first Tuesday, before 2024-02-01.
        start = datetime(2024, 1, 1, 0, 0)
        self.assertEqual(next_fire("0 0 1 * 2", start), datetime(2024, 1, 2, 0, 0))

    def test_dom_restricted_dow_star(self):
        start = datetime(2024, 1, 1, 0, 0)
        self.assertEqual(next_fire("0 0 5 * *", start), datetime(2024, 1, 5, 0, 0))

    def test_dow_restricted_dom_star(self):
        start = datetime(2024, 1, 1, 0, 0)
        self.assertEqual(next_fire("0 0 * * 5", start), datetime(2024, 1, 5, 0, 0))

    def test_no_match_raises_overflow(self):
        # February 30 never exists; a four-year window will not contain it.
        with self.assertRaises(OverflowError):
            next_fire("0 0 30 2 *", datetime(2024, 1, 1, 0, 0))

    def test_after_defaults_to_now_argument(self):
        fake = datetime(2024, 3, 10, 8, 0)
        self.assertEqual(
            next_fire("0 9 * * *", now=lambda: fake),
            datetime(2024, 3, 10, 9, 0),
        )

    def test_result_has_zero_seconds(self):
        result = next_fire("* * * * *", datetime(2024, 1, 1, 0, 0, 45, 123456))
        self.assertEqual(result.second, 0)
        self.assertEqual(result.microsecond, 0)

    def test_non_datetime_after(self):
        with self.assertRaises(CronError):
            next_fire("* * * * *", "not a datetime")


if __name__ == "__main__":
    unittest.main()
