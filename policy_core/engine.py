"""Deterministic policy selection and reproducible snapshot hashing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class PolicyError(ValueError):
    """Invalid policy data; do not silently treat it as valid."""


def load_policy(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise PolicyError("policy schema_version must be 1")
    rules = data.get("rules")
    if not isinstance(rules, list):
        raise PolicyError("rules must be an array")
    seen: set[str] = set()
    required = {"rule_id", "domains", "capabilities", "level", "description", "source"}
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict) or not required.issubset(rule):
            raise PolicyError(f"rule at index {index} lacks required fields")
        rule_id = rule["rule_id"]
        if not isinstance(rule_id, str) or not rule_id or rule_id in seen:
            raise PolicyError(f"invalid or duplicated rule_id: {rule_id!r}")
        seen.add(rule_id)
        if rule["level"] not in {"invariant", "mandatory", "conditional", "default", "reference"}:
            raise PolicyError(f"invalid level for {rule_id}")
        for key in ("domains", "capabilities"):
            if not isinstance(rule[key], list) or not rule[key] or not all(
                isinstance(item, str) and item for item in rule[key]
            ):
                raise PolicyError(f"invalid {key} for {rule_id}")
        for key in ("description", "source"):
            if not isinstance(rule[key], str) or not rule[key].strip():
                raise PolicyError(f"invalid {key} for {rule_id}")
    return data


def snapshot_id(data: dict[str, Any]) -> str:
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def resolve(data: dict[str, Any], domain: str, capability: str) -> dict[str, Any]:
    selected = [
        rule for rule in data["rules"]
        if ("*" in rule["domains"] or domain in rule["domains"])
        and ("*" in rule["capabilities"] or capability in rule["capabilities"])
    ]
    return {
        "snapshot_id": snapshot_id(data),
        "domain": domain,
        "capability": capability,
        "matched_rule_count": len(selected),
        "rules": selected,
    }
