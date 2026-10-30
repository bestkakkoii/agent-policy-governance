# Architecture and acceptance contract

## Ownership

| Module | Owns | Does not own |
| --- | --- | --- |
| engine | Catalog validation, scope selection, bounded profile facts | Semantic truth or current upstream facts |
| runtime | Sessions, deltas, recovery, project pins, bounded checks | Arbitrary shell containment |
| common | Atomic files, transaction store, diagnostics, locks | Host credential management |
| install | Managed host configuration and reversible runtime selection | Host trust approvals |
| evolution | Evidence-bound proposals, independent attestation, CAS admission | Inventing independent agents |
| sync | Fixed-repository commit-pinned candidate download | Unreviewed policy/code activation |
| source | Verified private archive and line-level evidence | Publishing complete private originals |
| service | Optional authenticated local RPC using the same core | Mandatory background process |
| adapters | Host events and context transport | Alternate policy semantics |
| registry | Stateless read-only MCP view of public catalog | Project execution or authority mutation |

## State and concurrency

A catalog is an immutable schema-validated payload plus SHA-256 content identity. It is not a digital signature. SQLite WAL and short explicit transactions serialize updates. Every project has a confirmed profile and pinned policy snapshot; every session records active/idle state and delivered fingerprints. The project may advance to desired_snapshot only when **all** its sessions are idle. A crashed host can leave an active session: the recovery agent must inspect the affected task and explicitly finish that real abandoned session before advancing, never silently expire a still-running peer.

Embedded execution is the default. If a service endpoint exists, adapters reuse it with authentication. Failures are logged and fall back to the identical core; context is restored when delivery was uncertain. No daemon is automatically started, no separate semantics are maintained. Raw-source content and raw prompts are never part of remote sync.

The first confirmed profile is an agent decision based on available project facts. Initial detector output is deliberately conservative. New task keywords select topics, not new domains. A change to the profile requires an idle boundary. Current explicit owner constraints outrank historic whitepaper defaults; game-only requirements stay game-scoped.

## Acceptance matrix

| Contract | Test evidence |
| --- | --- |
| 28 owner rules and R01–R71 are traceable | Catalog/source manifest tests; exact original hash audit performed separately |
| Irrelevant game rules are absent | Generic project and topic-domain separation tests |
| Context restores actual text after restart/compact | Session/delta/fresh tests and OpenCode subprocess adapter tests |
| Parallel agents pin one snapshot | Concurrent context and safe-boundary tests |
| No silent self-approval or stale overwrite | Independent actor, evidence, immutable-rule, high-risk and CAS tests |
| Installation preserves prior content | Repeat install, uninstall, edited config, injected write failure and journal conflict tests |
| Local outage does not lose accepted rules | Invalid service/offline sync tests |
| Supported direct writes can be denied | Native JSON contracts, Codex apply_patch direct/argv/heredoc, move/delete, cwd-relative and postimage-regression tests, OpenCode before-tool rejection tests |
| New-name checks spare existing paths | Existing-ancestor, new-component and solution-reference profile tests |
| MCP metadata is bounded and read-only | Protocol, origin/header/body/field, snapshot and cross-language selector tests |
| Packages deterministic and private-source-free | Reproducible ZIP and package-content tests |

A passed unit/contract test is not an authenticated real-host test. Reports must identify the actual OS/runtime used. The same suite runs on Windows/macOS/Linux CI without installing a new large language toolchain. A host without suitable preinstalled Python/Node fails explicitly rather than downloading one silently.

## Cost measurement

Record exact injected UTF-8 bytes, delta sizes and check latency. Native token counts remain null unless the host exposes actual values. File-cache hits are not model-token savings. OpenCode rebuilds system arrays per model request, so the adapter restores the complete applicable slice there instead of incorrectly sending only a delta. Provider prefix caching is outside this system's guarantees.

## Deliberate limits

No opaque binary obfuscation, extra LLM per tool call, compulsory role roster or background service. No huge runtime installation. No API credential requirement for local operation. No remote project source. No automatic source-code self-update. No full semantic theorem prover. No claims of complete whitepaper-prose compilation, cryptographically authenticated independent review, live host certification, or public ChatGPT approval before evidence exists.
