"""Reversible, managed-block installation; no CLI trust bypass or toolchain install."""
from __future__ import annotations

import base64
import os
import re
import shlex
import shutil
import sys
import subprocess
from pathlib import Path
from typing import Any

from .common import atomic_write, byte_digest, canonical, decode_json, digest, policy_error, read_json, require, write_json, file_lock

marker_start = "<!-- agent_policy_governance:begin -->"
marker_end = "<!-- agent_policy_governance:end -->"
managed_label = "agent_policy_governance"
root = Path(__file__).resolve().parent.parent


def managed_block(original: bytes, content: str | None) -> bytes:
    text = original.decode("utf-8-sig")
    require(text.count(marker_start) == text.count(marker_end) <= 1,
            "managed_block_invalid", "Unbalanced or duplicate policy instruction markers")
    pattern = re.compile(re.escape(marker_start) + r".*?" + re.escape(marker_end), re.DOTALL)
    if content is None:
        text = pattern.sub("", text)
    else:
        block = marker_start + "\n" + content.rstrip() + "\n" + marker_end
        text = pattern.sub(lambda _: block, text) if marker_start in text else text + ("\n\n" if text else "") + block + "\n"
    bom = b"\xef\xbb\xbf" if original.startswith(b"\xef\xbb\xbf") else b""
    return bom + text.encode("utf-8")


def owned_hook(hook: Any) -> bool:
    return isinstance(hook, dict) and hook.get("statusMessage") == managed_label


def merge_hooks(original: bytes, additions: dict[str, list[dict[str, Any]]]) -> bytes:
    data = decode_json(original) if original.strip() else {}
    require(isinstance(data, dict), "settings_invalid", "CLI settings must be a JSON object")
    hooks = data.setdefault("hooks", {})
    require(isinstance(hooks, dict), "settings_invalid", "Existing hooks must be an object")
    for event in list(hooks):
        require(isinstance(hooks[event], list), "settings_invalid", "Hook event must be an array", event=event)
        retained = []
        for group in hooks[event]:
            require(isinstance(group, dict) and isinstance(group.get("hooks"), list),
                    "settings_invalid", "Unexpected existing hook group", event=event)
            items = [hook for hook in group["hooks"] if not owned_hook(hook)]
            if items or not any(owned_hook(hook) for hook in group["hooks"]):
                retained.append({**group, "hooks": items})
        if retained:
            hooks[event] = retained
        else:
            del hooks[event]
    for event, items in additions.items():
        hooks.setdefault(event, []).extend(items)
    if not hooks:
        data.pop("hooks", None)
    return canonical(data) + b"\n"


def command_line(arguments: list[str]) -> str:
    if os.name == "nt":
        # Codex's commandWindows is interpreted by PowerShell, not CommandLineToArgvW.
        return "& " + " ".join("'" + value.replace("'", "''") + "'" for value in arguments)
    return shlex.join(arguments)


