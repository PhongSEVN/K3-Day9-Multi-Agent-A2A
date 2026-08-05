import unittest
from pathlib import Path

from delivery_agent import DeliveryAgent


class DeliveryAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = DeliveryAgent(Path("data"))

    def test_all_official_case_orders_are_supported(self):
        import json

        cases = sorted(Path("input").glob("EC_*.json"))
        self.assertEqual(50, len(cases))
        for path in cases:
            case = json.loads(path.read_text(encoding="utf-8-sig"))
            result = self.agent.investigate(
                case["case_id"], case["customer_request"]["claimed_order_id"]
            )
            self.assertTrue(result.order_evidence_id.startswith("order:"))
            self.assertIn(
                result.delivery_status,
                {
                    "late_seller_handoff",
                    "late_logistics",
                    "within_estimate",
                    "not_delivered_or_dates_missing",
                },
            )

    def test_unknown_order_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown order_id"):
            self.agent.investigate("EC_TEST", "not-an-order")


if __name__ == "__main__":
    unittest.main()

