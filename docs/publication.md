# Publishing and external authorization

## Native distribution

The repository is the canonical install entry. Release ZIPs have files at archive root (no unnecessary outer folder), contain only source and public curated rules, and include a SHA-256 file manifest. `python install.py` selects the newest suitable installed Python, installs a persistent local copy, and preserves unrelated user configuration. Runtime updates are explicit inspected reinstalls, not untrusted code executed by merely cloning or polling a branch.

## ChatGPT

The private package is `agent-policy-governance-preview` with skills and topic references. It is a private test artifact, not an approved directory entry. Use a different final identity (`agent-policy-governance`) so the official restriction on adding MCP to an already submitted skills-only identity does not trap the production product.

`python tools/package.py --mcp-url https://<real-owned-host>/mcp` produces the formal portable package. The builder rejects localhost, placeholders, credentials and non-HTTPS URLs. It does not pretend a URL is reachable or domain-verified. `registry/worker.mjs` is the Cloudflare Workers deployment entry; generate its catalog module with the package tool, then use the authorized existing deployment account/tooling. No connected hosting account or developer portal access was available in this build session.

Before public submission, the publishing agent must deploy and test the actual endpoint, verify developer identity and the owned domain, complete privacy/listing fields, execute the five positive/three negative cases in `submission_cases.json`, record a reviewer-accessible video, upload the package, and wait for the platform's actual review outcome. A ZIP or GitHub Release is not approval. No fake domain, test account, recording URL or success status may be inserted to bypass these steps.

## Verified official references (2026-10-29)

- https://developers.openai.com/plugins/build/plugins — root plugin.json, skills/, mcp.json, portable naming and exclusion of lifecycle hooks from public directory packages.
- https://developers.openai.com/plugins/deploy/submission — review, domain/developer verification, five positive/three negative cases and walkthrough requirement; skills-only identity limitation.
- https://developers.openai.com/plugins/build/mcp-events — current MCP support.
- https://modelcontextprotocol.io/specification/2026-07-28 — per-request metadata, discovery and Streamable HTTP.
- https://learn.chatgpt.com/docs/hooks — Codex events, hook trust, native failure/coverage limits.
- https://code.claude.com/docs/en/hooks — exec-form command arguments, onFailure block (v2.1.295+), workspace trust.
- https://opencode.ai/docs/plugins — native plugin integration.
- https://github.com/anomalyco/opencode/blob/dev/packages/plugin/src/index.ts — native hook contracts.

No claim that the owner has installed a particular current CLI version is made. Actual live host version/permissions must be inspected by the installation agent.