def instruction_text(launcher: Path, home: Path) -> str:
    invocation = command_line([sys.executable, str(launcher), "--home", str(home)])
    return f"""## Automatic policy governance
This is a user-authorized engineering policy integration, subordinate to platform safety and explicit current requirements.
Do not ask the user to restate the whitepaper. At task start, use the native hook context; if missing or a new technical topic arises, run `{invocation} context --project . --session <actual_session_id> --task <short_task_topics> --begin`. Use `--fresh` after compaction or handoff when the host did not restore context. Never substitute a hash/ID for actual rule text after context loss.
On first project use, inspect the auto-detected profile. Finish your own bootstrap task first with `finish --project . --session <actual_session_id>`, then, when other project agents are also idle, confirm factual tags with `profile --project . --tags software,<actual_tags> --actor <actual_agent_id>`. Add game only for actual game work, desktop_gui only for a desktop GUI. Re-enter `context --project . --session <actual_session_id> --task <short_task_topics> --begin --fresh` after confirming. Do not ask the user technical setup questions. Do not reread the entire source whitepaper.
Obey applicable rules, not unrelated domain rules. No forced extra agents, frameworks, daemon or tools. Apply the owner's newest supported technologies using installed compatible large toolchains; preserve existing project behavior and settings. Use English for agent handoffs, Traditional Chinese for owner reports. Keep meaningful snake_case owned names and honest, actionable diagnostics.
Before reporting completion, run the project's relevant strict checks and provide actual evidence. The hook only checks declared direct-write paths and available JSON/Python postimages; it does not verify arbitrary shell commands, all semantics, or all model output. Never label advisory coverage enforced. For a safe task boundary run `finish --project . --session <actual_session_id>` using the same invocation. Child agents inherit the same snapshot and relevant rule text, not the full whitepaper. Policy evolution needs evidence and a genuinely separate reviewer; self-approval is forbidden.
Use `explain <rule_ids>` only for necessary details; never reload unchanged rules for routine tool calls. Installation is not proof of live hook execution; use `doctor` and the host's normal trust UI. Never bypass trust or change the governance authority by direct file edits."""


def config_paths(user_home: Path, home: Path, use_environment: bool) -> dict[str, Path]:
    def configured(name: str, fallback: Path) -> Path:
        return Path(os.environ[name]).expanduser().resolve() if use_environment and os.environ.get(name) else fallback
    return {
        "codex": configured("CODEX_HOME", user_home / ".codex"),
        "claude": configured("CLAUDE_CONFIG_DIR", user_home / ".claude"),
        "opencode": configured("XDG_CONFIG_HOME", user_home / ".config") / "opencode",
        "home": home,
    }


def recover_journal(home: Path) -> dict[str, Any]:
    journal_path = home / "install_journal.json"
    if not journal_path.exists():
        return {"recovered": False}
    journal = read_json(journal_path)
    for item in reversed(journal["files"]):
        path = Path(item["path"])
        current = path.read_bytes() if path.exists() else None
        before = None if item["before"] is None else base64.b64decode(item["before"], validate=True)
        after = None if item["after"] is None else base64.b64decode(item["after"], validate=True)
        if current == before:
            continue
        require(current == after, "install_recovery_conflict", "File changed since interrupted installation; no overwrite", path=str(path))
        if before is None:
            path.unlink(missing_ok=True)
        else:
            atomic_write(path, before, private=True)
    journal_path.unlink()
    return {"recovered": True}


def apply_plan(home: Path, plan: dict[Path, bytes | None]) -> list[dict[str, Any]]:
    changes = []
    for path, data in plan.items():
        require(not path.is_symlink(), "unsafe_symlink", "Configuration destination is a symlink", path=str(path))
        original = path.read_bytes() if path.exists() else None
        if original == data:
            continue
        changes.append({"path": str(path), "before": None if original is None else base64.b64encode(original).decode(),
                        "after": None if data is None else base64.b64encode(data).decode()})
    if not changes:
        return []
    write_json(home / "install_journal.json", {"files": changes}, private=True)
    try:
        for change in changes:
            path = Path(change["path"])
            expected = None if change["before"] is None else base64.b64decode(change["before"])
            require((path.read_bytes() if path.exists() else None) == expected,
                    "install_concurrent_change", "Configuration changed while preparing install", path=str(path))
            if change["after"] is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, base64.b64decode(change["after"]), private=True)
    except BaseException:
        recover_journal(home)
        raise
    (home / "install_journal.json").unlink()
    return changes


def runtime_files() -> dict[str, bytes]:
    files = {"apg.py": (root / "apg.py").read_bytes(), "policies/catalog.json": (root / "policies/catalog.json").read_bytes()}
    files.update({"policy_core/" + path.name: path.read_bytes() for path in sorted((root / "policy_core").glob("*.py"))})
    adapter = root / "adapters/opencode/plugin.mjs"
    if adapter.exists():
        files["adapters/opencode/plugin.mjs"] = adapter.read_bytes()
    return files


