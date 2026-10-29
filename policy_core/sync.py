"""Read-only, commit-pinned remote download. Admission is a separate reviewed action."""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path
from typing import Any

from .common import decode_json, require, write_json
from .engine import validate_catalog

repository = "bestkakkoii/agent-policy-governance"


class no_redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        raise ValueError("A pinned policy download must not redirect to another origin/path")


def fetch_snapshot(home: Path, commit: str, expected_snapshot: str) -> dict[str, Any]:
    require(re.fullmatch(r"[a-f0-9]{40}", commit) is not None, "commit_required", "Use an exact inspected Git commit, not a moving branch")
    require(re.fullmatch(r"[a-f0-9]{64}", expected_snapshot) is not None, "snapshot_required", "Use the expected policy snapshot digest")
    url = f"https://raw.githubusercontent.com/{repository}/{commit}/policies/catalog.json"
    opener = urllib.request.build_opener(no_redirect)
    with opener.open(urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "agent_policy_governance"}), timeout=10) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    require(len(raw) <= 2 * 1024 * 1024, "snapshot_size", "Remote snapshot exceeds limit")
    envelope = validate_catalog(decode_json(raw))
    require(envelope["snapshot_id"] == expected_snapshot, "snapshot_mismatch", "Downloaded snapshot differs from the expected identity")
    destination = home / "candidates" / (expected_snapshot + ".json")
    write_json(destination, envelope, private=True)
    return {"ok": True, "candidate_path": str(destination), "snapshot_id": expected_snapshot, "git_commit": commit,
            "activated": False, "next": "independent_review_before_publication", "signature_verified": False}


def check_updates(runtime: Any, *, force: bool = False) -> dict[str, Any]:
    """Daily session-boundary discovery; fetch bytes once, never activate without review.

    Only the fixed repository name leaves the device. Failed checks are audited and
    retain the validated local snapshot. No background worker or scheduler is needed.
    """
    import time
    from .common import read_json
    settings_path = runtime.store.home / "sync_settings.json"
    if not settings_path.exists():
        return {"state": "not_installed"}
    settings = read_json(settings_path)
    if not settings.get("enabled", False):
        return {"state": "disabled"}
    now = time.time()
    with runtime.store.transaction() as connection:
        status = runtime.store.get(connection, "sync", "status") or {}
        due = max(settings.get("initial_check_after", 0), status.get("checked_at", 0) + settings.get("interval_seconds", 86400))
        if not force and now < due:
            return status or {"state": "not_due"}
        # Reserve the poll window before I/O so concurrent agents do not duplicate it.
        runtime.store.put(connection, "sync", "status", {**status, "checked_at": now, "state": "checking"})
    try:
        opener = urllib.request.build_opener(no_redirect)
        request = urllib.request.Request(f"https://api.github.com/repos/{repository}/commits/main",
                                         headers={"Accept": "application/vnd.github.sha", "User-Agent": "agent_policy_governance"})
        with opener.open(request, timeout=2) as response:
            body = response.read(1025).decode("utf-8").strip()
        require(re.fullmatch(r"[a-f0-9]{40}", body) is not None, "remote_commit_shape", "GitHub did not return a bounded commit identity")
        url = f"https://raw.githubusercontent.com/{repository}/{body}/policies/catalog.json"
        with opener.open(urllib.request.Request(url, headers={"User-Agent": "agent_policy_governance"}), timeout=2) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
        require(len(raw) <= 2 * 1024 * 1024, "snapshot_size", "Remote snapshot exceeds limit")
        envelope = validate_catalog(decode_json(raw))
        identity = envelope["snapshot_id"]
        with runtime.store.connection() as connection:
            desired = runtime.store.get(connection, "setting", "desired_snapshot")
        status = {"state": "current" if identity == desired else "review_required", "checked_at": now,
                  "git_commit": body, "snapshot_id": identity, "signature_verified": False}
        if identity != desired:
            path = runtime.store.home / "candidates" / (identity + ".json")
            write_json(path, envelope, private=True)
            status["candidate_path"] = str(path)
    except (OSError, ValueError, RuntimeError) as error:
        status = {"state": "offline_or_invalid", "checked_at": now, "error_type": type(error).__name__,
                  "reason": str(error), "recovery": "retain_verified_local_snapshot"}
    with runtime.store.transaction() as connection:
        runtime.store.put(connection, "sync", "status", status)
        runtime.store.audit(connection, "remote_version_check", status)
    return status
