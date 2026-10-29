"""Real loopback I/O, reversible configuration failure, and bounded update discovery."""
from __future__ import annotations

import io
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from policy_core.common import canonical, policy_error, read_json, write_json
from policy_core.engine import load_catalog
from policy_core.install import apply_plan, doctor, install, recover_journal
from policy_core.runtime import policy_runtime
from policy_core.service import local_server, execute_hybrid
from policy_core.sync import check_updates


class integration_tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="apg_integration_")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / "state"
        self.project = self.base / "project"
        self.project.mkdir()
        self.runtime = policy_runtime(self.home)

    def start_service(self) -> local_server:
        server = local_server(self.runtime)
        worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        worker.start()
        def cleanup() -> None:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)
        self.addCleanup(cleanup)
        self.url = f"http://127.0.0.1:{server.server_address[1]}/rpc"
        write_json(self.home / "service_endpoint.json", {"url": self.url, "token": server.token})
        return server

    def test_authenticated_loopback_reuses_same_policy_core(self) -> None:
        self.start_service()
        first = execute_hybrid(self.runtime, {"op": "context", "project": str(self.project), "session": "service", "task": "quality"})
        self.assertIn("owner.evidence", first["context"])
        self.assertEqual(self.runtime.context(self.project, "service", "quality")["context"], "")

    def test_loopback_rejects_missing_auth_origin_and_host(self) -> None:
        server = self.start_service()
        cases = [({}, 401), ({"Authorization": "Bearer " + server.token, "Origin": "https://example.net"}, 403),
                 ({"Authorization": "Bearer " + server.token, "Host": "evil.example"}, 403)]
        for headers, status in cases:
            request = urllib.request.Request(self.url, data=b'{"op":"health"}', headers={"Content-Type": "application/json", **headers})
            with self.subTest(headers=headers), self.assertRaises(urllib.error.HTTPError) as captured:
                urllib.request.urlopen(request, timeout=2)
            self.assertEqual(captured.exception.code, status)
            captured.exception.close()

    def test_invalid_service_receipt_never_contacts_external_host(self) -> None:
        write_json(self.home / "service_endpoint.json", {"url": "https://example.net/rpc", "token": "not_sent"})
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("External request attempted")), patch("sys.stderr", new=io.StringIO()):
            result = execute_hybrid(self.runtime, {"op": "context", "project": str(self.project), "session": "fallback"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["delivery"], "restored")

    def test_doctor_detects_missing_one_hook_not_only_all_hooks(self) -> None:
        user = self.base / "user"
        install(self.home, user, ["codex"], use_environment=False)
        path = user / ".codex/hooks.json"
        settings = read_json(path)
        del settings["hooks"]["PreToolUse"]
        write_json(path, settings)
        report = doctor(self.home)
        self.assertFalse(report["ok"])
        self.assertTrue(any(item.get("event") == "PreToolUse" for item in report["problems"]))

    def test_journal_restores_partial_apply_after_write_failure(self) -> None:
        left, right = self.base / "left.md", self.base / "right.md"
        left.write_bytes(b"before")
        from policy_core import install as installer
        original = installer.atomic_write
        def fail_second(path: Path, data: bytes, **kwargs) -> None:
            if path == right:
                raise OSError("Injected write failure")
            original(path, data, **kwargs)
        with patch.object(installer, "atomic_write", side_effect=fail_second), self.assertRaises(OSError):
            apply_plan(self.home, {left: b"after", right: b"new"})
        self.assertEqual(left.read_bytes(), b"before")
        self.assertFalse(right.exists())
        self.assertFalse((self.home / "install_journal.json").exists())

    def test_recovery_refuses_to_overwrite_user_edit(self) -> None:
        import base64
        target = self.base / "edited.md"
        target.write_bytes(b"new independent user work")
        write_json(self.home / "install_journal.json", {"files": [{"path": str(target), "before": base64.b64encode(b"before").decode(), "after": base64.b64encode(b"after").decode()}]})
        with self.assertRaises(policy_error):
            recover_journal(self.home)
        self.assertEqual(target.read_bytes(), b"new independent user work")

    def test_offline_sync_retains_valid_snapshot_and_logs_cause(self) -> None:
        write_json(self.home / "sync_settings.json", {"enabled": True})
        with patch("urllib.request.OpenerDirector.open", side_effect=OSError("offline fixture")):
            result = check_updates(self.runtime, force=True)
        self.assertEqual(result["state"], "offline_or_invalid")
        self.assertIn("offline fixture", result["reason"])
        self.assertEqual(self.runtime.context(self.project, "offline")["snapshot_id"], load_catalog()["snapshot_id"])

    def test_sync_pins_commit_and_does_not_activate_candidate(self) -> None:
        import copy
        from policy_core.common import digest
        candidate = copy.deepcopy(load_catalog())
        major, minor, patch_version = map(int, candidate["payload"]["version"].split("."))
        candidate["payload"]["version"] = f"{major}.{minor}.{patch_version + 1}"
        candidate["snapshot_id"] = digest(candidate["payload"])
        write_json(self.home / "sync_settings.json", {"enabled": True})
        responses = [io.BytesIO(b"a" * 40), io.BytesIO(canonical(candidate))]
        with patch("urllib.request.OpenerDirector.open", side_effect=responses) as requests:
            result = check_updates(self.runtime, force=True)
        self.assertIn("/" + "a" * 40 + "/policies/", requests.call_args_list[1].args[0].full_url)
        self.assertEqual(result["state"], "review_required")
        self.assertTrue(Path(result["candidate_path"]).exists())
        self.assertNotEqual(self.runtime.context(self.project, "sync")["snapshot_id"], candidate["snapshot_id"])
        with patch("urllib.request.OpenerDirector.open", side_effect=AssertionError("Duplicate poll")):
            self.assertEqual(check_updates(self.runtime)["state"], "review_required")


if __name__ == "__main__":
    unittest.main()
