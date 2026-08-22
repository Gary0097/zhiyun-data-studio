# -*- coding: utf-8 -*-

import re
import unittest
from pathlib import Path


class GovernanceTypeTests(unittest.TestCase):
    def test_registered_tool_types_are_supported(self) -> None:
        source = (Path(__file__).parents[1] / "backend" / "main.py").read_text(encoding="utf-8")
        types = re.findall(r'tool_type="([^"]+)"', source)
        self.assertTrue(types)
        self.assertTrue(set(types) <= {"file", "internal", "network", "shell"})


if __name__ == "__main__":
    unittest.main()
