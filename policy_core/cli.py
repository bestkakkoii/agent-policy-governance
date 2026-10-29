"""Agent-oriented commands. Diagnostics never claim unperformed verification."""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any

from .common import canonical, decode_json, default_home, policy_error, read_json, require, version
from .engine import discover_profile, load_catalog, select_rules
from .runtime import policy_runtime


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Agent Policy Governance: install once, resolve only applicable policies")
    result.add_argument("--home", type=Path, default=None, help="Local policy state directory (APG_HOME also supported)")
    result.add_argument("--version", action="version", version=version)
    commands = result.add_subparsers(dest="command", required=True)
    install = commands.add_parser("install")
    install.add_argument("--home", type=Path, default=argparse.SUPPRESS)
    install.add_argument("--user-home", type=Path)
    install.add_argument("--clients", default="codex,claude,opencode")
    install.add_argument("--project", type=Path)
    commands.add_parser("uninstall")
    commands.add_parser("doctor")
    context = commands.add_parser("context")
    context.add_argument("--project", type=Path, default=Path.cwd())
    context.add_argument("--session", required=True)
    context.add_argument("--task", default="")
    context.add_argument("--fresh", action="store_true")
    context.add_argument("--begin", action="store_true")
    context.add_argument("--full", action="store_true", help="All applicable rules, not all domains")
    context.add_argument("--text", action="store_true")
    finish = commands.add_parser("finish")
    finish.add_argument("--project", type=Path, default=Path.cwd())
    finish.add_argument("--session", required=True)
    profile = commands.add_parser("profile")
    profile.add_argument("--project", type=Path, default=Path.cwd())
    profile.add_argument("--tags")
    profile.add_argument("--actor")
    resolve = commands.add_parser("resolve")
    resolve.add_argument("--domain", default="software")
    resolve.add_argument("--capability", default="quality")
    explain = commands.add_parser("explain")
    explain.add_argument("rule_ids", nargs="+")
    explain.add_argument("--snapshot")
    check = commands.add_parser("check")
    check.add_argument("--project", type=Path, default=Path.cwd())
    check.add_argument("files", nargs="+")
    repair = commands.add_parser("repair")
    repair.add_argument("--project", type=Path, default=Path.cwd())
    repair.add_argument("file")
    hook = commands.add_parser("hook")
    hook.add_argument("adapter", choices=["codex", "claude", "opencode"])
    commands.add_parser("rpc")
    gate = commands.add_parser("gate")
    gate.add_argument("--project", type=Path, default=Path.cwd())
    gate.add_argument("--tool", required=True)
    proposal = commands.add_parser("propose")
    proposal.add_argument("candidate", type=Path)
    proposal.add_argument("--evidence", type=Path, required=True)
    proposal.add_argument("--actor", required=True)
    proposal.add_argument("--risk", choices=["low", "high"], required=True)
    proposal.add_argument("--rationale", required=True)
    proposal.add_argument("--rollback", action="store_true")
    review = commands.add_parser("review")
    review.add_argument("proposal_id")
    review.add_argument("--actor", required=True)
    review.add_argument("--findings", required=True)
    review.add_argument("--approve", action="store_true")
    review.add_argument("--evidence-checked", action="store_true")
    review.add_argument("--failure-modes", default="")
    review.add_argument("--rollback-plan", default="")
    publish = commands.add_parser("publish")
    publish.add_argument("proposal_id")
    exception = commands.add_parser("exception")
    exception.add_argument("--project", type=Path, default=Path.cwd())
    exception.add_argument("--rule", required=True)
    exception.add_argument("--path", required=True)
    exception.add_argument("--reason", required=True)
    exception.add_argument("--evidence", required=True)
    exception.add_argument("--actor", required=True)
    source = commands.add_parser("import-source")
    source.add_argument("archive", type=Path)
    source_read = commands.add_parser("source")
    source_read.add_argument("source_id")
    source_read.add_argument("name")
    source_read.add_argument("--start", type=int, default=1)
    source_read.add_argument("--count", type=int, default=80)
    sync = commands.add_parser("sync")
    sync.add_argument("--commit", required=True)
    sync.add_argument("--snapshot", required=True)
    service = commands.add_parser("serve")
    service.add_argument("--port", type=int, default=0)
    return result


def stdin_record() -> Any:
    return decode_json(sys.stdin.buffer.read(2 * 1024 * 1024 + 1))


