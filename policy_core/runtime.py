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
max_text_bytes = 2 * 1024 * 1024
patch_begin = "*** Begin Patch"
patch_end = "*** End Patch"
# Codex accepts apply_patch as a direct tool, an argv command and a shell heredoc (optionally after `cd <dir> &&`).
apply_patch_word = re.compile(r"(?<![\w.-])(?:apply_patch|applypatch)(?![\w.-])")
heredoc_workdir = re.compile(r"^\s*cd\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))\s*&&")


def validate_new_path(project: Path, target: Path) -> list[dict[str, Any]]:
    """Check only components this write creates; existing ancestors are prior project decisions, not new names."""
    results = []
    try:
        relative = target.relative_to(project)
    except ValueError:
        return [{"rule_id": "owner.naming", "status": "not_checked", "reason": "outside_project_ownership"}]
    current = project
    for part in relative.parts:
        current = current / part
        if current.exists() or part in known_file_names or part.startswith("."):
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


def tool_arguments(value: Any) -> dict[str, Any]:
    """Codex declares tool_input as arbitrary JSON; normalize raw patch text and argv arrays to an object."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return {"input": value}
    if isinstance(value, list):
        return {"command": value}
    if value is None:
        return {}
    raise policy_error("tool_input_shape", "Tool arguments must be an object, argv array, raw patch or null", type=type(value).__name__)


def read_existing_text(path: Path) -> tuple[str | None, str | None]:
    """Return (text, reason): bounded strict UTF-8 preimage, or the cause it cannot serve as a check baseline."""
    if not path.is_file():
        return None, None
    try:
        if path.stat().st_size > max_text_bytes:
            return None, "original_exceeds_checker_limit"
        return path.read_bytes().decode("utf-8-sig"), None
    except UnicodeDecodeError as error:
        return None, f"original_not_utf8: {error.reason} at byte {error.start}"
    except OSError as error:
        # The host performs (and reports) the real write; an unreadable baseline only limits what can be verified.
        return None, f"original_unreadable: {type(error).__name__}: {error}"


def bounded_postimage(text: str | None, reason: str | None) -> tuple[str | None, str | None]:
    """Derived postimages above the checker limit are reported as unchecked instead of denying a legitimate edit."""
    if text is not None and len(text.encode("utf-8")) > max_text_bytes:
        return None, "postimage_exceeds_checker_limit"
    return text, reason


def apply_patch_bodies(tool: str, arguments: Any) -> list[tuple[str, str | None]]:
    """Collect (patch, workdir) from direct, argv and heredoc invocations; file-content fields are never parsed."""
    bodies: list[tuple[str, str | None]] = []

    def take(text: str, invoked: bool) -> None:
        start = 0
        while (index := text.find(patch_begin, start)) >= 0:
            start = index + len(patch_begin)
            prefix = text[:index]
            command_line = prefix.rstrip().rsplit("\n", 1)[-1]
            if not (invoked or (tool == "apply_patch" and not prefix.strip()) or apply_patch_word.search(command_line)):
                continue
            end = text.find(patch_end, index)
            workdir = heredoc_workdir.match(command_line) if apply_patch_word.search(command_line) else None
            bodies.append((text[index:] if end < 0 else text[index:end + len(patch_end)],
                           next((group for group in workdir.groups() if group), None) if workdir else None))

    def walk(value: Any, depth: int) -> None:
        if depth > 8:
            return
        if isinstance(value, str):
            take(value, False)
        elif isinstance(value, list):
            invoked = bool(value) and isinstance(value[0], str) and apply_patch_word.fullmatch(Path(value[0]).name) is not None
            for item in value[1:] if invoked else value:
                if invoked and isinstance(item, str):
                    take(item, True)
                else:
                    walk(item, depth + 1)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item, depth + 1)

    walk(arguments, 0)
    return bodies


def parse_apply_patch(text: str) -> list[dict[str, Any]]:
    """Parse the Codex apply_patch grammar into add/delete/update operations with update hunks."""
    operations: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    hunk: dict[str, Any] | None = None
    for raw in text.split("\n"):
        line = raw[:-1] if raw.endswith("\r") else raw
        header = next((kind for kind in ("Add", "Delete", "Update") if line.startswith(f"*** {kind} File: ")), None)
        if header:
            current = {"kind": header.casefold(), "path": line.split(": ", 1)[1].strip(), "lines": [], "move_to": None, "hunks": []}
            operations.append(current)
            hunk = None
        elif current is None or line.startswith(patch_end):
            current = None
        elif current["kind"] == "add":
            if line.startswith("+"):
                current["lines"].append(line[1:])
        elif current["kind"] == "update":
            if line.startswith("*** Move to: "):
                current["move_to"] = line.split(": ", 1)[1].strip()
            elif line.startswith("*** End of File"):
                if hunk is not None:
                    hunk["end_of_file"] = True
            elif line.startswith("@@"):
                hunk = {"context": line[2:].strip() or None, "old": [], "new": [], "end_of_file": False}
                current["hunks"].append(hunk)
            elif line[:1] in {"+", "-", " ", ""}:
                if hunk is None:
                    # The first hunk may omit its @@ header.
                    hunk = {"context": None, "old": [], "new": [], "end_of_file": False}
                    current["hunks"].append(hunk)
                if line[:1] != "+":
                    hunk["old"].append(line[1:])
                if line[:1] != "-":
                    hunk["new"].append(line[1:])
    return operations


def seek_lines(lines: list[str], pattern: list[str], start: int, end_of_file: bool) -> int | None:
    """Mirror Codex apply_patch matching order (exact, trailing, surrounding whitespace); no fuzzy Unicode pass."""
    if not pattern:
        return start
    if len(pattern) > len(lines):
        return None
    first = len(lines) - len(pattern) if end_of_file else start
    for normalize in (str, str.rstrip, str.strip):
        wanted = [normalize(line) for line in pattern]
        for index in range(first, len(lines) - len(pattern) + 1):
            if all(normalize(lines[index + offset]) == wanted[offset] for offset in range(len(pattern))):
                return index
    return None


def apply_update_hunks(original: str, hunks: list[dict[str, Any]]) -> str | None:
    """Reconstruct the Codex postimage; None means it cannot be derived without guessing."""
    lines = original.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    replacements: list[tuple[int, int, list[str]]] = []
    index = 0
    for hunk in hunks:
        if hunk["context"] is not None:
            found = seek_lines(lines, [hunk["context"]], index, False)
            if found is None:
                return None
            index = found + 1
        old, new = hunk["old"], hunk["new"]
        if not old:
            replacements.append((len(lines) - 1 if lines and lines[-1] == "" else len(lines), 0, new))
            continue
        found = seek_lines(lines, old, index, hunk["end_of_file"])
        if found is None and old[-1] == "":
            old, new = old[:-1], new[:-1] if new and new[-1] == "" else new
            found = seek_lines(lines, old, index, hunk["end_of_file"])
        if found is None:
            return None
        replacements.append((found, len(old), new))
        index = found + len(old)
    for start, length, new in sorted(replacements, key=lambda item: item[0], reverse=True):
        lines[start:start + length] = new
    return "\n".join(lines) + "\n"


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

    def gate(self, project: Path, tool: str, arguments: Any) -> dict[str, Any]:
        arguments = tool_arguments(arguments)
        # Relative tool paths are relative to the host working directory, which may be below the project root.
        base = Path(project).expanduser().resolve()
        base = base.parent if base.is_file() else base
        project = find_project(base)
        normalized = tool.casefold().split(".")[-1]
        checks: list[dict[str, Any]] = []
        # Each target: path, proposed postimage, preimage baseline, whether new names are created, skip reason.
        targets: list[dict[str, Any]] = []
        if normalized in write_tools and normalized != "apply_patch":
            raw_path = arguments.get("file_path", arguments.get("filePath", arguments.get("path")))
            content = arguments.get("content")
            if isinstance(raw_path, str):
                target = (base / raw_path).resolve()
                original, unreadable = read_existing_text(target)
                if normalized == "edit" and target.is_file():
                    old, new = arguments.get("old_string", arguments.get("oldString")), arguments.get("new_string", arguments.get("newString"))
                    replace_all = arguments.get("replace_all", arguments.get("replaceAll", False))
                    if isinstance(old, str) and isinstance(new, str) and original is not None:
                        if old and (original.count(old) == 1 or replace_all):
                            content, unreadable = bounded_postimage(original.replace(old, new, -1 if replace_all else 1), unreadable)
                targets.append({"path": target, "content": content if isinstance(content, str) else None, "original": original,
                                "naming": True, "skipped": unreadable if normalized == "edit" else None})
        # Write/Edit payloads are file data; only apply_patch and command-style tools can invoke a patch.
        bodies = [] if normalized in write_tools - {"apply_patch"} else apply_patch_bodies(normalized, arguments)
        for body, workdir in bodies:
            directory = (base / workdir).resolve() if workdir else base
            for operation in parse_apply_patch(body):
                source = (directory / operation["path"]).resolve()
                if operation["kind"] == "add":
                    targets.append({"path": source, "content": "".join(line + "\n" for line in operation["lines"]),
                                    "original": None, "naming": True, "skipped": None})
                elif operation["kind"] == "delete":
                    targets.append({"path": source, "content": None, "original": None, "naming": False, "skipped": None})
                else:
                    destination = (directory / operation["move_to"]).resolve() if operation["move_to"] else source
                    original, unreadable = read_existing_text(source)
                    postimage = apply_update_hunks(original, operation["hunks"]) if original is not None else None
                    postimage, skipped = bounded_postimage(postimage, unreadable or ("patch_postimage_unavailable" if postimage is None else None))
                    if destination != source:
                        targets.append({"path": source, "content": None, "original": None, "naming": False, "skipped": None})
                    targets.append({"path": destination, "content": postimage, "original": original, "naming": destination != source,
                                    "skipped": skipped})
        for target in targets:
            path = target["path"]
            display = str(path.relative_to(project)) if path.is_relative_to(project) else str(path)
            if path == self.store.home or self.store.home in path.parents:
                checks.append({"rule_id": "owner.scope", "status": "failed", "path": display,
                               "reason": "Do not directly edit the installed policy authority/state; use reviewed policy evolution."})
            if target["naming"] and not path.exists():
                checks.extend(validate_new_path(project, path))
            if path.suffix not in source_suffixes:
                continue
            if target["skipped"]:
                checks.append({"rule_id": "owner.static_quality", "status": "not_checked", "path": display, "reason": target["skipped"]})
            if target["content"] is None:
                continue
            require(len(target["content"].encode("utf-8")) <= max_text_bytes, "tool_input_too_large", "Proposed source exceeds checker limit")
            failures = [{**failure, "path": display} for failure in validate_text(path, target["content"])]
            if failures and target["original"] is not None and validate_text(path, target["original"]):
                # Only regressions are denied; a preimage that already fails (for example JSON with comments) stays editable.
                failures = [{**failure, "status": "not_checked", "reason": "pre_existing_failure: " + failure["reason"]} for failure in failures]
            checks.extend(failures)
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
            arguments = tool_arguments(event.get("tool_input", {}))
            tool = event.get("tool_name", "")
            require(isinstance(tool, str), "tool_name_shape", "Tool name must be text")
            packet = self.context(project, session, tool, begin=True)
            decision = self.gate(project, tool, arguments)
            output: dict[str, Any] = {"hookEventName": kind}
            if not decision["ok"]:
                output.update(permissionDecision="deny", permissionDecisionReason=decision["reason"])
            unchecked = [f"{check['path']}: {check['reason']}" for check in decision["checks"]
                         if check["status"] == "not_checked" and check["rule_id"] == "owner.static_quality"]
            notice = "APG content check not performed (not verified): " + "; ".join(unchecked[:4]) if unchecked else ""
            if packet["context"] or notice:
                output["additionalContext"] = "\n".join(text for text in (packet["context"], notice) if text)
            return {"hookSpecificOutput": output} if len(output) > 1 else {}
        if kind in {"PreCompact", "PostToolUse"}:
            return {}
        raise policy_error("hook_event_unknown", "Unsupported hook event", event=kind)