def install_locked(home: Path, user_home: Path, clients: list[str], project: Path | None = None,
            *, use_environment: bool = True) -> dict[str, Any]:
    require(sys.version_info >= (3, 13), "runtime_unsupported", "Use an installed Python 3.13 or newer; no runtime is downloaded")
    require(set(clients) <= {"codex", "claude", "opencode"}, "client_unknown", "Unknown CLI adapter")
    observed_clients = {}
    for client in clients:
        binary = shutil.which(client)
        if binary is None:
            observed_clients[client] = {"available": False, "integration": "prepared_for_future_host"}
            continue
        probe = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=4, check=False)
        require(probe.returncode == 0, "host_probe_failed", "Installed host version could not be verified", client=client, original_error=probe.stderr)
        version_match = re.search(r"(?<!\d)(\d+)\.(\d+)\.(\d+)", probe.stdout)
        observed_clients[client] = {"available": True, "observed_version": probe.stdout.strip()[:256]}
        if client == "claude":
            require(version_match is not None and tuple(map(int, version_match.groups())) >= (2, 1, 295),
                    "host_capability_unavailable", "Installed Claude lacks the required exec/onFailure contract; no forced update or silent downgrade", client=client)
    home, user_home = home.resolve(), user_home.resolve()
    home.mkdir(parents=True, exist_ok=True)
    recover_journal(home)
    files = runtime_files()
    runtime_id = digest({path: byte_digest(data) for path, data in files.items()})
    release = home / "runtimes" / runtime_id
    plan: dict[Path, bytes | None] = {}
    for name, data in files.items():
        path = release / name
        require(not path.exists() or path.read_bytes() == data, "runtime_tampered", "Immutable installed runtime differs", path=str(path))
        if not path.exists():
            atomic_write(path, data, private=True)
    launcher = home / "run.py"
    launcher_text = '''"""Stable installed entrypoint; selected runtime is atomically replaced."""
import json
import runpy
import sys
import subprocess
from pathlib import Path
home = Path(__file__).resolve().parent
selection = json.loads((home / "active_runtime.json").read_text("utf-8"))
root = home / "runtimes" / selection["runtime_id"]
if not root.resolve().is_relative_to((home / "runtimes").resolve()):
    raise RuntimeError("Invalid runtime selection")
sys.path.insert(0, str(root))
runpy.run_path(str(root / "apg.py"), run_name="__main__")
'''
    plan[launcher] = launcher_text.encode()
    plan[home / "active_runtime.json"] = canonical({"runtime_id": runtime_id, "python": sys.executable}) + b"\n"
    settings = config_paths(user_home, home, use_environment)
    text = instruction_text(launcher, home)
    managed: dict[str, str] = {}
    previous_path = home / "install_receipt.json"
    previous = read_json(previous_path) if previous_path.exists() else {"files": {}, "clients": []}
    for client in clients:
        directory = settings[client]
        instructions = directory / ("CLAUDE.md" if client == "claude" else "AGENTS.md")
        original = instructions.read_bytes() if instructions.exists() else b""
        plan[instructions] = managed_block(original, text)
        managed[str(instructions)] = "instructions"
        arguments = [sys.executable, str(launcher), "--home", str(home), "hook", client]
        if client == "opencode":
            source = root / "adapters/opencode/plugin.mjs"
            require(source.is_file(), "adapter_missing", "OpenCode adapter not packaged")
            plugin = directory / "plugins" / "agent_policy_governance.js"
            config = {"python": sys.executable, "launcher": str(launcher), "home": str(home)}
            generated = source.read_text("utf-8").replace("/*APG_CONFIG*/ null", canonical(config).decode())
            if plugin.exists() and str(plugin) not in previous["files"]:
                raise policy_error("plugin_collision", "An unmanaged file already occupies the plugin path", path=str(plugin))
            plan[plugin] = generated.encode()
            managed[str(plugin)] = "generated"
        else:
            config = directory / ("hooks.json" if client == "codex" else "settings.json")
            events = ["SessionStart", "UserPromptSubmit", "PreToolUse", "SubagentStart", "SubagentStop", "PostCompact", "Stop", "SessionEnd"]
            additions: dict[str, list[dict[str, Any]]] = {}
            for event in events:
                if client == "claude":
                    hook = {"type": "command", "command": arguments[0], "args": arguments[1:], "timeout": 10,
                            "statusMessage": managed_label, "onFailure": "block"}
                else:
                    hook = {"type": "command", "command": command_line(arguments), "timeout": 3 if event == "SessionEnd" else 10, "statusMessage": managed_label, "additionalContextLimit": 12000}
                    if os.name == "nt":
                        hook["commandWindows"] = hook["command"]
                additions[event] = [{"hooks": [hook]}]
            original = config.read_bytes() if config.exists() else b""
            plan[config] = merge_hooks(original, additions)
            managed[str(config)] = "hooks"
    if project is not None:
        instructions = project.resolve() / "AGENTS.md"
        original = instructions.read_bytes() if instructions.exists() else b""
        plan[instructions] = managed_block(original, text)
        managed[str(instructions)] = "instructions"
    receipt_files = dict(previous["files"])
    for path, kind in managed.items():
        destination = Path(path)
        original = destination.read_bytes() if destination.exists() else None
        old = receipt_files.get(path)
        receipt_files[path] = {"kind": kind, "before": old["before"] if old else None if original is None else base64.b64encode(original).decode(),
                               "after_sha256": byte_digest(plan[destination]), "after": base64.b64encode(plan[destination]).decode()}
    plan[home / "active_runtime.json"] = canonical({"runtime_id": runtime_id, "python": sys.executable}) + b"\n"
    if not (home / "sync_settings.json").exists():
        plan[home / "sync_settings.json"] = canonical({"enabled": True, "interval_seconds": 86400, "initial_check_after": __import__("time").time() + 86400}) + b"\n"
    receipt = {"schema_version": 1, "runtime_id": runtime_id, "clients": sorted(set(previous["clients"]) | set(clients)),
               "files": receipt_files, "runtime_manifest": {path: byte_digest(data) for path, data in files.items()},
               "python": sys.executable, "user_home": str(user_home), "trust_bypassed": False, "observed_clients": observed_clients}
    plan[previous_path] = canonical(receipt) + b"\n"
    changes = apply_plan(home, plan)
    return {"ok": True, "changed_files": len(changes), "runtime_id": runtime_id, "home": str(home),
            "clients": receipt["clients"], "state": "configured_not_live_verified", "trust_bypassed": False,
            "observed_clients": observed_clients,
            "codex_action": "Host must authorize the exact hook definitions through its normal /hooks trust flow; never bypass it.",
            "launch": command_line([sys.executable, str(launcher), "--home", str(home), "doctor"])}


