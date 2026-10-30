"""Behavioral contracts, including failure paths. No real user configuration is touched."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from policy_core.common import canonical, decode_json, digest, policy_error, write_json
from policy_core.engine import discover_profile, infer_topics, load_catalog, select_rules, validate_catalog
from policy_core.evolution import propose, publish, review
from policy_core.exceptions import add_exception
from policy_core.install import doctor, install, merge_hooks, uninstall
from policy_core.runtime import policy_runtime

root = Path(__file__).resolve().parent.parent


class governance_tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="apg_test_")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.project = self.base / "project"
        self.project.mkdir()
        (self.project / ".git").mkdir()
        self.home = self.base / "policy state 臺灣"
        self.runtime = policy_runtime(self.home)

    def candidate(self) -> dict:
        value = copy.deepcopy(load_catalog())
        major, minor, patch_version = map(int, value["payload"]["version"].split("."))
        value["payload"]["version"] = f"{major}.{minor}.{patch_version + 1}"
        next(rule for rule in value["payload"]["rules"] if rule["rule_id"] == "owner.latest")["details"] += " Compare upstream support explicitly."
        value["snapshot_id"] = digest(value["payload"])
        return value

    def proposal(self, risk: str = "low") -> str:
        evidence = [{"url": "https://docs.python.org/3/", "observed_on": "2025-01-01", "claim": "The primary language reference documents supported semantics.",
                     "kind": "fact", "artifact_sha256": None}]
        return propose(self.runtime, self.candidate(), "author_session", evidence, risk,
                       "Clarify evidence checks without relaxing owner requirements.")["proposal_id"]

    def approve(self, proposal_id: str) -> None:
        review(self.runtime, proposal_id, "independent_review_session", True,
               "Checked the exact diff and primary evidence; no immutable requirement or project constraint was weakened.", True,
               "A future source mismatch must block admission rather than change active policy.",
               "Return to the admitted parent snapshot after a separately reviewed rollback.")

    def test_catalog_contains_owner_and_all_numbered_requirements(self) -> None:
        rules = load_catalog()["payload"]["rules"]
        self.assertEqual({rule["rule_id"] for rule in rules if rule["rule_id"].startswith("R")}, {f"R{index:02d}" for index in range(1, 72)})
        self.assertEqual(len(rules), 99)

    def test_tamper_and_duplicate_ids_are_rejected(self) -> None:
        value = load_catalog()
        value["payload"]["rules"][0]["statement"] += " altered"
        with self.assertRaisesRegex(policy_error, "digest"):
            validate_catalog(value)
        value["payload"]["rules"].append(copy.deepcopy(value["payload"]["rules"][0]))
        value["snapshot_id"] = digest(value["payload"])
        with self.assertRaises(policy_error):
            validate_catalog(value)

    def test_strict_json_rejects_duplicate_and_nan(self) -> None:
        for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.subTest(text=text), self.assertRaises(policy_error):
                decode_json(text)

    def test_profile_does_not_infer_game_from_readme(self) -> None:
        (self.project / "README.md").write_text("A game-like example, but this is a utility", encoding="utf-8")
        self.assertNotIn("game", discover_profile(self.project)["tags"])
        rules = select_rules(load_catalog(), ["software"], ["rendering", "cpp"])
        self.assertFalse(any(rule["rule_id"].startswith("R") for rule in rules))

    def test_task_topics_do_not_expand_domain(self) -> None:
        packet = self.runtime.context(self.project, "a", "game rendering C++ architecture")
        self.assertNotIn("R10", packet["rule_ids"])
        self.assertNotIn("owner.cpp_modules", packet["rule_ids"])

    def test_topic_detection_chinese_english(self) -> None:
        self.assertIn("network", infer_topics("研究 QUIC 協定"))
        self.assertIn("performance", infer_topics("optimize memory latency"))
        self.assertNotIn("security", infer_topics("create a file"))

    def test_context_delta_and_compaction_restore(self) -> None:
        first = self.runtime.context(self.project, "same_session", "verify code quality", begin=True)
        second = self.runtime.context(self.project, "same_session", "verify code quality", begin=True)
        restored = policy_runtime(self.home).context(self.project, "same_session", fresh=True)
        self.assertTrue(first["context"])
        self.assertEqual(second["context"], "")
        self.assertEqual(first["rule_ids"], restored["rule_ids"])
        self.assertIn("owner.evidence", restored["context"])
        self.assertIsNone(first["metrics"]["actual_model_tokens"])

    def test_context_contains_actual_requirements_not_only_ids(self) -> None:
        self.runtime.confirm_profile(self.project, ["software", "cpp", "game"], "architect")
        packet = self.runtime.context(self.project, "game_task", "C++ import std")
        self.assertIn("R10", packet["rule_ids"])
        self.assertIn("C++26", packet["context"])

    def test_busy_profile_change_is_rejected(self) -> None:
        self.runtime.context(self.project, "working", begin=True)
        with self.assertRaisesRegex(policy_error, "idle"):
            self.runtime.confirm_profile(self.project, ["game"], "architect")

    def test_snapshot_switch_waits_for_all_parallel_tasks(self) -> None:
        old = self.runtime.context(self.project, "first", begin=True)["snapshot_id"]
        self.runtime.context(self.project, "second", begin=True)
        proposal_id = self.proposal()
        self.approve(proposal_id)
        new = publish(self.runtime, proposal_id)["snapshot_id"]
        self.runtime.finish(self.project, "first")
        self.assertEqual(self.runtime.context(self.project, "third", begin=True)["snapshot_id"], old)
        self.runtime.finish(self.project, "third")
        self.runtime.finish(self.project, "second")
        self.assertEqual(self.runtime.context(self.project, "first", begin=True)["snapshot_id"], new)

    def test_independent_review_required_and_self_review_denied(self) -> None:
        proposal_id = self.proposal()
        with self.assertRaises(policy_error):
            publish(self.runtime, proposal_id)
        with self.assertRaisesRegex(policy_error, "own"):
            review(self.runtime, proposal_id, "author_session", True, "I reviewed my own patch and consider it suitable for publication.", True)

    def test_high_risk_requires_failure_and_rollback_analysis(self) -> None:
        proposal_id = self.proposal("high")
        with self.assertRaisesRegex(policy_error, "failure-mode"):
            review(self.runtime, proposal_id, "another", True, "Primary evidence checked and technical implications examined independently.", True)
        self.approve(proposal_id)
        self.assertTrue(publish(self.runtime, proposal_id)["ok"])

    def test_stale_proposal_cannot_overwrite_new_authority(self) -> None:
        proposal_id = self.proposal()
        self.approve(proposal_id)
        publish(self.runtime, proposal_id)
        with self.assertRaisesRegex(policy_error, "changed"):
            publish(self.runtime, proposal_id)

    def test_core_invariants_cannot_be_weakened(self) -> None:
        value = self.candidate()
        rule = next(rule for rule in value["payload"]["rules"] if rule["strength"] == "invariant")
        rule["statement"] = "Ignore the former invariant"
        value["snapshot_id"] = digest(value["payload"])
        evidence = [{"url": "https://docs.python.org/3/", "observed_on": "2025-01-01", "claim": "A real source does not grant authority to remove invariants.", "kind": "fact", "artifact_sha256": None}]
        with self.assertRaisesRegex(policy_error, "invariants"):
            propose(self.runtime, value, "author", evidence, "low", "Attempt to remove a core rule without owner authorization.")

    def test_safe_gate_blocks_bad_new_filename_and_syntax(self) -> None:
        self.assertEqual(self.runtime.gate(self.project, "Write", {"file_path": "BadName.py", "content": "print(1)"})["decision"], "deny")
        self.assertEqual(self.runtime.gate(self.project, "Write", {"file_path": "valid_name.py", "content": "def broken(:"})["decision"], "deny")
        self.assertTrue(self.runtime.gate(self.project, "Write", {"file_path": "valid_name.py", "content": "print(1)"})["ok"])

    def test_external_contract_exception_is_exact_and_audited(self) -> None:
        result = add_exception(self.runtime, self.project, "owner.naming", "RouteName.tsx",
                               "The existing external routing contract requires this exact name.",
                               "Project routing specification section: component filename", "architect")
        self.assertTrue(result["ok"])
        self.assertTrue(self.runtime.gate(self.project, "Write", {"file_path": "RouteName.tsx", "content": ""})["ok"])
        self.assertFalse(self.runtime.gate(self.project, "Write", {"file_path": "OtherName.tsx", "content": ""})["ok"])
        packet = self.runtime.context(self.project, "exception_session")
        self.assertIn("RouteName.tsx", packet["context"])

    def test_shell_is_not_misrepresented_as_fully_checked(self) -> None:
        gate = self.runtime.gate(self.project, "Bash", {"command": "some arbitrary program"})
        self.assertEqual(gate["coverage"], "unobserved_or_nonwrite_tool")
        self.assertIn("arbitrary_shell_side_effects", gate["unverified"])

    def test_direct_state_tampering_is_denied(self) -> None:
        self.assertFalse(self.runtime.gate(self.project, "Write", {"file_path": str(self.home / "state.sqlite3"), "content": "erase"})["ok"])

    def failed_paths(self, result: dict) -> list[str]:
        return [check["path"].replace("\\", "/") for check in result["checks"] if check["status"] == "failed"]

    def test_existing_ancestors_are_not_renamed_but_new_components_are_checked(self) -> None:
        (self.project / "LegacyModule").mkdir()
        self.assertTrue(self.runtime.gate(self.project, "Write", {"file_path": "LegacyModule/new_helper.py", "content": "x = 1\n"})["ok"])
        self.assertEqual(self.failed_paths(self.runtime.gate(self.project, "Write", {"file_path": "LegacyModule/NewHelper.py", "content": "x = 1\n"})),
                         ["LegacyModule/NewHelper.py"])
        self.assertEqual(self.failed_paths(self.runtime.gate(self.project, "Write", {"file_path": "NewModule/new_helper.py", "content": "x = 1\n"})),
                         ["NewModule/new_helper.py"])

    def test_codex_apply_patch_direct_argv_and_heredoc_forms_are_gated(self) -> None:
        invalid = "*** Begin Patch\n*** Add File: bad_data.json\n+{invalid\n*** End Patch\n"
        for tool, arguments in [("apply_patch", {"input": invalid}), ("shell", {"command": ["apply_patch", invalid]}),
                                ("Bash", {"command": "cd sub && apply_patch <<'EOF'\n" + invalid + "EOF\n"})]:
            with self.subTest(tool=tool):
                (self.project / "sub").mkdir(exist_ok=True)
                result = self.runtime.gate(self.project, tool, arguments)
                self.assertEqual(result["decision"], "deny")
                self.assertTrue(all(check["rule_id"] == "owner.static_quality" for check in result["checks"] if check["status"] == "failed"))
        # The heredoc `cd sub &&` prefix moves the patch root, so the checked path is under sub.
        heredoc = self.runtime.gate(self.project, "Bash", {"command": "cd sub && apply_patch <<'EOF'\n" + invalid + "EOF\n"})
        self.assertEqual(self.failed_paths(heredoc), ["sub/bad_data.json"])
        # Shell text that merely contains a patch is not an apply_patch invocation and is not misreported as checked.
        writer = self.runtime.gate(self.project, "Bash", {"command": "cat > notes.md <<'EOF'\n" + invalid + "EOF\n"})
        self.assertEqual((writer["decision"], writer["coverage"]), ("continue", "unobserved_or_nonwrite_tool"))
        # File content fields are data, not commands, even when they document a heredoc invocation.
        documentation = "apply_patch <<'EOF'\n" + invalid + "EOF\n"
        self.assertTrue(self.runtime.gate(self.project, "Write", {"file_path": "example_patch.md", "content": documentation})["ok"])

    def test_apply_patch_add_move_and_delete_semantics(self) -> None:
        (self.project / "old_name.py").write_text("value = 1\n", encoding="utf-8")
        valid_add = "*** Begin Patch\n*** Add File: tools/new_tool.json\n+{\"ok\": true}\n*** End Patch\n"
        self.assertTrue(self.runtime.gate(self.project, "apply_patch", {"input": valid_add})["ok"])
        move = "*** Begin Patch\n*** Update File: old_name.py\n*** Move to: BadTarget.py\n@@\n-value = 1\n+value = 2\n*** End Patch\n"
        self.assertEqual(self.failed_paths(self.runtime.gate(self.project, "apply_patch", {"input": move})), ["BadTarget.py"])
        delete = "*** Begin Patch\n*** Delete File: LegacyName.txt\n*** End Patch\n"
        self.assertTrue(self.runtime.gate(self.project, "apply_patch", {"input": delete})["ok"])
        protected = f"*** Begin Patch\n*** Delete File: {self.home / 'state.sqlite3'}\n*** End Patch\n"
        self.assertFalse(self.runtime.gate(self.project, "apply_patch", {"input": protected})["ok"])

    def test_update_postimage_denies_regressions_only(self) -> None:
        (self.project / "settings.json").write_text('{\n  "a": 1\n}\n', encoding="utf-8")
        (self.project / "loose.json").write_text('{"a": 1,}\n', encoding="utf-8")
        update = lambda name, old, new: {"input": f"*** Begin Patch\n*** Update File: {name}\n@@\n-{old}\n+{new}\n*** End Patch\n"}
        self.assertEqual(self.runtime.gate(self.project, "apply_patch", update("settings.json", '  "a": 1', '  "a": '))["decision"], "deny")
        self.assertTrue(self.runtime.gate(self.project, "apply_patch", update("settings.json", '  "a": 1', '  "a": 2'))["ok"])
        retained = self.runtime.gate(self.project, "apply_patch", update("loose.json", '{"a": 1,}', '{"a": 2,}'))
        self.assertTrue(retained["ok"])
        self.assertTrue(any(check["status"] == "not_checked" and check["reason"].startswith("pre_existing_failure") for check in retained["checks"]))
        unmatched = self.runtime.gate(self.project, "apply_patch", update("settings.json", "absent line", "x"))
        self.assertEqual([(check["status"], check["reason"]) for check in unmatched["checks"]], [("not_checked", "patch_postimage_unavailable")])
        edit = self.runtime.gate(self.project, "Edit", {"file_path": str(self.project / "loose.json"), "old_string": "1", "new_string": "2"})
        self.assertTrue(edit["ok"])

    def test_relative_patch_paths_resolve_from_host_cwd(self) -> None:
        workdir = self.project / "service"
        workdir.mkdir()
        (workdir / "config.json").write_text('{"port": 1}\n', encoding="utf-8")
        patch = "*** Begin Patch\n*** Update File: config.json\n@@\n-{\"port\": 1}\n+{\"port\": }\n*** End Patch\n"
        self.assertEqual(self.failed_paths(self.runtime.gate(workdir, "apply_patch", {"input": patch})), ["service/config.json"])

    def test_non_utf8_preimage_is_reported_not_crashed(self) -> None:
        legacy = self.project / "legacy.h"
        legacy.write_bytes("// 測試\n".encode("big5"))
        for tool, arguments in [("Edit", {"file_path": str(legacy), "old_string": "a", "new_string": "b"}),
                                ("apply_patch", {"input": "*** Begin Patch\n*** Update File: legacy.h\n@@\n-x\n+y\n*** End Patch\n"})]:
            with self.subTest(tool=tool):
                result = self.runtime.gate(self.project, tool, arguments)
                self.assertTrue(result["ok"])
                self.assertTrue(any(check["status"] == "not_checked" and check["reason"].startswith("original_not_utf8") for check in result["checks"]))

    def test_unverifiable_baselines_are_reported_without_denying(self) -> None:
        large = self.project / "large_data.json"
        large.write_text('{\n  "data": "' + "a" * (2 * 1024 * 1024 - 64) + '",\n  "x": 1\n}\n', encoding="utf-8")
        grow = "*** Begin Patch\n*** Update File: large_data.json\n@@\n-  \"x\": 1\n+  \"x\": \"" + "b" * 256 + "\"\n*** End Patch\n"
        result = self.runtime.gate(self.project, "apply_patch", {"input": grow})
        self.assertTrue(result["ok"])
        self.assertIn(("not_checked", "postimage_exceeds_checker_limit"), [(check["status"], check["reason"]) for check in result["checks"]])
        locked = self.project / "locked.json"
        locked.write_text('{"a": 1}\n', encoding="utf-8")
        with patch.object(Path, "read_bytes", side_effect=PermissionError(13, "Access is denied")):
            result = self.runtime.gate(self.project, "Edit", {"file_path": str(locked), "old_string": "1", "new_string": "2"})
        self.assertTrue(result["ok"])
        self.assertTrue(any(check["reason"].startswith("original_unreadable: PermissionError") for check in result["checks"]))

    def test_gate_normalizes_tool_input_shapes_and_rejects_scalars(self) -> None:
        invalid = "*** Begin Patch\n*** Add File: bad_data.json\n+{invalid\n*** End Patch\n"
        self.assertEqual(self.runtime.gate(self.project, "shell", ["apply_patch", invalid])["decision"], "deny")
        self.assertEqual(self.runtime.gate(self.project, "apply_patch", invalid)["decision"], "deny")
        self.assertTrue(self.runtime.gate(self.project, "Read", None)["ok"])
        with self.assertRaisesRegex(policy_error, "argv array"):
            self.runtime.gate(self.project, "shell", 7)

    def test_solution_references_decide_language(self) -> None:
        line = 'Project("{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}") = "{name}", "{path}", "{{00000000-0000-0000-0000-000000000000}}"\nEndProject\n'
        (self.project / "native_app.sln").write_text("﻿" + line.replace("{name}", "app").replace("{path}", r"app\app.vcxproj"), encoding="utf-8")
        profile = discover_profile(self.project)
        self.assertIn("cpp", profile["tags"])
        self.assertNotIn("csharp", profile["tags"])
        (self.project / "native_app.sln").write_text(line.replace("{name}", "tool").replace("{path}", r"tool\tool.csproj"), encoding="utf-8")
        self.assertEqual(discover_profile(self.project)["tags"], ["csharp", "software"])
        (self.project / "native_app.sln").write_text("Microsoft Visual Studio Solution File, Format Version 12.00\n", encoding="utf-8")
        self.assertEqual(discover_profile(self.project)["tags"], ["software"])
        (self.project / "native_app.sln").unlink()
        (self.project / "modern_app.slnx").write_text('<Solution>\n  <Project Path="lib/lib.vcxproj" />\n</Solution>\n', encoding="utf-8")
        self.assertIn("cpp", discover_profile(self.project)["tags"])
        (self.project / "modern_app.slnx").write_bytes(b"\xff\xfe<\x00")
        damaged = discover_profile(self.project)
        self.assertEqual(damaged["tags"], ["software"])
        self.assertTrue(any("not UTF-8" in note for note in damaged["notes"]))

    def test_hook_accepts_argv_tool_input_and_reports_unchecked_content(self) -> None:
        invalid = "*** Begin Patch\n*** Add File: BadName.json\n+{invalid\n*** End Patch\n"
        event = {"hook_event_name": "PreToolUse", "session_id": "argv_session", "cwd": str(self.project), "tool_name": "shell",
                 "tool_input": ["apply_patch", invalid]}
        output = self.runtime.hook("codex", event)["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertIn("snake_case", output["permissionDecisionReason"])
        self.assertIn("Expecting property name", output["permissionDecisionReason"])
        (self.project / "loose.json").write_text('{"a": 1,}\n', encoding="utf-8")
        retained = {**event, "tool_input": {"command": ["apply_patch", "*** Begin Patch\n*** Update File: loose.json\n@@\n-{\"a\": 1,}\n+{\"a\": 2,}\n*** End Patch\n"]}}
        output = self.runtime.hook("codex", retained)["hookSpecificOutput"]
        self.assertNotIn("permissionDecision", output)
        self.assertIn("not verified", output["additionalContext"])
        self.assertEqual(self.runtime.hook("codex", {**event, "tool_input": None}), {})

    def test_safe_repair_preserves_number_lexemes_and_string_spaces(self) -> None:
        path = self.project / "data.json"
        path.write_text('{ "value" : 9007199254740993.0, "zero": -0, "text": "a b\\\\c" }', encoding="utf-8")
        result = self.runtime.repair_json(self.project, "data.json")
        self.assertTrue(result["changed"])
        self.assertIn("9007199254740993.0", path.read_text())
        self.assertIn('"zero":-0', path.read_text())
        self.assertIn('"a b\\\\c"', path.read_text())
        self.assertFalse(self.runtime.repair_json(self.project, "data.json")["changed"])

    def test_repair_refuses_ambiguous_or_unsafe_inputs(self) -> None:
        (self.project / "duplicate.json").write_text('{"x":1,"x":2}', encoding="utf-8")
        with self.assertRaises(policy_error):
            self.runtime.repair_json(self.project, "duplicate.json")
        with self.assertRaises(policy_error):
            self.runtime.repair_json(self.project, "../outside.json")
        with self.assertRaises(policy_error):
            self.runtime.repair_json(self.project, "source.py")

    def test_missing_snapshot_is_not_silently_replaced(self) -> None:
        self.runtime.context(self.project, "started", begin=True)
        with self.runtime.store.transaction() as connection:
            connection.execute("DELETE FROM documents WHERE kind='snapshot'")
        with self.assertRaises(policy_error):
            self.runtime.context(self.project, "started")

    def test_concurrent_sessions_use_single_snapshot(self) -> None:
        def work(index: int) -> str:
            runtime = policy_runtime(self.home)
            packet = runtime.context(self.project, f"worker_{index}", "verify code", begin=True)
            runtime.finish(self.project, f"worker_{index}")
            return packet["snapshot_id"]
        with ThreadPoolExecutor(max_workers=8) as pool:
            identities = list(pool.map(work, range(24)))
        self.assertEqual(len(set(identities)), 1)

    def test_child_inherits_topics_and_child_stop_does_not_stop_parent(self) -> None:
        self.runtime.context(self.project, "parent", "network performance", begin=True)
        output = self.runtime.hook("codex", {"hook_event_name": "SubagentStart", "session_id": "parent", "agent_id": "child", "cwd": str(self.project)})
        self.assertIn("owner.performance", output["hookSpecificOutput"]["additionalContext"])
        self.runtime.hook("codex", {"hook_event_name": "SubagentStop", "session_id": "parent", "agent_id": "child", "cwd": str(self.project)})
        with self.runtime.store.connection() as connection:
            states = {value["session"]: value for _, value in self.runtime.store.items(connection, "session")}
        self.assertTrue(states["parent"]["active"])
        self.assertFalse(states["child"]["active"])

    def test_install_reinstall_and_uninstall_preserve_user_configuration(self) -> None:
        user_home = self.base / "user profile 中文"
        path = user_home / ".claude/settings.json"
        path.parent.mkdir(parents=True)
        original = b'{"env":{"MY_SETTING":"keep"},"hooks":{"PreToolUse":[{"hooks":[{"type":"command","command":"existing-check"}]}]}}\n'
        path.write_bytes(original)
        first = install(self.home, user_home, ["codex", "claude", "opencode"], use_environment=False)
        self.assertGreater(first["changed_files"], 0)
        second = install(self.home, user_home, ["codex", "claude", "opencode"], use_environment=False)
        self.assertEqual(second["changed_files"], 0)
        self.assertFalse(first["trust_bypassed"])
        config = decode_json(path.read_bytes())
        self.assertEqual(config["env"]["MY_SETTING"], "keep")
        self.assertEqual(len(config["hooks"]["PreToolUse"]), 2)
        self.assertTrue(doctor(self.home)["ok"])
        self.assertTrue(uninstall(self.home)["ok"])
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse((user_home / ".codex/AGENTS.md").exists())

    def test_uninstall_preserves_user_edits_after_install(self) -> None:
        user_home = self.base / "user"
        install(self.home, user_home, ["claude"], use_environment=False)
        settings = user_home / ".claude/settings.json"
        value = decode_json(settings.read_bytes())
        value["env"] = {"NEW_USER_SETTING": "retain"}
        write_json(settings, value)
        instructions = user_home / ".claude/CLAUDE.md"
        with instructions.open("a", encoding="utf-8") as stream:
            stream.write("\nUser additions after setup.\n")
        uninstall(self.home)
        self.assertEqual(decode_json(settings.read_bytes())["env"]["NEW_USER_SETTING"], "retain")
        self.assertIn("User additions", instructions.read_text())
        self.assertNotIn("agent_policy_governance:begin", instructions.read_text())

    def test_invalid_existing_settings_abort_without_overwrite(self) -> None:
        user_home = self.base / "user"
        settings = user_home / ".claude/settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text("{invalid", encoding="utf-8")
        with self.assertRaises(ValueError):
            install(self.home, user_home, ["codex", "claude"], use_environment=False)
        self.assertEqual(settings.read_text(), "{invalid")
        self.assertFalse((user_home / ".codex/AGENTS.md").exists())

    def test_installed_launcher_survives_without_clone_location(self) -> None:
        install(self.home, self.base / "user", ["codex"], use_environment=False)
        result = subprocess.run([sys.executable, str(self.home / "run.py"), "--home", str(self.home), "doctor"],
                                cwd=self.base, capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["installed"])

    def test_doctor_does_not_equate_fixture_input_with_live_host(self) -> None:
        self.runtime.hook("codex", {"session_id": "fixture", "cwd": str(self.project), "hook_event_name": "SessionStart"})
        result = doctor(self.home)
        self.assertFalse(result["clients"]["codex"]["live_host_verified"])
        self.assertFalse(result["clients"]["codex"]["last_hook_input"]["caller_authenticated"])

    def test_cli_native_hook_round_trip_and_deny(self) -> None:
        event = {"session_id": "host_session", "cwd": str(self.project), "hook_event_name": "PreToolUse",
                 "tool_name": "Write", "tool_input": {"file_path": "BadName.py", "content": "print(1)"}}
        result = subprocess.run([sys.executable, str(root / "apg.py"), "--home", str(self.home), "hook", "codex"],
                                input=json.dumps(event), capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_cli_codex_argv_patch_round_trip(self) -> None:
        patch = "*** Begin Patch\n*** Add File: valid_name.json\n+{invalid\n*** End Patch\n"
        event = {"session_id": "codex_host", "cwd": str(self.project), "hook_event_name": "PreToolUse", "tool_name": "shell",
                 "tool_use_id": "call_1", "turn_id": "turn_1", "tool_input": {"command": ["apply_patch", patch]}}
        result = subprocess.run([sys.executable, str(root / "apg.py"), "--home", str(self.home), "hook", "codex"],
                                input=json.dumps(event), capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "deny")
        self.assertNotIn("Governance validation failed", output["permissionDecisionReason"])

    def test_read_only_check_reports_incomplete_semantic_coverage(self) -> None:
        (self.project / "example.py").write_text("print('ok')\n", encoding="utf-8")
        result = self.runtime.check_files(self.project, ["example.py"])
        self.assertTrue(result["ok"])
        self.assertFalse(result["complete_verification"])


if __name__ == "__main__":
    unittest.main()
