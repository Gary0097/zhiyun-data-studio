# -*- coding: utf-8 -*-

import unittest
from datetime import date

from backend.agent_tools import RiskToolInputError, parse_order_payload
from backend.risk_engine import analyze_orders, score_order


class RiskEngineTests(unittest.TestCase):
    def test_overdue_and_delayed_order_is_red(self) -> None:
        risk = score_order({"order_no": "A", "promised_date": "2026-08-10", "status": "生产中", "progress": 40, "production_delay_days": 7}, date(2026, 8, 22))
        self.assertEqual(risk["level"], "red")
        self.assertTrue(any("超过承诺交期" in reason for reason in risk["reasons"]))

    def test_near_due_low_progress_order_is_yellow(self) -> None:
        risk = score_order({"order_no": "B", "promised_date": "2026-08-24", "status": "生产中", "progress": 50}, date(2026, 8, 22))
        self.assertEqual(risk["level"], "yellow")

    def test_completed_order_is_green(self) -> None:
        risk = score_order({"order_no": "C", "promised_date": "2026-08-01", "status": "已完成", "progress": 100}, date(2026, 8, 22))
        self.assertEqual(risk["level"], "green")

    def test_summary_counts_levels(self) -> None:
        result = analyze_orders([
            {"order_no": "A", "promised_date": "2026-08-01", "status": "生产中", "progress": 20},
            {"order_no": "B", "promised_date": "2026-08-24", "status": "生产中", "progress": 50},
            {"order_no": "C", "promised_date": "2026-08-01", "status": "已完成", "progress": 100},
        ], date(2026, 8, 22))
        self.assertEqual(result["summary"], {"total": 3, "red": 1, "yellow": 1, "green": 1})

    def test_data_core_query_result_can_be_analyzed(self) -> None:
        orders = parse_order_payload('{"records":[{"record_id":"1","data":{"order_no":"A","status":"生产中","progress":20}}]}')
        self.assertEqual(orders[0]["order_no"], "A")

    def test_malformed_agent_payload_is_rejected(self) -> None:
        with self.assertRaises(RiskToolInputError):
            parse_order_payload("not-json")

    def test_invalid_numeric_values_do_not_crash_analysis(self) -> None:
        risk = score_order({"order_no": "D", "status": "生产中", "progress": "未知", "production_delay_days": "无"}, date(2026, 8, 22))
        self.assertEqual(risk["progress"], 0)


if __name__ == "__main__":
    unittest.main()
