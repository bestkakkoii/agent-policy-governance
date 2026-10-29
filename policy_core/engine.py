"""Validated policy snapshots, deterministic matching, and bounded profile discovery."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import digest, read_json, require

root = Path(__file__).resolve().parent.parent
catalog_path = root / "policies/catalog.json"
strengths = {"invariant", "required", "conditional", "default", "reference"}
rule_fields = {"rule_id", "strength", "scope", "topics", "statement", "details", "source", "check"}
identifier_pattern = re.compile(r"(?:[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*|R[0-9]{2})\Z")
tag_pattern = re.compile(r"[a-z][a-z0-9_]*\Z")


def validate_catalog(envelope: Any) -> dict[str, Any]:
    require(isinstance(envelope, dict) and set(envelope) == {"payload", "snapshot_id"},
            "catalog_shape", "Expected a content-addressed policy envelope")
    payload = envelope["payload"]
    require(isinstance(payload, dict) and set(payload) == {"schema_version", "version", "rules"},
            "catalog_shape", "Unexpected policy payload fields")
    require(payload["schema_version"] == 2 and type(payload["schema_version"]) is int,
            "catalog_schema", "Unsupported policy schema")
    require(isinstance(payload["version"], str) and bool(re.fullmatch(r"\d+\.\d+\.\d+", payload["version"])),
            "catalog_version", "Version must be major.minor.patch")
    require(envelope["snapshot_id"] == digest(payload), "snapshot_integrity", "Policy digest mismatch")
    rules = payload["rules"]
    require(isinstance(rules, list) and 0 < len(rules) <= 4096,
            "catalog_rules", "Policy rules must be a nonempty bounded array")
    seen: set[str] = set()
    for item in rules:
        require(isinstance(item, dict) and set(item) == rule_fields,
                "rule_shape", "Unexpected or missing rule fields")
        identity = item["rule_id"]
        require(isinstance(identity, str) and bool(identifier_pattern.fullmatch(identity)) and identity not in seen,
                "rule_identity", "Invalid or duplicate rule ID", rule_id=identity)
        seen.add(identity)
        require(isinstance(item["strength"], str) and item["strength"] in strengths,
                "rule_strength", "Unknown rule strength", rule_id=identity)
        for key in ("scope", "topics"):
            values = item[key]
            require(isinstance(values, list) and len(values) <= 64 and
                    all(isinstance(value, str) and bool(tag_pattern.fullmatch(value)) for value in values),
                    "rule_tags", "Invalid rule tags", rule_id=identity, field=key)
            require(len(values) == len(set(values)), "rule_tags", "Duplicate tag", rule_id=identity)
        require(bool(item["topics"]), "rule_tags", "A rule needs explicit task topics", rule_id=identity)
        for key in ("statement", "details", "source", "check"):
            value = item[key]
            require(isinstance(value, str) and 0 < len(value) <= 10000,
                    "rule_text", "Missing or oversized rule text", rule_id=identity, field=key)
        require(item["check"] in {"reasoning", "file_name", "source_encoding", "evidence", "policy_integrity"},
                "rule_checker", "Unknown rule checker", rule_id=identity)
    return envelope


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    return validate_catalog(read_json(path or catalog_path))


def select_rules(catalog: dict[str, Any], tags: list[str], topics: list[str], *, full: bool = False) -> list[dict[str, Any]]:
    selected = []
    for rule in catalog["payload"]["rules"]:
        if not set(rule["scope"]).issubset(tags):
            continue
        if full or "always" in rule["topics"] or set(rule["topics"]).intersection(topics):
            selected.append(rule)
    return sorted(selected, key=lambda rule: (not rule["rule_id"].startswith("owner."), rule["rule_id"]))


def find_project(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.is_file():
        path = path.parent
    require(path.is_dir(), "project_missing", "Project directory does not exist", path=str(path))
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return path


def discover_profile(project: Path) -> dict[str, Any]:
    """Do not run project code or recursively scan user files to discover a profile."""
    project = find_project(project)
    tags = {"software"}
    evidence = []
    markers = {
        "Cargo.toml": "rust", "go.mod": "go", "pyproject.toml": "python",
        "requirements.txt": "python", "CMakeLists.txt": "cpp", "pom.xml": "java",
        "build.gradle": "java", "package.json": "web", "wails.json": "desktop_gui",
        "tauri.conf.json": "desktop_gui", "project.godot": "game",
    }
    for name, tag in markers.items():
        if (project / name).is_file():
            tags.add(tag)
            evidence.append(name)
    entries = sorted(project.iterdir(), key=lambda path: path.name)[:512]
    extension_tags = {".py": "python", ".rs": "rust", ".go": "go", ".csproj": "csharp",
                      ".sln": "csharp", ".cpp": "cpp", ".cppm": "cpp", ".ixx": "cpp", ".mpp": "cpp",
                      ".cc": "cpp", ".cxx": "cpp", ".vcxproj": "cpp", ".java": "java", ".uproject": "game"}
    for path in entries:
        if path.is_file() and not path.is_symlink() and path.suffix in extension_tags:
            tags.add(extension_tags[path.suffix])
            evidence.append(path.name)
    if (project / "src-tauri/tauri.conf.json").is_file():
        tags.update({"desktop_gui", "rust"})
        evidence.append("src-tauri/tauri.conf.json")
    # Project type is never inferred from an incidental mention in a README.
    return {"project": str(project), "tags": sorted(tags), "evidence": sorted(set(evidence)),
            "confirmation": "detected", "confirmed_by": None}


def infer_topics(text: str) -> list[str]:
    vocabulary = {
        "requirements": ["requirements", "需求", "design", "設計", "architecture", "架構"],
        "quality": ["test", "check", "verify", "build", "lint", "測試", "驗證", "編譯", "檢查"],
        "naming": ["write", "edit", "patch", "implement", "rename", "實作", "命名", "修改"],
        "dependencies": ["library", "package", "dependency", "upgrade", "version", "algorithm", "concept", "paper", "preprint", "experimental", "函式庫", "技術", "升級", "依賴", "最新", "演算法", "算法", "概念", "論文", "實驗性"],
        "network": ["network", "http", "tls", "quic", "socket", "封包", "網路", "協定"],
        "desktop_gui": ["desktop", "gui", "wails", "tauri", "saucer", "桌面", "介面"],
        "rendering": ["render", "gpu", "fps", "shader", "graphics", "繪圖", "渲染", "畫質"],
        "assets": ["asset", "texture", "audio", "model", "素材", "資源", "音效", "動畫"],
        "security": ["security", "crypto", "auth", "defense", "rea", "安全", "加密", "授權", "逆向"],
        "release": ["release", "deploy", "publish", "package", "發行", "發布", "部署", "交付"],
        "update": ["update", "rollback", "recover", "更新", "回復", "恢復"],
        "migration": ["migrate", "migration", "refactor", "existing", "遷移", "重構", "既有"],
        "performance": ["performance", "latency", "memory", "optimize", "efficiency", "效能", "延遲", "占用", "優化"],
        "control_api": ["api", "sdk", "instance", "thread", "client", "接口", "實例", "執行緒", "客戶端"],
        "server": ["server", "database", "transaction", "伺服器", "服務端", "資料庫", "交易"],
        "platform": ["windows", "linux", "macos", "android", "ios", "platform", "docker", "平台"],
        "agents": ["agent", "delegate", "orchestrate", "handoff", "代理", "委派", "協作", "交接"],
        "reuse": ["reuse", "modular", "portable", "重用", "模組", "移植"],
        "cpp": ["c++", "cpp", "module", "cmake", "import std"],
        "qt": ["qt", "qobject", "qwidget"],
    }
    lowered = text.casefold()
    return sorted(topic for topic, words in vocabulary.items() if any(
        word in lowered if not word.isascii() or not word.isalnum()
        else bool(re.search(r"(?<![a-z])" + re.escape(word) + r"[a-z]*(?![a-z])", lowered))
        for word in words))


def format_context(snapshot: str, profile: dict[str, Any], rules: list[dict[str, Any]], *, removed: list[str] | None = None) -> str:
    lines = [f"APG policy snapshot {snapshot}; profile={','.join(profile['tags'])}.",
             "Apply only relevant rules. Owner/current explicit requirements outrank domain defaults. "
             "Rules marked reasoning require evidence; they are not automatically proven. "
             "Do not reread the whole whitepaper. Delegate only for real benefit; pass this snapshot and relevant rules."]
    if removed:
        lines.append("No longer applicable in this context: " + ", ".join(removed))
    for rule in rules:
        lines.append(f"[{rule['rule_id']}:{rule['strength']}] {rule['statement']} {rule['details']}")
    return "\n".join(lines)
