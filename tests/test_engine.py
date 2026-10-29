"""Regression tests for the read-only prototype."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from policy_core.engine import PolicyError, load_policy, resolve, snapshot_id


ROOT = Path(__file__).resolve().parent.parent


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.data = load_policy(ROOT / "policies" / "seed.json")

    def test_matching_rules_are_scoped(self):
        self.assertEqual(resolve(self.data, "software", "rendering")["matched_rule_count"], 0)
        self.assertEqual(resolve(self.data, "game", "rendering")["matched_rule_count"], 1)
        self.assertEqual(resolve(self.data, "software", "code_quality")["matched_rule_count"], 1)

    def test_snapshot_is_key_order_independent(self):
        reordered = dict(reversed(list(self.data.items())))
        self.assertEqual(snapshot_id(self.data), snapshot_id(reordered))

    def test_duplicate_ids_are_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            data = json.loads(json.dumps(self.data))
            data["rules"].append(dict(data["rules"][0]))
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(PolicyError):
                load_policy(path)


if __name__ == "__main__":
    unittest.main()
