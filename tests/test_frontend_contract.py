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

    def test_analysis_artifacts_have_review_and_export_controls(self):
        for text in ["保存为待审阅工件", "接受工件", "撤销接受", "导出工件"]:
            self.assertIn(text, self.source)

    def test_agent_dock_uses_real_streaming_model_endpoint(self):
        for text in [
            'Q.host.fetch("/zhiyun-app-discovery/agent/chat"',
            'app_id: "zhiyun-data-studio"',
            "response.body.getReader()",
            "new TextDecoder()",
            "agentSessionRef.current",
            "history: history",
            "Authorization",
        ]:
            self.assertIn(text, self.source)
        self.assertNotIn("已把该问题交给企业数据分析智能体，正在生成结构化结果", self.source)

    def test_agent_context_is_bounded_traceable_and_never_autoloads_simulation(self):
        for text in ["agentPageContext", ".slice(0, 6000)", "selected.record_id", "selected.source_type", "不会自动载入模拟数据"]:
            self.assertIn(text, self.source)
        self.assertNotIn('source_type: "simulated"', self.source)

    def test_agent_dock_supports_stop_retry_and_explicit_errors(self):
        for text in ["new AbortController()", "controller.signal", "停止", "重试上次", "调用智能体失败", "智能体未返回可显示内容"]:
            self.assertIn(text, self.source)

    def test_agent_provenance_never_defaults_aggregate_to_real(self):
        for text in ['function agentSourceType()', '"mixed"', '"unknown"', 'source_type: agentSourceType()']:
            self.assertIn(text, self.source)
        self.assertNotIn('selected && selected.source_type ? selected.source_type : "real"', self.source)

    def test_agent_artifact_context_uses_persisted_project_status(self):
        self.assertIn("project_status: artifact.project_status", self.source)
        self.assertNotIn("status: artifact.status", self.source)

    def test_completed_agent_event_preserves_all_text_parts(self):
        self.assertIn('var completedText = ""', self.source)
        self.assertIn("completedText += part.text", self.source)
        self.assertNotIn("full = part.text; setLastAgentBot(full)", self.source)


if __name__ == "__main__":
    unittest.main()