def uninstall_locked(home: Path) -> dict[str, Any]:
    recover_journal(home)
    receipt_path = home / "install_receipt.json"
    require(receipt_path.exists(), "not_installed", "No installation receipt exists")
    receipt = read_json(receipt_path)
    plan: dict[Path, bytes | None] = {}
    conflicts: list[str] = []
    for name, item in receipt["files"].items():
        path = Path(name)
        if not path.exists():
            continue
        require(not path.is_symlink(), "unsafe_symlink", "Managed path became a symlink", path=name)
        current = path.read_bytes()
        if byte_digest(current) == item["after_sha256"]:
            if item["before"] is None:
                plan[path] = None
            else:
                plan[path] = base64.b64decode(item["before"], validate=True)
        elif item["kind"] == "instructions":
            plan[path] = managed_block(current, None)
        elif item["kind"] == "hooks":
            plan[path] = merge_hooks(current, {})
        else:
            conflicts.append(name)
    require(not conflicts, "uninstall_conflict", "Modified generated adapter retained; reconcile before removal", paths=conflicts)
    plan[receipt_path] = None
    apply_plan(home, plan)
    return {"ok": True, "removed_hooks": True, "retained": "policy state, evidence, runtime and backups (no data deletion)"}


def doctor(home: Path) -> dict[str, Any]:
    from .runtime import policy_runtime
    runtime = policy_runtime(home)
    path = home / "install_receipt.json"
    receipt = read_json(path) if path.exists() else None
    problems = []
    if receipt:
        for name in receipt["files"]:
            target = Path(name)
            if target.name == "hooks.json" and target.parent.name == ".codex":
                configuration = target.parent / "config.toml"
                if configuration.exists():
                    import tomllib
                    settings = tomllib.loads(configuration.read_text("utf-8-sig"))
                    if settings.get("features", {}).get("hooks", settings.get("features", {}).get("codex_hooks", True)) is False:
                        problems.append({"code": "host_hooks_disabled", "path": str(configuration)})
            if target.name == "settings.json" and target.parent.name == ".claude" and target.exists():
                if read_json(target).get("disableAllHooks") is True:
                    problems.append({"code": "host_hooks_disabled", "path": str(target)})
    if receipt:
        release = home / "runtimes" / receipt["runtime_id"]
        for name, expected in receipt["runtime_manifest"].items():
            target = release / name
            if not target.is_file() or byte_digest(target.read_bytes()) != expected:
                problems.append({"code": "installed_runtime_changed", "path": str(target)})
        for name, item in receipt["files"].items():
            target = Path(name)
            if not target.exists():
                problems.append({"code": "managed_config_missing", "path": name})
                continue
            raw = target.read_bytes()
            if item["kind"] == "instructions" and marker_start.encode() not in raw:
                problems.append({"code": "instruction_block_missing", "path": name})
            elif item["kind"] == "generated" and byte_digest(raw) != item["after_sha256"]:
                problems.append({"code": "adapter_changed", "path": name})
            elif item["kind"] == "hooks":
                data = decode_json(raw)
                expected = decode_json(base64.b64decode(item["after"]))
                for event, groups in expected.get("hooks", {}).items():
                    desired_hooks = [hook for group in groups for hook in group.get("hooks", []) if owned_hook(hook)]
                    actual_hooks = [hook for group in data.get("hooks", {}).get(event, []) for hook in group.get("hooks", []) if owned_hook(hook)]
                    if actual_hooks != desired_hooks:
                        problems.append({"code": "hook_registration_changed", "path": name, "event": event})
    with runtime.store.connection() as connection:
        events = dict(runtime.store.items(connection, "host_event"))
        desired = runtime.store.get(connection, "setting", "desired_snapshot")
        runtime.catalog_for(connection, desired)
    return {"ok": not problems, "installed": receipt is not None, "problems": problems,
            "python": sys.version, "snapshot_id": desired,
            "clients": {client: {"binary_found": shutil.which("claude" if client == "claude" else client) is not None,
                        "configured": bool(receipt and client in receipt["clients"]), "last_hook_input": events.get(client),
                        "live_host_verified": False, "trust": "host_managed_not_bypassed"} for client in ("codex", "claude", "opencode")},
            "limitations": ["Input receipts alone do not authenticate the caller or prove end-to-end host enforcement.",
                            "Native trust/approval and unsupported tool paths remain platform boundaries."]}


def install(home: Path, user_home: Path, clients: list[str], project: Path | None = None, *, use_environment: bool = True) -> dict[str, Any]:
    with file_lock(home / "install.lock"):
        return install_locked(home, user_home, clients, project, use_environment=use_environment)


def uninstall(home: Path) -> dict[str, Any]:
    with file_lock(home / "install.lock"):
        return uninstall_locked(home)