def execute(arguments: argparse.Namespace) -> dict[str, Any] | None:
    home = (arguments.home or default_home()).expanduser().resolve()
    command = arguments.command
    if command in {"install", "uninstall", "doctor"}:
        from . import install
        if command == "install":
            return install.install(home, arguments.user_home or Path.home(), arguments.clients.split(","), arguments.project,
                                   use_environment=arguments.user_home is None)
        return install.uninstall(home) if command == "uninstall" else install.doctor(home)
    if command == "import-source":
        from .source import import_source
        return import_source(home, arguments.archive)
    if command == "source":
        from .source import read_source
        return read_source(home, arguments.source_id, arguments.name, arguments.start, arguments.count)
    if command == "sync":
        from .sync import fetch_snapshot
        return fetch_snapshot(home, arguments.commit, arguments.snapshot)
    runtime = policy_runtime(home)
    if command == "context":
        return runtime.context(arguments.project, arguments.session, arguments.task,
                               fresh=arguments.fresh, begin=arguments.begin, full=arguments.full)
    if command == "finish":
        return runtime.finish(arguments.project, arguments.session)
    if command == "profile":
        if not arguments.tags:
            return {"ok": True, "profile": discover_profile(arguments.project)}
        require(bool(arguments.actor), "actor_required", "Profile confirmation requires the actual deciding agent identity")
        return {"ok": True, "profile": runtime.confirm_profile(arguments.project, arguments.tags.split(","), arguments.actor)}
    if command == "resolve":
        catalog = load_catalog()
        capabilities = {"code_quality": "quality", "rendering": "rendering"}
        rules = select_rules(catalog, ["software", arguments.domain], [capabilities.get(arguments.capability, arguments.capability)])
        return {"ok": True, "snapshot_id": catalog["snapshot_id"], "rules": rules, "matched_rule_count": len(rules)}
    if command == "explain":
        return runtime.explain(arguments.rule_ids, arguments.snapshot)
    if command == "exception":
        from .exceptions import add_exception
        return add_exception(runtime, arguments.project, arguments.rule, arguments.path, arguments.reason, arguments.evidence, arguments.actor)
    if command == "check":
        return runtime.check_files(arguments.project, arguments.files)
    if command == "repair":
        return runtime.repair_json(arguments.project, arguments.file)
    if command == "hook":
        event = stdin_record()
        arguments.hook_event = event.get("hook_event_name") if isinstance(event, dict) else None
        from .service import execute_hybrid
        return execute_hybrid(runtime, {"op": "hook", "adapter": arguments.adapter, "event": event})
    if command == "gate":
        return runtime.gate(arguments.project, arguments.tool, stdin_record())
    if command == "rpc":
        from .service import execute_hybrid
        return execute_hybrid(runtime, stdin_record())
    if command in {"propose", "review", "publish"}:
        from . import evolution
        if command == "propose":
            return evolution.propose(runtime, read_json(arguments.candidate), arguments.actor,
                                     read_json(arguments.evidence), arguments.risk, arguments.rationale, rollback=arguments.rollback)
        if command == "review":
            return evolution.review(runtime, arguments.proposal_id, arguments.actor, arguments.approve,
                                    arguments.findings, arguments.evidence_checked, arguments.failure_modes, arguments.rollback_plan)
        return evolution.publish(runtime, arguments.proposal_id)
    if command == "serve":
        from .service import serve
        serve(runtime, arguments.port)
        return None
    raise policy_error("command_unknown", "Unknown command")


def main() -> int:
    if sys.version_info < (3, 13):
        print("APG requires an already installed Python 3.13 or newer. No toolchain will be installed automatically.", file=sys.stderr)
        return 2
    arguments = parser().parse_args()
    try:
        value = execute(arguments)
        if value is not None:
            if getattr(arguments, "text", False):
                print(value.get("context", ""))
            else:
                print(canonical(value).decode("utf-8"))
        return 1 if value is not None and value.get("ok") is False else 0
    except KeyboardInterrupt:
        print(canonical({"ok": False, "error": "interrupted", "message": "Operation interrupted; no completion claimed"}).decode(), file=sys.stderr)
        return 130
    except (policy_error, OSError, ValueError, TypeError, KeyError) as error:
        record = error.record() if isinstance(error, policy_error) else {"ok": False, "error": type(error).__name__, "message": str(error)}
        record["stage"] = arguments.command
        print(canonical(record).decode(), file=sys.stderr)
        # Codex errors on PreToolUse can fail open. Explicit deny is required for a readable malformed request.
        if arguments.command == "hook" and getattr(arguments, "hook_event", None) == "PreToolUse":
            print(canonical({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                    "permissionDecisionReason": "Governance validation failed: " + str(error)}}).decode())
            return 0
        return 2
    except Exception:
        # Unexpected faults retain a full traceback for the agent; never silently continue.
        traceback.print_exc(file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
