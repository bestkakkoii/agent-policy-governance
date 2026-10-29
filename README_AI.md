# Agent entrypoint

Project: agent_policy_governance

1. Read this document first. Policy data is canonical once admitted and reviewed; the source whitepaper remains immutable evidence.
2. Policies apply by project profile and task capability, not by blindly loading every rule.
3. Treat mandatory/conditional/default/reference classes separately. Never promote historical observations to current verified facts.
4. Do not claim hard enforcement without an actual verified tool boundary. ChatGPT plugin availability does not imply automatic control of local CLIs.
5. Run `python -m unittest discover -s tests -v` and `python -m policy_core.cli resolve --domain software --capability code_quality` after modifying the prototype.
6. Never mutate user projects, global instructions, credentials, or CLI configuration without a supported and authorized integration step.
7. A policy evolution proposal must cite evidence, preserve its source, and undergo independent review; an agent must not approve its own proposal.
8. Current limitations and milestones live in `docs/status.md`. Do not misrepresent planned features as implemented.

Naming: snake_case for owned paths and identifiers; README_AI.md and external SDK contracts are explicit exceptions.
