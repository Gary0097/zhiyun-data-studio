# -*- coding: utf-8 -*-

import unittest

from backend.fusion_engine import analyze_department_metrics


class FusionEngineTests(unittest.TestCase):
    def test_department_metrics_use_configured_fields(self) -> None:
        result = analyze_department_metrics([
            {"dept": "一车间", "qty": 100, "hours": 20, "people": 5, "amount": 1000, "waste": 2},
            {"dept": "一车间", "qty": 50, "hours": 10, "people": 5, "amount": 400, "waste": 1},
            {"dept": "二车间", "qty": 60, "hours": 20, "people": 4, "amount": 720, "waste": 3},
        ], {"department": "dept", "output": "qty", "labor_hours": "hours", "employee_count": "people", "cost": "amount", "loss": "waste"})
        first = result["results"][0]
        self.assertEqual(first["department"], "一车间")
        self.assertEqual(first["output_per_hour"], 5.0)
        self.assertEqual(first["cost_per_output"], 9.33)
        self.assertEqual(first["loss_rate"], 2.0)
        self.assertEqual(result["highlights"]["highest_productivity"], "一车间")
        self.assertEqual(result["highlights"]["lowest_unit_cost"], "一车间")
        self.assertEqual(result["highlights"]["lowest_loss_rate"], "一车间")

    def test_missing_required_mapping_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "labor_hours"):
            analyze_department_metrics([], {"department": "dept", "output": "qty"})

    def test_rows_without_department_are_reported(self) -> None:
        result = analyze_department_metrics([{"dept": "", "qty": 3}], {"department": "dept", "output": "qty", "labor_hours": "hours"})
        self.assertEqual(result["summary"]["invalid_records"], 1)


if __name__ == "__main__":
    unittest.main()
