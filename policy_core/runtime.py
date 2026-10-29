"""Session-aware context, safe-boundary versioning, and supported tool checks."""
from __future__ import annotations

import ast
import re
import time
from pathlib import Path
from typing import Any

from .common import atomic_write, byte_digest, canonical, decode_json, digest, policy_error, require, state_store
from .engine import discover_profile, find_project, format_context, infer_topics, load_catalog, select_rules, validate_catalog

known_file_names = {
    "README_AI.md", "README.md", "AGENTS.md", "CLAUDE.md", "SKILL.md", "LICENSE", "NOTICE",
    "Dockerfile", "Makefile", "CMakeLists.txt", "CMakePresets.json", "CMakeUserPresets.json",
    "CHANGELOG.md", "__init__.py", "__main__.py", ".gitignore", ".gitattributes", ".editorconfig",
}
source_suffixes = {".py", ".rs", ".go", ".c", ".h", ".hpp", ".cpp", ".cppm", ".ixx", ".cs", ".java", ".ts", ".tsx", ".js", ".mjs", ".json", ".md"}
write_tools = {"write", "edit", "multiedit", "apply_patch", "write_file", "replace_in_file"}


def validate_new_path(project: Path, target: Path) -> list[dict[str, Any]]:
    results = []
    try:
        relative = target.relative_to(project)
    except ValueError:
        return [{"rule_id": "owner.naming", "status": "not_checked", "reason": "outside_project_ownership"}]
    for part in relative.parts:
        if part in known_file_names or part.startswith("."):
            continue
        stem = part.split(".")[0]
        if not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", stem):
            results.append({"rule_id": "owner.naming", "status": "failed", "path": str(relative),
                            "reason": "New owned paths require semantic lowercase snake_case; keep exact external contracts as narrow exceptions."})
            break
    return results


def validate_text(path: Path, text: str) -> list[dict[str, Any]]:
    results = []
    if "\x00" in text:
        results.append({"rule_id": "owner.encoding", "status": "failed", "reason": "NUL in a source text file"})
    try:
        if path.suffix == ".py":
            ast.parse(text, filename=path.name)
        elif path.suffix == ".json":
            decode_json(text)
    except (SyntaxError, ValueError, policy_error) as error:
        results.append({"rule_id": "owner.static_quality", "status": "failed", "reason": str(error)})
    return results


