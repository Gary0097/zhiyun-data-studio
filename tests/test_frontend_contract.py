import unittest
from pathlib import Path


class FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).parents[1] / "ui" / "index.js").read_text(encoding="utf-8")

    def test_primary_orders_api_is_used(self):
        self.assertIn('json(CORE + "/orders")', self.source)
        self.assertNotIn('json(CORE + "/records/orders?limit=500")', self.source)

    def test_required_filters_and_states_are_present(self):
        for text in ("全部客户", "全部状态", "全部来源", "真实数据", "模拟数据", "Data Core 中暂无持久化订单", "字段缺失"):
            self.assertIn(text, self.source)

    def test_agent_context_keeps_data_core_identity(self):
        self.assertIn('"/agent/context"', self.source)
        self.assertIn("selected.record_id", self.source)
        self.assertIn("selected.source_type", self.source)

    def test_agent_context_requires_a_host_contract(self):
        self.assertIn('typeof Q.setAgentContext !== "function"', self.source)
        self.assertIn("Promise.resolve(Q.setAgentContext(context))", self.source)
        self.assertNotIn("qwenpaw:agent-context", self.source)


if __name__ == "__main__":
    unittest.main()
