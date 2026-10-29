# agents
Snapshot: 08cba5b9a39218449c769d90644644cf7f6d11973a96b08f0fdb30d38535d13d

## owner.documentation
Strength: required; scope: []
Keep README_AI.md as the authority entry; use minimal native AGENTS.md/CLAUDE.md referrals instead of duplicating full policy documents.
Document rationale, invariants, ownership, threading, side effects and failure behavior, not obvious code. Keep prior project instructions intact.

## owner.agents
Strength: required; scope: []
Delegate only when parallelism or specialist independence yields real benefit. Pass applicable rules, scope, ownership, evidence and next steps to actual delegates.
Do not force a new agent/team for every task. The main agent integrates consistency; reviewers are not authors of the change they approve. No universal JSON-only communication.

## owner.evolution
Strength: required; scope: []
Improve replaceable policies when reliable evidence supports the change, after independent risk-proportionate agent review under the previous policy.
No self-approval, core-boundary changes or invented evidence. Claims of performance/security/correctness need evidence appropriate to the claim. A snapshot changes only at a safe task boundary; harmful changes require independent recovery review.

## owner.privacy
Strength: required; scope: []
Keep project code, prompts, credentials and private documents local by default. Remote governance receives only necessary profile metadata, rule IDs and explicitly minimized evidence.
Public registry lookup must not upload a project or launch local commands.

## R21
Strength: required; scope: ["game"]
多 Agent 協作、完全技術自治
工作樹、路徑責任、接口契約、委派政策傳遞、真實權限隔離和獨立驗收
Authority: 共通架構〈多 Agent／Git／CI〉
Apply current owner instructions first; dated observations and examples are not current technical facts.
