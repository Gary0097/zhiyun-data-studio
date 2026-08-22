# -*- coding: utf-8 -*-

import unittest
from pathlib import Path

from backend.order_contract import OrderContractError, build_agent_context, normalize_order_response


class OrderContractTests(unittest.TestCase):
    def test_data_core_orders_contract_preserves_persistence_metadata(self) -> None:
        result = normalize_order_response({"orders": [{
            "record_id": "rec-1", "source_type": "real", "source_name": "erp",
            "data": {"order_no": "SO-1", "customer_name": "海川", "progress": 40},
        }]})
        order = result["orders"][0]
        self.assertEqual(order["record_id"], "rec-1")
        self.assertEqual(order["source_type"], "real")
        self.assertEqual(order["source_name"], "erp")
        self.assertIn("promised_date", order["missing_fields"])

    def test_empty_data_core_result_stays_empty(self) -> None:
        self.assertEqual(normalize_order_response({"orders": []}), {"orders": [], "total": 0})

    def test_invalid_data_core_shape_is_rejected(self) -> None:
        with self.assertRaises(OrderContractError):
            normalize_order_response({"items": []})

    def test_agent_context_requires_traceable_record(self) -> None:
        context = build_agent_context({"record_id": "rec-2", "source_type": "simulated", "order_no": "SO-2"})
        self.assertEqual(context["record_id"], "rec-2")
        self.assertEqual(context["source_type"], "simulated")
        with self.assertRaisesRegex(OrderContractError, "record_id"):
            build_agent_context({"source_type": "real"})

    def test_runtime_routes_expose_contract_and_context(self) -> None:
        source = (Path(__file__).parents[1] / "backend" / "main.py").read_text(encoding="utf-8")
        self.assertIn('@router.post("/orders/normalize")', source)
        self.assertIn('@router.post("/agent/context")', source)
        self.assertIn("status_code=502", source)
        self.assertIn("status_code=422", source)


if __name__ == "__main__":
    unittest.main()
