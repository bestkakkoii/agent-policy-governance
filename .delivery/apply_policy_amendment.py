"""Apply the owner's explicit C++/latest-technology amendment to the exact baseline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
from policy_core.common import canonical, digest
from policy_core.engine import load_catalog

catalog = load_catalog(root / "policies/catalog.json")
if catalog["snapshot_id"] != "08cba5b9a39218449c769d90644644cf7f6d11973a96b08f0fdb30d38535d13d":
    raise RuntimeError("Unexpected policy baseline; reconcile concurrent changes first")


def replace(path: str, old: str, new: str) -> None:
    target = root / path
    text = target.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError("Expected one exact preimage in " + path)
    target.write_text(text.replace(old, new), encoding="utf-8", newline="\n")


updates = {
    "owner.latest": {
        "topics": ["always", "dependencies", "requirements", "network"],
        "statement": "Prefer and adopt the newest publicly released or published technologies, algorithms and concepts when reliable primary evidence and explicit reasoning support a theoretical advantage for the actual task; measured superiority is not an adoption prerequisite.",
        "details": "Include previews, experimental implementations, research papers, preprints and emerging designs, not just library versions. Do not wait for stability labels, popularity or mature benchmarks. Check publication/source identity, assumptions and applicability; implement a published idea when feasible rather than inventing an existing API. Preserve installed-large-toolchain limits, legal access, hard requirements and necessary correctness/security checks. Label expected benefits as theoretical until measured; record and pin available versions/commits for each run.",
        "source": "docs/policy_amendments.md#latest_technology",
    },
    "owner.cpp_modules": {
        "topics": ["always", "cpp", "requirements", "quality"],
        "statement": "All owned C++ core and interfaces require C++26 or a newer usable standard, including the latest available experimental mode, and a real named Modules/import/export architecture with toolchain-provided import std;.",
        "details": "Use export module module_name; for module interface units, export only intended public declarations, import module_name; at consumers, and module module_name; for implementation units. Separate public declarations and implementation definitions where practical; keep justified template/inline definitions in interfaces or appropriate partitions. Use the real standard-library module, never a fabricated stdmodule shim. Includes are limited to necessary SDK, third-party and non-module boundaries, not an alternate owned-core header architecture. Use the newest compatible installed compiler/SDK mode. Missing C++26, named-module or standard-library-module support is a blocker, not permission to downgrade or force a large toolchain installation.",
        "source": "docs/policy_amendments.md#cpp_modules",
    },
    "owner.performance": {
        "statement": "Preserve correctness and recoverability, remove useless work, and adopt theoretically better new algorithms or designs when credible reasoning fits the workload; do not require measured superiority before selection.",
        "details": "State assumptions and expected gains separately from observations. Claims of actual latency, throughput or footprint improvement require measurements. Perform risk-relevant correctness/security validation; separate instrumented and release builds. Never trade safety for undefined behavior or unbounded queues.",
        "source": "docs/policy_amendments.md#latest_technology",
    },
    "owner.evolution": {
        "statement": "Improve replaceable policies using reliable facts or theory-supported expected advantages, after independent risk-proportionate agent review. Published algorithms, new concepts and experimental technologies qualify without a prior measured win.",
        "details": "For theory evidence, record the primary source, comparison baseline, assumptions and task applicability. The reviewer checks the reasoning, not a nonexistent benchmark. Do not self-approve, alter core boundaries or fabricate evidence. Empirical performance claims still need measured artifacts; theoretical benefits remain explicitly unverified in the target environment. Required compatibility/correctness/security checks and safe-boundary activation remain; harmful changes require independent recovery review.",
        "source": "docs/policy_amendments.md#latest_technology",
    },
}
for rule in catalog["payload"]["rules"]:
    if rule["rule_id"] in updates:
        rule.update(updates.pop(rule["rule_id"]))
if updates:
    raise RuntimeError("Missing rule IDs: " + repr(updates))
catalog["payload"]["version"] = "0.2.1"
catalog["snapshot_id"] = digest(catalog["payload"])
(root / "policies/catalog.json").write_bytes(canonical(catalog) + b"\n")

replace("policy_core/common.py", 'version = "0.2.0"', 'version = "0.2.1"')
replace("tests/test_governance.py", 'value["payload"]["version"] = "0.2.1"',
        'major, minor, patch_version = map(int, value["payload"]["version"].split("."))\n        value["payload"]["version"] = f"{major}.{minor}.{patch_version + 1}"')
replace("tests/test_integrations.py", 'candidate["payload"]["version"] = "0.2.1"',
        'major, minor, patch_version = map(int, candidate["payload"]["version"].split("."))\n        candidate["payload"]["version"] = f"{major}.{minor}.{patch_version + 1}"')
replace("policy_core/engine.py", '".cpp": "cpp", ".cppm": "cpp", ".java": "java", ".uproject": "game"',
        '".cpp": "cpp", ".cppm": "cpp", ".ixx": "cpp", ".mpp": "cpp",\n                      ".cc": "cpp", ".cxx": "cpp", ".vcxproj": "cpp", ".java": "java", ".uproject": "game"')
replace("policy_core/engine.py", '"dependencies": ["library", "package", "dependency", "upgrade", "version", "函式庫", "技術", "升級", "依賴", "最新"],',
        '"dependencies": ["library", "package", "dependency", "upgrade", "version", "algorithm", "concept", "paper", "preprint", "experimental", "函式庫", "技術", "升級", "依賴", "最新", "演算法", "算法", "概念", "論文", "實驗性"],')
replace("policy_core/evolution.py", '''        require(isinstance(item, dict) and set(item) == {"url", "observed_on", "claim", "kind", "artifact_sha256"},
                "evidence_shape", "Evidence needs url, observed_on, claim, kind, artifact_sha256")''',
'''        require(isinstance(item, dict), "evidence_shape", "Evidence must be an object")
        fields = {"url", "observed_on", "claim", "kind", "artifact_sha256"}
        theory_fields = {"baseline", "assumptions", "applicability"}
        if item.get("kind") == "theory":
            fields |= theory_fields
        require(set(item) == fields, "evidence_shape", "Missing or unexpected evidence fields", expected=sorted(fields))
        if item.get("kind") == "theory":
            for field in sorted(theory_fields):
                require(isinstance(item[field], str) and 1 <= len(item[field].strip()) <= 4000,
                        "theory_reasoning", "Theory requires a comparison baseline, assumptions and task applicability", field=field)''')
replace("policy_core/evolution.py", '{"fact", "compatibility", "performance", "security"}',
        '{"fact", "compatibility", "performance", "security", "theory"}')

replace("README_AI.md", 'Use installed compatible toolchains; prefer verified newest supported technology and real upstream mainline dependencies, resolve once and pin during a run.',
        'Use installed compatible toolchains and prefer the newest published/released technologies, algorithms and concepts, including previews, experiments and research implementations. Reliable primary evidence plus explicit theoretical advantage for this task is sufficient to adopt; maturity labels, popularity and a measured win are not prerequisites. Record assumptions and applicability, distinguish expected benefits from empirical results, and preserve necessary compatibility/correctness/security checks. Use real upstream mainline dependencies, resolve once and pin during a run. C++ projects require C++26 or a newer usable/experimental mode, real import std;, named Modules/import/export and practical interface/implementation separation; no silent downgrade or forced large-toolchain upgrade.')
replace("README_AI.md", 'Bind evidence to the exact candidate; performance claims require measurements.',
        'Bind evidence to the exact candidate. Use kind=theory with baseline, assumptions and applicability for a theoretically advantageous published idea; no measured artifact is required. Empirical performance claims still require measurements. Explicit owner amendments are direct user authority, not an agent pretending to independently approve its own proposal. See docs/policy_amendments.md for the current amendment and the accepted evidence contract.')
replace("plugins/chatgpt/skills/policy-governance/SKILL.md", 'Select installed compatible large toolchains; verify newer supported technologies and actual upstream mainline revisions before claiming them current.',
        'Select installed compatible large toolchains; verify the newest publications/releases and actual upstream mainline revisions before claiming them current. Adopt new technologies, algorithms and concepts, including previews, experiments and published research, when reliable primary evidence and explicit task-relevant reasoning indicate a theoretical advantage; do not wait for measured superiority or stable labels. Keep theoretical benefits distinct from observed results and retain necessary compatibility/correctness/security checks. For C++ profiles, require C++26 or a newer usable experimental mode, real import std;, named Modules/import/export, and practical interface/implementation separation.')
replace("README.md", '**v0.2.0 是可安裝的預發行版', '**v0.2.1 是可安裝的預發行版')
replace("README.md", '## 已實作\n', '## 本次規範補充\n\nC++ 專案強制 C++26 或更新可用標準（包含實驗性模式）、真正的 `import std;`、`export module`／`import`／`export` 與合理的模組介面／實作分離。最新技術、演算法與新概念，只要有可靠來源與符合任務的理論優勢即可優先採用，不必等待成熟或先取得實測勝出；理論效果不得冒充已驗證成果。仍遵守現有大型工具鏈限制及必要的正確性／安全驗證。詳見 [規範修訂與證據契約](docs/policy_amendments.md)。\n\n## 已實作\n')

(root / "docs/policy_amendments.md").write_text('''# Owner-authorized policy amendments

Authority: explicit project-owner requests in the current conversation on 2026-10-29, supplementing the engineering instructions and whitepaper v6.3.1. This is an owner-authorized baseline change, not a claimed independent agent review. The immutable original whitepaper and its source hashes are unchanged. Execution authority remains policies/catalog.json; this record explains provenance and acceptance.

## cpp_modules

The owner requested mandatory C++26 or newer, including experimental modes, the real standard-library module, and Modules/import/export architecture. This amendment explicitly covers `export module module_name;`, public `export` declarations, consuming `import module_name;`, real `import std;`, and `module module_name;` implementation units. Separate interfaces/declarations from definitions where practical, retaining justified template/inline definitions or partitions. The requirement applies to C++ profiles, not unrelated languages, and is present even when the task prompt omits C++ keywords.

Use the newest applicable compiler/SDK already installed. Missing hard support is a blocker; do not create a fake `stdmodule`, fall back to owned header-only architecture/old standards, or force a large toolchain installation. This amendment is a policy requirement, not a claim that the governance runtime compiles or mechanically proves every C++ module graph.

## latest_technology

The owner's threshold is the newest publicly published or released technology with a credible theoretical advantage, explicitly including algorithms and new concepts. Stable releases, popularity, maturity, prior production use or a benchmark win are not admission gates. A published idea without an existing package may be implemented when feasible and legally usable in the actual environment. Publication alone does not prove an advantage: record the source, assumptions, baseline and workload applicability. Do not invent implementation availability, versions or APIs.

Selection and empirical claims are separate. Theory can justify adoption without a measured artifact; actual improvement claims require measurement. Necessary compatibility, correctness, security and recoverability checks remain. Existing installed-large-toolchain limits and hard product constraints take precedence. Apply changes to technology choices and architecture, not merely version numbers. Normal autonomous policy evolution retains genuinely independent risk-based review and safe-boundary activation; the owner need not participate in technical selection.

## theory_evidence_contract

Existing evidence kinds `fact`, `compatibility`, `performance`, and `security` retain their contract. New `kind: theory` accepts `artifact_sha256: null` and additionally requires nonempty `baseline`, `assumptions`, and `applicability` strings. It also retains `url`, `observed_on`, and `claim`. The claim must explicitly describe expected/theoretical benefit, not pretend to be a measurement. The independent reviewer checks the real primary source and reasoning. Schema acceptance is not proof that a theory is sound or that cited evidence was actually read.

A fixture example (not real research evidence):

```json
{"kind":"theory","url":"https://example.org/theory-fixture","observed_on":"2026-10-29","claim":"Expected lower work under the stated input assumptions; not measured on the target.","artifact_sha256":null,"baseline":"Current full-scan algorithm","assumptions":"Inputs are ordered and updates are sparse.","applicability":"The task already guarantees these input properties."}
```

## acceptance

- Latest-technology preference is in the compact common baseline, without loading all domain rules.
- C++ module/export requirements load for C++ profiles and never leak into a generic non-C++ profile.
- Chinese and English algorithm/concept/research prompts select relevant technology policies.
- Theory proposals without a measured artifact are accepted for independent review; incomplete reasoning, self-review, stale authority and unsupported empirical claims remain rejected.
- Python runtime, remote MCP policy view and packaged Skills share the same content-addressed catalog. References and selector fixtures are regenerated from it.
- Updating an existing installation preserves its admitted snapshot. The installing/maintenance agent must reconcile and admit a newer candidate under the existing review rules; do not claim a running device silently changed policy. New installations use the new bundled baseline. Active tasks switch only at a safe boundary.
''', encoding="utf-8", newline="\n")

(root / "docs/release_notes.md").write_text('''# v0.2.1 — newest technology and explicit C++ modules

Owner-authorized policy update: C++26 or newer usable/experimental modes, real `import std;`, `export module`, public `export`, consuming `import`, and practical module interface/implementation separation. C++ requirements now remain present for C++ profiles independently of prompt keywords; unrelated profiles are unaffected.

Prefer the newest published/released technologies, algorithms, concepts, previews and experiments on reliable task-relevant theoretical grounds. No stable-label, maturity or measured-superiority prerequisite. Theory evidence records baseline, assumptions and applicability without requiring a measured artifact; empirical performance claims still require measurements. Existing installed-large-toolchain constraints, necessary correctness/security checks, independent review and safe version switching remain.

Adds regression coverage for policy scope, module-project detection, theory admission and rejection paths, packaged Skills and the remote MCP view. Generated references and policy snapshot are refreshed from the single catalog. Existing native-host certification and ChatGPT public-hosting/Directory-approval limitations remain; no new claim of C++ compiler enforcement or measured model-token savings is made. Original source whitepaper hashes are unchanged. See docs/policy_amendments.md for authority and evidence semantics.
''', encoding="utf-8", newline="\n")

(root / "tests/test_policy_amendments.py").write_text('''"""Owner-amendment contracts; research URLs are fixtures, not verified evidence."""
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
''', encoding="utf-8", newline="\n")

with (root / "tests/registry.test.mjs").open("a", encoding="utf-8", newline="\n") as stream:
    stream.write('''\n// Verify public policy transport, not native C++ build or research truth.
test("owner amendment reaches remote common and C++ profile slices", async () => {
  const generic = (await (await call("policy_resolve", { tags: ["software"], topics: [] })).json()).result.structuredContent;
  assert.ok(generic.rules.find((rule) => rule.rule_id === "owner.latest").statement.includes("theoretical advantage"));
  assert.ok(!generic.rules.some((rule) => rule.rule_id === "owner.cpp_modules"));
  const cpp = (await (await call("policy_resolve", { tags: ["software", "cpp"], topics: [] })).json()).result.structuredContent;
  const rule = cpp.rules.find((entry) => entry.rule_id === "owner.cpp_modules");
  assert.ok(rule.details.includes("export module module_name;"));
  assert.ok(rule.details.includes("module module_name;"));
});
''')

# Refresh generated views only after loading the updated runtime version.
from tools.package import plugin_files
from policy_core.engine import select_rules
import policy_core.common as common
common.version = "0.2.1"
import tools.package as package
package.version = "0.2.1"
for name, content in plugin_files().items():
    target = root / "plugins/chatgpt" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
vectors_path = root / "tests/selector_vectors.json"
vectors = json.loads(vectors_path.read_text(encoding="utf-8"))
for vector in vectors:
    vector["rule_ids"] = [rule["rule_id"] for rule in select_rules(catalog, vector["tags"], vector["topics"])]
vectors_path.write_text(json.dumps(vectors, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"version": "0.2.1", "snapshot_id": catalog["snapshot_id"], "rules": len(catalog["payload"]["rules"])}))
