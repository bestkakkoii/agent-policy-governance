---
name: policy-governance
description: Apply the user's authorized engineering and game-development policies to planning, implementation, review, agent handoff, and evidence-backed technical upgrades. Select only the rules relevant to the actual project and task.
---

# Engineering policy governance

Use this workflow when the user has selected this policy integration for engineering work. It is not an instruction to control unrelated plugins, bypass safety, hide errors, or override the user's current request.

Determine the actual project domain, capabilities and environment from available evidence. Resolve technical defaults autonomously, but preserve explicit product constraints. Do not require the user to repeat the whitepaper. Apply common engineering rules to general software, and game rules only to actual game work.

When the policy MCP is connected, call `policy_capabilities` to establish its bounds, then `policy_resolve` with only profile tags and task topics. Do not send source code, prompts, credentials, personal data or filenames. Keep the returned snapshot and rule fingerprints. Request only deltas during an intact conversation. After compaction/handoff, restore the **actual applicable rule text**, not merely IDs. Do not repeatedly read the complete policy catalog.

For a private skills-only preview or unavailable endpoint, use `references/index.md` and only the needed topic files. These are a pinned packaged snapshot, not proof of the latest upstream status. State that guidance is advisory and remote checks were unavailable. Only consult raw source evidence for a real ambiguity; originals are not bundled publicly.

Keep immutable requirements, mandatory conditions, replaceable defaults and observations distinct. Do not add agents, libraries, frameworks, tests or persistent services solely because a policy mentions them. Select installed compatible large toolchains; verify the newest publications/releases and actual upstream mainline revisions before claiming them current. Adopt new technologies, algorithms and concepts, including previews, experiments and published research, when reliable primary evidence and explicit task-relevant reasoning indicate a theoretical advantage; do not wait for measured superiority or stable labels. Keep theoretical benefits distinct from observed results and retain necessary compatibility/correctness/security checks. For C++ profiles, require C++26 or a newer usable experimental mode, real import std;, named Modules/import/export, and practical interface/implementation separation. Consult `references/common.md` for the compact engineering baseline and then only relevant topic references.

Verify factual claims, distinguish executed checks from planned checks, and report concrete failure reasons. Deterministic constraints should use relevant native checks. A source that says an API exists does not prove local support or performance. Never claim blanket prevention of hallucinations or universal output interception.

For policy improvements, prepare exact changes with primary evidence and risks. A genuinely separate agent reviews according to risk before acceptance; never fabricate independence or silently weaken core requirements. This public MCP is read-only and **cannot publish policy changes**. Native local governance can accept reviewed changes at safe task boundaries. Installation does not grant authority over other plugins or automatically install anything on the user's computer.
