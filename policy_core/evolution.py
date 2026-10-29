"""Evidence-bound change admission; local identities are attestations, not authentication."""
from __future__ import annotations

import datetime
import urllib.parse
from pathlib import Path
from typing import Any

from .common import digest, require
from .engine import validate_catalog
from .runtime import policy_runtime


def validate_evidence(items: Any) -> None:
    require(isinstance(items, list) and 0 < len(items) <= 32, "evidence_required", "Provide bounded reliable evidence")
    for item in items:
        require(isinstance(item, dict), "evidence_shape", "Evidence must be an object")
        fields = {"url", "observed_on", "claim", "kind", "artifact_sha256"}
        theory_fields = {"baseline", "assumptions", "applicability"}
        if item.get("kind") == "theory":
            fields |= theory_fields
        require(set(item) == fields, "evidence_shape", "Missing or unexpected evidence fields", expected=sorted(fields))
        if item.get("kind") == "theory":
            for field in sorted(theory_fields):
                require(isinstance(item[field], str) and 1 <= len(item[field].strip()) <= 4000,
                        "theory_reasoning", "Theory requires a comparison baseline, assumptions and task applicability", field=field)
        url = urllib.parse.urlsplit(item["url"])
        require(url.scheme == "https" and bool(url.hostname) and not url.username and not url.password,
                "evidence_url", "Evidence must use a non-credentialed HTTPS source URL")
        require(item["kind"] in {"fact", "compatibility", "performance", "security", "theory"}, "evidence_kind", "Unknown evidence kind")
        require(isinstance(item["claim"], str) and 12 <= len(item["claim"]) <= 4000, "evidence_claim", "State a concrete, supported claim")
        date = datetime.date.fromisoformat(item["observed_on"])
        require(date <= datetime.datetime.now(datetime.UTC).date(), "evidence_future", "Evidence observation cannot be future dated")
        artifact = item["artifact_sha256"]
        require(artifact is None or isinstance(artifact, str) and len(artifact) == 64 and all(c in "0123456789abcdef" for c in artifact),
                "evidence_artifact", "Artifact hash must be SHA-256 or null")
        if item["kind"] == "performance":
            require(artifact is not None, "performance_evidence", "Performance improvement claims require a measured artifact digest")


def propose(runtime: policy_runtime, candidate: dict[str, Any], proposer: str, evidence: list[dict[str, Any]],
            risk: str, rationale: str, *, rollback: bool = False) -> dict[str, Any]:
    validate_catalog(candidate)
    validate_evidence(evidence)
    require(bool(proposer.strip()) and len(proposer) <= 256, "actor_required", "Use the actual proposing agent/session identity")
    require(risk in {"low", "high"}, "risk_required", "Risk must be low or high")
    require(20 <= len(rationale) <= 8000, "rationale_required", "Explain scope and technical reason")
    with runtime.store.transaction() as connection:
        base_id = runtime.store.get(connection, "setting", "desired_snapshot")
        base = runtime.catalog_for(connection, base_id)
        old = {rule["rule_id"]: rule for rule in base["payload"]["rules"]}
        new = {rule["rule_id"]: rule for rule in candidate["payload"]["rules"]}
        for rule_id, rule in old.items():
            if rule["strength"] == "invariant":
                require(new.get(rule_id) == rule, "core_invariant_change", "Normal agent evolution cannot alter core invariants", rule_id=rule_id)
        for rule_id, rule in new.items():
            require(rule["strength"] != "invariant" or old.get(rule_id) == rule,
                    "core_invariant_change", "An agent cannot introduce new unreviewable authority", rule_id=rule_id)
        changed = sorted(key for key in set(old) | set(new) if old.get(key) != new.get(key))
        require(bool(changed), "empty_change", "Proposal contains no rule changes")
        if rollback:
            require(runtime.store.get(connection, "snapshot", candidate["snapshot_id"]) is not None,
                    "rollback_unknown", "Rollback target must be a previously admitted local snapshot")
        else:
            require(tuple(map(int, candidate["payload"]["version"].split("."))) > tuple(map(int, base["payload"]["version"].split("."))),
                    "version_not_increased", "Evolution must increment the policy version")
        proposal = {"base_snapshot": base_id, "candidate": candidate, "proposer": proposer,
                    "evidence": evidence, "risk": risk, "rationale": rationale, "changed_rule_ids": changed,
                    "kind": "rollback" if rollback else "evolution"}
        proposal_id = digest(proposal)
        runtime.store.put(connection, "proposal", proposal_id, proposal)
        runtime.store.audit(connection, "proposal", {"proposal_id": proposal_id, "actor": proposer, "risk": risk, "changed": changed})
    return {"ok": True, "proposal_id": proposal_id, "changed_rule_ids": changed, "next": "independent_review",
            "evidence_status": "submitted_not_independently_verified"}