class policy_runtime:
    def __init__(self, home: Path, catalog: Path | None = None) -> None:
        self.store = state_store(home)
        self.bundle = load_catalog(catalog)
        snapshot = self.bundle["snapshot_id"]
        with self.store.transaction() as connection:
            existing = self.store.get(connection, "snapshot", snapshot)
            if existing is not None:
                validate_catalog(existing)
            else:
                self.store.put(connection, "snapshot", snapshot, self.bundle)
            if self.store.get(connection, "setting", "desired_snapshot") is None:
                self.store.put(connection, "setting", "desired_snapshot", snapshot)

    @staticmethod
    def project_key(project: Path) -> str:
        return digest(str(find_project(project)))

    def catalog_for(self, connection: Any, snapshot: str) -> dict[str, Any]:
        value = self.store.get(connection, "snapshot", snapshot)
        require(value is not None, "snapshot_missing", "Pinned policy snapshot is unavailable", snapshot_id=snapshot)
        return validate_catalog(value)

    def stage(self, envelope: dict[str, Any], *, expected_base: str) -> dict[str, Any]:
        """Low-level publication primitive. CLI evolution calls it only after review."""
        validate_catalog(envelope)
        with self.store.transaction() as connection:
            current = self.store.get(connection, "setting", "desired_snapshot")
            require(current == expected_base, "stale_policy_base", "Authority changed; rebase and review again", current=current)
            snapshot = envelope["snapshot_id"]
            self.store.put(connection, "snapshot", snapshot, envelope)
            self.store.put(connection, "setting", "desired_snapshot", snapshot)
            self.store.audit(connection, "snapshot_staged", {"base": current, "snapshot_id": snapshot})
        return {"ok": True, "snapshot_id": snapshot, "activation": "next_quiescent_task_boundary"}

    def confirm_profile(self, project: Path, tags: list[str], actor: str) -> dict[str, Any]:
        project = find_project(project)
        require(actor.strip() != "" and len(actor) <= 256, "actor_required", "A real agent/session identity is required")
        require(bool(tags) and len(tags) <= 64 and all(re.fullmatch(r"[a-z][a-z0-9_]*", tag) for tag in tags),
                "profile_tags", "Invalid profile tags")
        key = self.project_key(project)
        with self.store.transaction() as connection:
            sessions = [value for _, value in self.store.items(connection, "session") if value["project_key"] == key]
            require(not any(value["active"] for value in sessions), "profile_busy", "Confirm profile at an idle task boundary")
            profile = discover_profile(project)
            profile.update(tags=sorted(set(tags) | {"software"}), confirmation="confirmed", confirmed_by=actor)
            self.store.put(connection, "profile", key, profile)
            self.store.audit(connection, "profile_confirmed", {"project_key": key, "tags": profile["tags"], "actor": actor})
        return profile

    def context(self, project: Path, session: str, task: str = "", *, fresh: bool = False,
                begin: bool = False, full: bool = False, parent_session: str | None = None) -> dict[str, Any]:
        require(bool(session) and len(session) <= 256, "session_required", "Use a stable host session ID")
        require(len(task) <= 131072, "task_too_large", "Task metadata is too large")
        project = find_project(project)
        key = self.project_key(project)
        session_key = digest([key, session])
        with self.store.transaction() as connection:
            profile = self.store.get(connection, "profile", key)
            if profile is None:
                profile = discover_profile(project)
                # The detector records conservative facts; domain expansion requires an agent decision.
                self.store.put(connection, "profile", key, profile)
            desired = self.store.get(connection, "setting", "desired_snapshot")
            project_state = self.store.get(connection, "project", key) or {"snapshot_id": desired}
            peers = [value for _, value in self.store.items(connection, "session") if value["project_key"] == key]
            if not any(value["active"] for value in peers):
                project_state["snapshot_id"] = desired
            snapshot = project_state["snapshot_id"]
            self.store.put(connection, "project", key, project_state)
            catalog = self.catalog_for(connection, snapshot)
            previous = self.store.get(connection, "session", session_key)
            current = previous or {"project_key": key, "session": session, "active": False,
                                   "snapshot_id": snapshot, "topics": [], "delivered": {},
                                   "injected_bytes": 0, "packets": 0}
            previous_active = current["active"]
            if current["snapshot_id"] != snapshot:
                current.update(snapshot_id=snapshot, delivered={})
                fresh = True
            topics = set(current["topics"])
            if previous is None and parent_session:
                parent = self.store.get(connection, "session", digest([key, parent_session]))
                if parent:
                    topics.update(parent["topics"])
            if task:
                if begin and not previous_active:
                    topics.clear()
                topics.update(infer_topics(task))
            current["topics"] = sorted(topics)
            current["active"] = previous_active or begin
            applicable = select_rules(catalog, profile["tags"], current["topics"], full=full)
            for identity, exception in self.store.items(connection, "exception"):
                if exception["project_key"] == key and exception["snapshot_id"] == snapshot:
                    applicable.append({"rule_id": "exception." + identity, "strength": "conditional",
                                       "statement": f"Exact-path exception to {exception['rule_id']}: {exception['path']}",
                                       "details": exception["reason"] + "; evidence: " + exception["evidence"]})
            fingerprints = {rule["rule_id"]: digest(rule) for rule in applicable}
            removed = sorted(set(current["delivered"]) - set(fingerprints))
            delta = [rule for rule in applicable if fresh or current["delivered"].get(rule["rule_id"]) != fingerprints[rule["rule_id"]]]
            text = format_context(snapshot, profile, delta, removed=removed) if delta or removed or fresh else ""
            if text:
                identity = canonical({"session": session, "project": str(project), "profile_confirmation": profile["confirmation"]}).decode()
                text = "APG local runtime identity: " + identity + "\n" + text
            current.update(delivered=fingerprints, updated=time.time())
            current["injected_bytes"] += len(text.encode("utf-8"))
            current["packets"] += bool(text)
            self.store.put(connection, "session", session_key, current)
            self.store.audit(connection, "context", {"session_key": session_key, "snapshot_id": snapshot,
                             "delta_rule_count": len(delta), "injected_bytes": len(text.encode("utf-8"))})
        return {"ok": True, "snapshot_id": snapshot, "profile": profile, "context": text,
                "rule_ids": list(fingerprints), "delta_rule_ids": [rule["rule_id"] for rule in delta],
                "removed_rule_ids": removed, "delivery": "restored" if fresh else "delta",
                "metrics": {"injected_bytes": len(text.encode("utf-8")), "session_injected_bytes": current["injected_bytes"],
                            "actual_model_tokens": None}, "enforcement": "supported_checks_only"}

    def finish(self, project: Path, session: str) -> dict[str, Any]:
        key = digest([self.project_key(project), session])
        with self.store.transaction() as connection:
            current = self.store.get(connection, "session", key)
            if current:
                current["active"] = False
                self.store.put(connection, "session", key, current)
                self.store.audit(connection, "safe_boundary", {"session_key": key, "snapshot_id": current["snapshot_id"]})
        return {"ok": True, "boundary": "idle", "session": session}

    def explain(self, rule_ids: list[str], snapshot: str | None = None) -> dict[str, Any]:
        require(0 < len(rule_ids) <= 128, "rule_ids_required", "Request one to 128 rule IDs")
        with self.store.connection() as connection:
            snapshot = snapshot or self.store.get(connection, "setting", "desired_snapshot")
            catalog = self.catalog_for(connection, snapshot)
        by_id = {rule["rule_id"]: rule for rule in catalog["payload"]["rules"]}
        missing = sorted(set(rule_ids) - set(by_id))
        require(not missing, "unknown_rule", "Unknown rule IDs", missing=missing)
        return {"ok": True, "snapshot_id": snapshot, "rules": [by_id[key] for key in rule_ids]}

    def gate(self, project: Path, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        project = find_project(project)
        normalized = tool.casefold().split(".")[-1]
        checks: list[dict[str, Any]] = []
        targets: list[tuple[Path, str | None]] = []
        if normalized in write_tools:
            raw_path = arguments.get("file_path", arguments.get("filePath", arguments.get("path")))
            content = arguments.get("content")
            if isinstance(raw_path, str):
                target = (project / raw_path).resolve()
                if normalized == "edit" and target.is_file():
                    old, new = arguments.get("old_string", arguments.get("oldString")), arguments.get("new_string", arguments.get("newString"))
                    if isinstance(old, str) and isinstance(new, str) and target.stat().st_size <= 2 * 1024 * 1024:
                        original = target.read_text("utf-8-sig")
                        if old and (original.count(old) == 1 or arguments.get("replace_all", arguments.get("replaceAll", False))):
                            content = original.replace(old, new, -1 if arguments.get("replace_all", arguments.get("replaceAll", False)) else 1)
                targets.append((target, content if isinstance(content, str) else None))
            if normalized == "apply_patch":
                patch = arguments.get("input", arguments.get("patch", arguments.get("command", "")))
                if isinstance(patch, str):
                    for name in re.findall(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", patch, re.MULTILINE):
                        targets.append(((project / name).resolve(), None))
        for target, content in targets:
            if target == self.store.home or self.store.home in target.parents:
                checks.append({"rule_id": "owner.scope", "status": "failed", "reason": "Do not directly edit the installed policy authority/state; use reviewed policy evolution."})
            if not target.exists():
                checks.extend(validate_new_path(project, target))
            if content is not None and target.suffix in source_suffixes:
                require(len(content.encode("utf-8")) <= 2 * 1024 * 1024, "tool_input_too_large", "Proposed source exceeds checker limit")
                checks.extend(validate_text(target, content))
        with self.store.connection() as connection:
            key = self.project_key(project)
            exceptions = [value for _, value in self.store.items(connection, "exception") if value["project_key"] == key]
            pinned = self.store.get(connection, "project", key)
            active_snapshot = pinned["snapshot_id"] if pinned else self.store.get(connection, "setting", "desired_snapshot")
        for check in checks:
            for exception in exceptions:
                if (exception["snapshot_id"] == active_snapshot and check.get("rule_id") == exception["rule_id"]
                        and check.get("path", "").replace("\\", "/") == exception["path"]):
                    check.update(status="excepted", reason=exception["reason"], evidence=exception["evidence"])
        failed = [check for check in checks if check["status"] == "failed"]
        return {"ok": not failed, "decision": "deny" if failed else "continue", "checks": checks,
                "coverage": "direct_write_paths_and_available_postimages" if targets else "unobserved_or_nonwrite_tool",
                "unverified": ["semantic_policy_compliance", "arbitrary_shell_side_effects", "external_tool_side_effects"],
                "reason": "; ".join(check["reason"] for check in failed)}

    def check_files(self, project: Path, files: list[str]) -> dict[str, Any]:
        project = find_project(project)
        require(len(files) <= 1024, "too_many_files", "Bound checks to the changed files")
        checks = []
        for filename in files:
            path = (project / filename).resolve()
            require(path.is_relative_to(project), "outside_project", "Check path escaped project", path=filename)
            require(path.is_file() and not (project / filename).is_symlink(), "unsafe_file", "Expected a regular owned file", path=filename)
            require(path.stat().st_size <= 2 * 1024 * 1024, "file_too_large", "Source exceeds checker limit", path=filename)
            if path.suffix not in source_suffixes:
                checks.append({"path": filename, "status": "not_checked", "reason": "unsupported_file_type"})
                continue
            try:
                text = path.read_bytes().decode("utf-8-sig")
            except UnicodeDecodeError as error:
                checks.append({"path": filename, "status": "failed", "rule_id": "owner.encoding", "reason": str(error)})
                continue
            failures = validate_text(path, text)
            checks.extend({"path": filename, **result} for result in failures)
            if not failures:
                checks.append({"path": filename, "status": "passed", "checks": ["utf8", "supported_syntax"],
                               "sha256": byte_digest(path.read_bytes())})
        return {"ok": not any(item["status"] == "failed" for item in checks), "checks": checks,
                "semantic_compliance": "requires_agent_evidence", "complete_verification": False}

    def repair_json(self, project: Path, filename: str) -> dict[str, Any]:
        project = find_project(project)
        path = project / filename
        require(not path.is_symlink() and path.resolve().is_relative_to(project), "unsafe_repair_path", "Refusing path escape/symlink")
        require(path.suffix == ".json", "repair_not_proven_safe", "Only semantic-preserving strict JSON normalization is automatic")
        original = path.read_bytes()
        value = decode_json(original)
        # Whitespace-only rewrite preserves numeric lexemes, key order and string escapes.
        text = original.decode("utf-8-sig")
        pieces = []
        quoted = escaped = False
        for character in text:
            if quoted:
                pieces.append(character)
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    quoted = False
            elif character == '"':
                quoted = True
                pieces.append(character)
            elif character not in " \t\r\n":
                pieces.append(character)
        repaired = ("".join(pieces) + "\n").encode("utf-8")
        require(decode_json(repaired) == value, "repair_equivalence", "JSON semantic equivalence check failed")
        if original != repaired:
            backup = self.store.home / "repair_backups" / (byte_digest(original) + ".json")
            atomic_write(backup, original, private=True)
            require(path.read_bytes() == original, "concurrent_file_change", "File changed during repair")
            atomic_write(path, repaired)
        return {"ok": True, "changed": original != repaired, "before": byte_digest(original),
                "after": byte_digest(repaired), "proof": "whitespace_only_outside_strings_preserving_numeric_lexemes", "backup_retained": original != repaired}

    def hook(self, adapter: str, event: dict[str, Any]) -> dict[str, Any]:
        require(adapter in {"codex", "claude", "opencode"}, "adapter_unknown", "Unsupported native hook adapter")
        require(isinstance(event, dict), "hook_input_shape", "Hook event must be an object")
        kind = event.get("hook_event_name")
        session = event.get("agent_id") if kind in {"SubagentStart", "SubagentStop"} else event.get("session_id")
        require(isinstance(session, str) and bool(session), "session_required", "Hook input lacks an actual session ID")
        cwd = event.get("cwd")
        require(isinstance(cwd, str) and bool(cwd), "cwd_required", "Hook input lacks the actual working directory")
        project = Path(cwd)
        with self.store.transaction() as connection:
            self.store.put(connection, "host_event", adapter, {"event": kind, "received_at": time.time(), "session": session, "caller_authenticated": False})
        if kind == "PostCompact":
            # No unsupported additionalContext output is assumed for this event.
            # Invalidate delivered fingerprints; the next supported context boundary
            # (PreToolUse/UserPromptSubmit/SessionStart) restores the actual rule text.
            key = digest([self.project_key(project), session])
            with self.store.transaction() as connection:
                current = self.store.get(connection, "session", key)
                if current:
                    current["delivered"] = {}
                    self.store.put(connection, "session", key, current)
            return {}
        if kind in {"Stop", "SessionEnd", "SubagentStop"}:
            self.finish(project, session)
            return {}
        if kind in {"SessionStart", "SubagentStart", "UserPromptSubmit"}:
            update_notice = ""
            if kind == "SessionStart":
                from .sync import check_updates
                update_status = check_updates(self)
                if update_status.get("state") == "review_required":
                    update_notice = "\nAPG upstream policy candidate requires independent evidence review before admission: " + canonical(update_status).decode()
            packet = self.context(project, session, str(event.get("prompt", "")),
                                  fresh=kind != "UserPromptSubmit" or event.get("_apg_restore") is True, begin=kind in {"UserPromptSubmit", "SubagentStart"},
                                  parent_session=event.get("session_id") if kind == "SubagentStart" else None)
            if packet["context"] or update_notice:
                return {"hookSpecificOutput": {"hookEventName": kind, "additionalContext": packet["context"] + update_notice}}
            return {}
        if kind == "PreToolUse":
            arguments = event.get("tool_input", {})
            # Codex custom tools can carry a raw apply_patch string.
            if isinstance(arguments, str):
                arguments = {"input": arguments}
            require(isinstance(arguments, dict), "tool_input_shape", "Tool arguments must be an object or raw patch")
            tool = event.get("tool_name", "")
            require(isinstance(tool, str), "tool_name_shape", "Tool name must be text")
            packet = self.context(project, session, tool, begin=True)
            decision = self.gate(project, tool, arguments)
            output: dict[str, Any] = {"hookEventName": kind}
            if not decision["ok"]:
                output.update(permissionDecision="deny", permissionDecisionReason=decision["reason"])
            if packet["context"]:
                output["additionalContext"] = packet["context"]
            return {"hookSpecificOutput": output} if len(output) > 1 else {}
        if kind in {"PreCompact", "PostToolUse"}:
            return {}
        raise policy_error("hook_event_unknown", "Unsupported hook event", event=kind)
