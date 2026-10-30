# Unreleased — write-gate accuracy for Codex and existing projects

Runtime-only fixes; the policy catalog and snapshot are unchanged, and installed hook definitions stay byte-identical, so existing Codex hook trust remains valid after reinstall.

- Naming checks apply only to path components a write creates. New files inside existing non-snake_case directories (for example `BlueCgHP/new_helper.cpp`) are no longer denied; new non-conforming names still are.
- Codex `apply_patch` is recognized as a direct tool, as the documented `["apply_patch", patch]` argv form and as a heredoc (with optional `cd <dir> &&`). Previously the argv and heredoc forms were not gated at all.
- apply_patch additions and update hunks are checked as postimages; `Move to` destinations get name checks; deletions no longer get name checks; relative patch paths resolve from the host working directory instead of the repository root.
- PreToolUse, the `gate` CLI and RPC accept the JSON `tool_input` shapes Codex declares (object, argv array, raw patch, null); an argv array no longer turns every such tool call into a validation-failure denial.
- Content checks deny regressions only. Preimages that already fail (for example JSON with comments), are not UTF-8, are unreadable or too large, derived postimages above the checker limit, and unmatched hunks are reported as `not_checked` and announced to the agent; a non-UTF-8 or locked file no longer crashes Edit checks into a denial.
- Profile discovery reads root `.sln`/`.slnx` project references (`.vcxproj` → `cpp`, `.csproj` → `csharp`) instead of labeling every solution C#; unreadable solutions are recorded in profile `notes`.

Contract-tested on Windows with Python 3.15.2 against the hook schemas embedded in Codex 0.165.0; the naming fix was verified natively in headless Claude Code 2.1.312. Native Codex tool-call verification is pending a live model session.

# v0.2.1 — newest technology and explicit C++ modules

Owner-authorized policy update: C++26 or newer usable/experimental modes, real `import std;`, `export module`, public `export`, consuming `import`, and practical module interface/implementation separation. C++ requirements now remain present for C++ profiles independently of prompt keywords; unrelated profiles are unaffected.

Prefer the newest published/released technologies, algorithms, concepts, previews and experiments on reliable task-relevant theoretical grounds. No stable-label, maturity or measured-superiority prerequisite. Theory evidence records baseline, assumptions and applicability without requiring a measured artifact; empirical performance claims still require measurements. Existing installed-large-toolchain constraints, necessary correctness/security checks, independent review and safe version switching remain.

Adds regression coverage for policy scope, module-project detection, theory admission and rejection paths, packaged Skills and the remote MCP view. Generated references and policy snapshot are refreshed from the single catalog. Existing native-host certification and ChatGPT public-hosting/Directory-approval limitations remain; no new claim of C++ compiler enforcement or measured model-token savings is made. Original source whitepaper hashes are unchanged. See docs/policy_amendments.md for authority and evidence semantics.
