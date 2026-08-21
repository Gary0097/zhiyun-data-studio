# -*- coding: utf-8 -*-

import unittest

from backend.trend_engine import analyze_order_trends


class TrendEngineTests(unittest.TestCase):
    def test_monthly_series_and_upward_direction(self) -> None:
        result = analyze_order_trends([
            {"order_date": "2026-01-01", "progress": 20},
            {"order_date": "2026-02-01", "progress": 40},
            {"order_date": "2026-02-02", "progress": 60, "production_delay_days": 2},
            {"order_date": "2026-03-01", "progress": 70},
            {"order_date": "2026-03-02", "progress": 80},
            {"order_date": "2026-03-03", "progress": 90},
        ])
        self.assertEqual([item["order_count"] for item in result["series"]], [1, 2, 3])
        self.assertEqual(result["summary"]["direction"], "上升")
        self.assertEqual(result["series"][1]["delay_rate"], 50.0)

    def test_invalid_dates_are_reported(self) -> None:
        result = analyze_order_trends([{"order_date": "错误日期"}, {"progress": 30}])
        self.assertEqual(result["summary"]["invalid_date_records"], 2)
        self.assertEqual(result["summary"]["valid_orders"], 0)

    def test_progress_is_normalized(self) -> None:
        result = analyze_order_trends([
            {"order_date": "2026-01-01", "progress": 200},
            {"order_date": "2026-01-02", "progress": -10},
        ])
        self.assertEqual(result["series"][0]["average_progress"], 50.0)


if __name__ == "__main__":
    unittest.main()
