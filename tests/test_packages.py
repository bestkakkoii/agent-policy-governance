"""Publication safeguards and reproducible artifacts."""
import tempfile
import unittest
from pathlib import Path

from policy_core.common import policy_error
from tools.package import endpoint_valid, plugin_files, source_files, write_archive


class package_tests(unittest.TestCase):
    def test_packages_are_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            files = plugin_files()
            left, right = Path(directory) / "left.zip", Path(directory) / "right.zip"
            self.assertEqual(write_archive(left, files), write_archive(right, files))
            self.assertEqual(left.read_bytes(), right.read_bytes())

    def test_preview_has_distinct_identity_and_no_hooks_or_mcp(self) -> None:
        files = plugin_files()
        self.assertIn(b'agent-policy-governance-preview', files["plugin.json"])
        self.assertNotIn("mcp.json", files)
        self.assertFalse(any("hooks" in name or name.endswith(".py") for name in files))
        self.assertIn("skills/policy-governance/references/common.md", files)

    def test_production_requires_real_endpoint_and_separate_identity(self) -> None:
        for value in ["http://site.net/mcp", "https://localhost/mcp", "https://example.com/mcp", "https://127.0.0.1/mcp", "https://a.invalid/mcp", "https://name:secret@real.net/mcp"]:
            with self.subTest(value=value), self.assertRaises(policy_error):
                plugin_files(value)
        files = plugin_files("https://policies.actual-owner.net/mcp")
        self.assertIn("mcp.json", files)
        self.assertNotIn(b"-preview", files["plugin.json"])

    def test_public_source_excludes_private_state_and_original_zip(self) -> None:
        files = source_files()
        self.assertFalse(any(name.endswith((".sqlite3", ".zip", ".log", ".pyc")) or "whitepaper_source" in name for name in files))

    def test_codex_compaction_invalidates_then_restores_on_supported_event(self) -> None:
        from policy_core.runtime import policy_runtime
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            runtime = policy_runtime(base / "state")
            event = {"session_id":"compacted", "cwd":str(base), "hook_event_name":"UserPromptSubmit", "prompt":"verify quality"}
            self.assertIn("hookSpecificOutput", runtime.hook("codex",event))
            self.assertEqual(runtime.hook("codex",{**event,"hook_event_name":"PostCompact"}), {})
            restored = runtime.hook("codex",{**event,"hook_event_name":"PreToolUse","tool_name":"Read","tool_input":{}})
            self.assertIn("owner.evidence",restored["hookSpecificOutput"]["additionalContext"])
