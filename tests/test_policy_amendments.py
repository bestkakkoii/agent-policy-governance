"""Owner-amendment contracts; research URLs are fixtures, not verified evidence."""
from __future__ import annotations

import copy
import datetime
import tempfile
import unittest
from pathlib import Path

from policy_core.common import digest, policy_error
from policy_core.engine import discover_profile, infer_topics, load_catalog, select_rules
from policy_core.evolution import propose, publish, review, validate_evidence
from policy_core.runtime import policy_runtime
from tools.package import plugin_files


class policy_amendment_tests(unittest.TestCase):
    def evidence(self) -> dict:
        return {"url": "https://example.org/theory-fixture", "observed_on": datetime.datetime.now(datetime.UTC).date().isoformat(),
                "claim": "Expected lower work under stated assumptions; target performance is not measured.",
                "kind": "theory", "artifact_sha256": None, "baseline": "Current full-scan algorithm",
                "assumptions": "Inputs are ordered and updates are sparse.",
                "applicability": "The project guarantees these properties for the target workload."}

    def test_cpp_architecture_is_explicit_and_profile_scoped(self) -> None:
        catalog = load_catalog()
        cpp_rules = {rule["rule_id"]: rule for rule in select_rules(catalog, ["software", "cpp"], [])}
        rule = cpp_rules["owner.cpp_modules"]
        self.assertEqual(rule["strength"], "required")
        text = rule["statement"] + " " + rule["details"]
        for requirement in ("C++26", "experimental", "import std;", "export module module_name;", "import module_name;", "module module_name;", "implementation units", "public declarations", "blocker"):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, text)
        generic = select_rules(catalog, ["software"], ["cpp"])
        self.assertNotIn("owner.cpp_modules", [item["rule_id"] for item in generic])

    def test_latest_preference_is_common_without_loading_every_domain(self) -> None:
        rules = {rule["rule_id"]: rule for rule in select_rules(load_catalog(), ["software"], [])}
        self.assertIn("owner.latest", rules)
        self.assertNotIn("owner.cpp_modules", rules)
        self.assertFalse(any(identity.startswith("R") for identity in rules))
        text = rules["owner.latest"]["statement"] + " " + rules["owner.latest"]["details"]
        for phrase in ("algorithms", "concepts", "theoretical advantage", "not an adoption prerequisite", "preprints", "installed-large-toolchain"):
            self.assertIn(phrase, text)

    def test_algorithms_and_concepts_trigger_technology_topics(self) -> None:
        for prompt in ("採用最新演算法", "研究新概念與論文", "evaluate an algorithm", "apply a preprint concept", "experimental approach"):
            with self.subTest(prompt=prompt):
                self.assertIn("dependencies", infer_topics(prompt))

    def test_module_and_native_project_markers_detect_cpp(self) -> None:
        for filename in ("core.ixx", "core.mpp", "core.cppm", "app.vcxproj", "core.cxx", "core.cc"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                (project / filename).write_text("", encoding="utf-8")
                self.assertIn("cpp", discover_profile(project)["tags"])

    def test_theory_requires_no_measured_artifact(self) -> None:
        self.assertIsNone(validate_evidence([self.evidence()]))

    def test_theory_requires_bounded_explicit_reasoning(self) -> None:
        for field in ("baseline", "assumptions", "applicability"):
            for invalid in (None, "", "   ", "x" * 4001):
                item = self.evidence()
                item[field] = invalid
                with self.subTest(field=field, invalid=type(invalid).__name__), self.assertRaises(policy_error):
                    validate_evidence([item])
            item = self.evidence()
            del item[field]
            with self.assertRaises(policy_error):
                validate_evidence([item])

    def test_empirical_claim_still_needs_measurement(self) -> None:
        item = {key: value for key, value in self.evidence().items() if key not in {"baseline", "assumptions", "applicability"}}
        item["kind"] = "performance"
        with self.assertRaisesRegex(policy_error, "measured"):
            validate_evidence([item])
        item["artifact_sha256"] = "a" * 64
        self.assertIsNone(validate_evidence([item]))

    def test_theory_admission_keeps_independent_review_and_safe_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = policy_runtime(Path(directory) / "state")
            project = Path(directory) / "project"
            project.mkdir()
            old = runtime.context(project, "active", "algorithm", begin=True)["snapshot_id"]
            candidate = copy.deepcopy(load_catalog())
            major, minor, patch_version = map(int, candidate["payload"]["version"].split("."))
            candidate["payload"]["version"] = f"{major}.{minor}.{patch_version + 1}"
            next(rule for rule in candidate["payload"]["rules"] if rule["rule_id"] == "owner.latest")["details"] += " Fixture clarification."
            candidate["snapshot_id"] = digest(candidate["payload"])
            proposal = propose(runtime, candidate, "fixture_author", [self.evidence()], "low", "Fixture theory-only candidate preserves all core requirements.")
            self.assertEqual(proposal["evidence_status"], "submitted_not_independently_verified")
            with self.assertRaises(policy_error):
                publish(runtime, proposal["proposal_id"])
            with self.assertRaises(policy_error):
                review(runtime, proposal["proposal_id"], "fixture_author", True, "Fixture author is not an independent reviewer and must be rejected.", True)
            review(runtime, proposal["proposal_id"], "fixture_reviewer", True, "Fixture-only distinct reviewer attestation, not a claim of actual research review.", True)
            new = publish(runtime, proposal["proposal_id"])["snapshot_id"]
            self.assertNotEqual(new, old)
            self.assertEqual(runtime.context(project, "active")["snapshot_id"], old)
            runtime.finish(project, "active")
            self.assertEqual(runtime.context(project, "next", begin=True)["snapshot_id"], new)

    def test_packaged_skill_contains_same_amendments(self) -> None:
        files = plugin_files()
        common = files["skills/policy-governance/references/common.md"].decode()
        cpp = files["skills/policy-governance/references/cpp.md"].decode()
        self.assertIn("theoretical advantage", common)
        self.assertIn("export module module_name;", cpp)
        self.assertIn("module module_name;", cpp)
