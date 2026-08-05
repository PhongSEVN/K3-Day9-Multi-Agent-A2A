import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from coordinator import Coordinator


class EndToEndPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        cls.output_dir = root / "output"
        cls.trace_path = root / "trace.jsonl"
        cls.count = Coordinator("data").run("input", cls.output_dir, cls.trace_path)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_writes_exactly_fifty_valid_outputs(self):
        paths = sorted(self.output_dir.glob("EC_*.json"))
        self.assertEqual(50, self.count)
        self.assertEqual({f"EC_{i:03d}.json" for i in range(1, 51)}, {p.name for p in paths})
        for path in paths:
            self.assertEqual(path.stem, json.loads(path.read_text(encoding="utf-8"))["case_id"])

    def test_official_case_distribution(self):
        issues = Counter(
            json.loads(path.read_text(encoding="utf-8"))["assessment"]["primary_issue"]
            for path in self.output_dir.glob("EC_*.json")
        )
        self.assertEqual(
            {
                "canceled_order_paid": 8,
                "unavailable_order_paid": 8,
                "late_delivery_seller": 8,
                "late_delivery_logistics": 8,
                "valid_split_payment": 9,
                "unsupported_late_claim": 9,
            },
            dict(issues),
        )

    def test_trace_contains_every_agent_handoff(self):
        events = [json.loads(line) for line in self.trace_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(350, len(events))
        self.assertEqual(
            {"coordinator", "order_seller_agent", "payment_agent", "delivery_agent", "policy_agent", "verifier_agent"},
            {event["agent"] for event in events},
        )


if __name__ == "__main__":
    unittest.main()
