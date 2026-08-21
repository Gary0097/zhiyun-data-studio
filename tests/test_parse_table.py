# -*- coding: utf-8 -*-

import unittest

from backend.table_parser import parse_table


class ParseTableTests(unittest.TestCase):
    def test_utf8_csv_is_parsed(self) -> None:
        result = parse_table("orders.csv", "订单编号,客户名称\nA-1,海川制造\n".encode())
        self.assertEqual(result["row_count"], 1)
        self.assertEqual(result["rows"][0]["客户名称"], "海川制造")

    def test_unknown_extension_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "仅支持"):
            parse_table("orders.txt", b"a,b")


if __name__ == "__main__":
    unittest.main()
