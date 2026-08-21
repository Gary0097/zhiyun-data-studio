# -*- coding: utf-8 -*-

import unittest
from datetime import date

from backend.brief_engine import generate_order_daily_brief


class BriefEngineTests(unittest.TestCase):
    def test_brief_reports_scope_and_high_risk_orders(self) -> None:
        brief = generate_order_daily_brief([
            {"order_no": "A", "order_date": "2026-08-01", "promised_date": "2026-08-10", "status": "生产中", "progress": 20}
        ], date(2026, 8, 22))
        self.assertEqual(brief["data_scope"], ["orders"])
        self.assertIn("finance", brief["missing_domains"])
        self.assertEqual(brief["summary"]["red"], 1)
        self.assertEqual(brief["top_risks"][0]["order_no"], "A")

    def test_empty_brief_does_not_invent_data(self) -> None:
        brief = generate_order_daily_brief([], date(2026, 8, 22))
        self.assertEqual(brief["summary"]["total"], 0)
        self.assertEqual(brief["insights"][0]["level"], "normal")

    def test_quality_warning_is_included(self) -> None:
        brief = generate_order_daily_brief([{"progress": 10}], date(2026, 8, 22))
        self.assertTrue(any("字段质量" in item["text"] for item in brief["insights"]))


if __name__ == "__main__":
    unittest.main()
