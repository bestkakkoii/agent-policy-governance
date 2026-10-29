# Release evidence: 0.2.0

## Observed, not planned

On 2026-10-29 the exact 63-file source transfer was verified on actual GitHub-hosted Windows, macOS and Ubuntu runners before source publication:

https://github.com/bestkakkoii/agent-policy-governance/actions/runs/40853605614

All three verification jobs and the source-publication job completed successfully. Each platform ran the 43 Python tests and 17 JavaScript tests, including real subprocess/local HTTP calls, reversible install/reinstall/uninstall, failure recovery, context restore, concurrent version pins, independent-review bookkeeping, MCP contracts and reproducible packaging. These are application and adapter-contract tests, not authenticated native model-session tests.

Source-publication commit: `14578539e510294ed51a624e48934b6ed51c28fb`.
Source transfer SHA-256: `6e18075252ed28ed3487abd2becf5a3af14684f33987f45ff8cd7b95bcfd4695`.
Policy snapshot: `08cba5b9a39218449c769d90644644cf7f6d11973a96b08f0fdb30d38535d13d`.

The earlier delivery attempt passed all OS tests but publication was rejected because the Actions token cannot change workflow definitions. The successful publication preserved the existing workflow; the owner's authorized GitHub connector separately installed the final workflow. No token privileges or platform trust were bypassed.

## Final distribution gate

The main-branch workflow verifies the checked-out source on all three OS families, then builds the exact release assets and attaches `verification.json` and `sha256_sums.txt`. The report records selected installed runtimes, source-file hashes, commands, exit statuses and package identities. Check the tag's workflow result rather than treating this document as proof that a subsequent run passed.

The local build also passed strict JavaScript checking with the already installed TypeScript compiler (`--allowJs --checkJs --noEmit --strict --target es2023 --module nodenext --moduleResolution nodenext`) for the MCP handler and OpenCode adapter. No tools were downloaded to invent an environment result.

## Boundaries that remain unverified or external

- Authenticated Codex, Claude Code and OpenCode model sessions on the owner's devices; native trust must be respected and activation tested by the installing agent.
- Arbitrary shell side effects and every model response are not globally intercepted.
- The curated R01-R71 plus 28 owner rules are not a mechanical executable conversion of every whitepaper sentence.
- Reviewer actor IDs and hashes are not cryptographic proof of independent humans/agents or a signed publisher identity.
- The unchanged embedded-context fixture returns zero additional bytes; no end-to-end model token reduction percentage has been measured.
- No public MCP endpoint has been deployed and no ChatGPT Directory approval has been obtained. The skills-only ZIP is a separate private preview identity.

These limits remain visible in README_AI.md, the doctor output and release notes.
