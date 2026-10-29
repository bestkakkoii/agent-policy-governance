# Implementation status

## Implemented in the initial prototype
- Repository entrypoint and explicit development instructions.
- Deterministic selection of structured policy records by domain and capability.
- Validation of policy record shape and duplicate identifiers.
- Content-derived snapshot identifier and reproducible JSON output.
- Standard-library regression tests.

## Not yet implemented
- Full rule-by-rule conversion of source whitepaper 6.3.1 (18 chapters).
- Signed snapshots, immutable Git releases, delta distribution, cache invalidation, IPC/local daemon.
- Independent review workflow, rule evaluation against actual source code, safe auto-remediation.
- Codex, Claude Code, OpenCode, Orca hooks and installers.
- ChatGPT Universal Plugin, remote MCP, submission/approval.
- Token savings measurements or guaranteed enforcement.

## Primary source
Uploaded source in planning conversation: online_game_agent_whitepapers_v6_3_1_2026_10_23(2).zip (20 files, including README_AI.md, 18 numbered chapters, sha256_sums.md). This source has **not** been committed to the public repository; redistribution and classification require review.

## Product contract
- Existing 21 confirmed decisions remain requirements.
- Policy definitions are structured canonical data after approved conversion; original text is evidence.
- Project profile auto-detection followed by persistence.
- Safe repairs only; uncertain cases require reasoning or blocking.
- A new snapshot becomes effective at the next safe task boundary.
- Git authority + remote registry, local cache first, minimal metadata remotely.
- Hybrid embedded / local service deployment chosen by measured benefit.
- Public ChatGPT plugin and separate native CLI adapters; do not assert control over platform-unavailable operations.
