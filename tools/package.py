"""Deterministic source/private-plugin archives; public MCP identity needs a real URL."""
from __future__ import annotations

import argparse
import ipaddress
import json
import sys
import urllib.parse
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from policy_core.common import canonical, byte_digest, require, version
from policy_core.engine import load_catalog


def source_files() -> dict[str, bytes]:
    excluded = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules", "dist", "artifacts", ".wrangler"}
    result = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in excluded for part in relative.parts) or relative.parts[:2] == ("registry", "generated"):
            continue
        if path.suffix in {".pyc", ".log", ".zip", ".sqlite3"} or path.name == ".coverage":
            continue
        result[relative.as_posix()] = path.read_bytes()
    return result


def write_archive(path: Path, files: dict[str, bytes]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(files.items()):
            require(not name.startswith("/") and ".." not in Path(name).parts, "archive_path", "Invalid package path")
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 29, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, content)
    return byte_digest(path.read_bytes())


def endpoint_valid(url: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(url)
        host = (parsed.hostname or "").casefold()
        if parsed.scheme != "https" or not host or parsed.username or parsed.password or parsed.fragment or parsed.query:
            return False
        if host in {"localhost", "example.com", "example.net", "example.org"} or host.endswith((".localhost", ".local", ".invalid", ".example", ".test")) or "<" in url or ">" in url:
            return False
        try:
            if not ipaddress.ip_address(host).is_global:
                return False
        except ValueError:
            if "." not in host:
                return False
        return bool(parsed.path and parsed.path != "/")
    except ValueError:
        return False


def plugin_files(endpoint: str | None = None) -> dict[str, bytes]:
    if endpoint is not None:
        require(endpoint_valid(endpoint), "real_endpoint_required", "Production package requires a real public HTTPS MCP endpoint; no placeholders")
    catalog = load_catalog()
    identity = "agent-policy-governance" if endpoint else "agent-policy-governance-preview"
    manifest = {"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json", "name": identity,
                "version": version, "description": "Apply scoped engineering policies with explicit evidence and capability limits."}
    files = {"plugin.json": canonical(manifest) + b"\n",
             "skills/policy-governance/SKILL.md": (root / "plugins/chatgpt/skills/policy-governance/SKILL.md").read_bytes()}
    topics = sorted({topic for rule in catalog["payload"]["rules"] for topic in rule["topics"] if topic != "always"})
    index = ["# Pinned policy references", "Snapshot: `" + catalog["snapshot_id"] + "`.",
             "Read common.md first, then only needed topic files. Do not read every file. Scope still applies."]
    for topic in ["common", *topics]:
        rules = [rule for rule in catalog["payload"]["rules"] if ("always" if topic == "common" else topic) in rule["topics"]]
        lines = ["# " + topic, "Snapshot: " + catalog["snapshot_id"]]
        for rule in rules:
            lines.extend(["", "## " + rule["rule_id"], "Strength: " + rule["strength"] + "; scope: " + json.dumps(rule["scope"], ensure_ascii=False), rule["statement"], rule["details"]])
        files[f"skills/policy-governance/references/{topic}.md"] = ("\n".join(lines) + "\n").encode("utf-8")
        index.append(f"- {topic}.md: " + ", ".join(rule["rule_id"] for rule in rules))
    files["skills/policy-governance/references/index.md"] = ("\n".join(index) + "\n").encode()
    if endpoint:
        cases = json.loads((root / "docs/submission_cases.json").read_text("utf-8"))
        manifest["extensions"] = {"com.openai": {"review": {"test_cases": cases}, "publication": {"release_notes": "Initial evidence-backed engineering governance package; read-only MCP, no lifecycle hooks."}}}
        files["plugin.json"] = canonical(manifest) + b"\n"
        files["mcp.json"] = canonical({"$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json", "mcpServers": {
            "policy_governance": {"type": "streamable-http", "url": endpoint, "extensions": {"com.openai": {"auth": {"type": "none"}}}}}}) + b"\n"
    return files


def build(destination: Path, endpoint: str | None = None) -> dict:
    generated = root / "registry/generated"
    generated.mkdir(parents=True, exist_ok=True)
    catalog = load_catalog()
    (generated / "policy_data.mjs").write_text("// Generated from policies/catalog.json; do not edit.\nexport default " + canonical(catalog).decode() + ";\n", encoding="utf-8")
    source = source_files()
    source["file_manifest.json"] = canonical({name: byte_digest(data) for name, data in sorted(source.items())}) + b"\n"
    source_name = f"agent_policy_governance_{version}.zip"
    plugin_name = "chatgpt_policy_governance.zip" if endpoint else "chatgpt_policy_governance_preview.zip"
    outputs = {source_name: write_archive(destination / source_name, source), plugin_name: write_archive(destination / plugin_name, plugin_files(endpoint))}
    (destination / "sha256_sums.txt").write_text("".join(f"{digest}  {name}\n" for name, digest in sorted(outputs.items())), encoding="utf-8")
    return {"ok": True, "artifacts": outputs, "officially_published": False, "mcp_configured": endpoint is not None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=root / "dist")
    parser.add_argument("--mcp-url")
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.mcp_url), indent=2))