def review(runtime: policy_runtime, proposal_id: str, reviewer: str, approved: bool, findings: str,
           evidence_checked: bool, failure_modes: str = "", rollback_plan: str = "") -> dict[str, Any]:
    require(bool(reviewer.strip()) and len(reviewer) <= 256, "actor_required", "Use the actual reviewer agent/session identity")
    require(40 <= len(findings) <= 12000, "review_findings", "Record substantive independent findings")
    with runtime.store.transaction() as connection:
        proposal = runtime.store.get(connection, "proposal", proposal_id)
        require(proposal is not None, "proposal_missing", "Unknown proposal")
        require(reviewer != proposal["proposer"], "self_review_forbidden", "The proposer cannot approve their own change")
        require(runtime.store.get(connection, "setting", "desired_snapshot") == proposal["base_snapshot"],
                "stale_review", "Rebase proposal before independent review")
        if approved:
            require(evidence_checked, "evidence_not_checked", "Reviewer must actually inspect the cited evidence")
            if proposal["risk"] == "high":
                require(len(failure_modes) >= 30 and len(rollback_plan) >= 30, "deep_review_required",
                        "High-risk review needs concrete failure-mode and rollback analysis")
        result = {"proposal_id": proposal_id, "reviewer": reviewer, "approved": approved, "findings": findings,
                  "evidence_checked": evidence_checked, "failure_modes": failure_modes, "rollback_plan": rollback_plan,
                  "identity_assurance": "local_agent_attestation_not_cryptographic_independence"}
        runtime.store.put(connection, "review", proposal_id, result)
        runtime.store.audit(connection, "review", {"proposal_id": proposal_id, "reviewer": reviewer, "approved": approved})
    return {"ok": True, **result}


def publish(runtime: policy_runtime, proposal_id: str) -> dict[str, Any]:
    with runtime.store.transaction() as connection:
        proposal = runtime.store.get(connection, "proposal", proposal_id)
        review_result = runtime.store.get(connection, "review", proposal_id)
        require(proposal is not None and review_result is not None, "review_required", "Proposal and independent review are required")
        require(review_result["approved"] and review_result["evidence_checked"] and review_result["reviewer"] != proposal["proposer"],
                "review_rejected", "Proposal lacks independent approval")
        current = runtime.store.get(connection, "setting", "desired_snapshot")
        require(current == proposal["base_snapshot"], "stale_policy_base", "Published authority changed; rebase and re-review")
        candidate = validate_catalog(proposal["candidate"])
        snapshot = candidate["snapshot_id"]
        runtime.store.put(connection, "snapshot", snapshot, candidate)
        runtime.store.put(connection, "setting", "desired_snapshot", snapshot)
        runtime.store.audit(connection, "published", {"proposal_id": proposal_id, "snapshot_id": snapshot, "reviewer": review_result["reviewer"]})
    return {"ok": True, "snapshot_id": snapshot, "activation": "next_quiescent_project_boundary"}
