"""Narrow, explicit project exceptions. Core invariants cannot be exempted."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import digest, require
from .engine import find_project
from .runtime import policy_runtime


def add_exception(runtime: policy_runtime, project: Path, rule_id: str, path: str, reason: str, evidence: str, actor: str) -> dict[str, Any]:
    project = find_project(project)
    relative = Path(path)
    require(not relative.is_absolute() and ".." not in relative.parts and "*" not in path and "?" not in path,
            "exception_scope", "An exception must name one exact project-relative path")
    require(path != "" and path != "." and len(reason) >= 20 and len(evidence) >= 12 and bool(actor.strip()),
            "exception_evidence", "An explicit scoped rationale, evidence and agent identity are required")
    record = {"project_key": runtime.project_key(project), "rule_id": rule_id, "path": relative.as_posix(),
              "reason": reason, "evidence": evidence, "actor": actor}
    with runtime.store.transaction() as connection:
        snapshot = runtime.store.get(connection, "setting", "desired_snapshot")
        catalog = runtime.catalog_for(connection, snapshot)
        matches = [rule for rule in catalog["payload"]["rules"] if rule["rule_id"] == rule_id]
        require(bool(matches), "unknown_rule", "Unknown exception rule")
        require(matches[0]["strength"] != "invariant", "core_invariant_exception", "Core invariants cannot be exempted")
        require(rule_id == "owner.naming", "exception_checker_unsupported", "Executable exceptions currently cover exact external naming contracts only; other exceptions remain review proposals")
        record["snapshot_id"] = snapshot
        exception_id = digest(record)
        runtime.store.put(connection, "exception", exception_id, record)
        runtime.store.audit(connection, "exception", {"exception_id": exception_id, "rule_id": rule_id, "path": record["path"], "actor": actor})
    return {"ok": True, "exception_id": exception_id, "scope": record}
