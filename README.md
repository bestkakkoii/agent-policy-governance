# Agent Policy Governance

Cross-agent policy governance, built from evidence-backed structured policies rather than repeatedly injecting full whitepapers.

**Status: initial prototype.** No universal enforcement, ChatGPT Directory submission, or automatic CLI hook registration is claimed.

## Goals

- Always-on governance, on-demand policy matching.
- Content-addressed, reproducible policy snapshots.
- Respect explicit project requirements and distinguish mandatory policies from conditional guidance.
- Run without a resident service for single-process use; support a shared local service in later phases.
- Keep policy changes independently reviewable, never silently rewrite source evidence.

## Quick start (prototype)

```sh
git clone https://github.com/bestkakkoii/agent-policy-governance.git
cd agent-policy-governance
python -m unittest discover -s tests -v
python -m policy_core.cli resolve --domain software --capability code_quality
python -m policy_core.cli resolve --domain game --capability rendering
```

Requires Python 3.10+ standard library for this bootstrap prototype, **not** a mandatory target runtime version. The release implementation must discover supported toolchains rather than install large runtimes automatically.

This command **does not yet install into Codex, Claude Code, OpenCode, Orca or ChatGPT**. Installation hooks are intentionally excluded until their behavior is verified.

See [README_AI.md](README_AI.md) and [status](docs/status.md).
