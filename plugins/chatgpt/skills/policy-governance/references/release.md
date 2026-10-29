# release
Snapshot: 6575834e2f9560f90defb39cad9e2e2e0dd013a1ce73c2d7af47378826e6e33a

## owner.documentation
Strength: required; scope: []
Keep README_AI.md as the authority entry; use minimal native AGENTS.md/CLAUDE.md referrals instead of duplicating full policy documents.
Document rationale, invariants, ownership, threading, side effects and failure behavior, not obvious code. Keep prior project instructions intact.

## owner.release_defense
Strength: conditional; scope: []
Apply asset-specific repeatable release defenses that increase unauthorized analysis/tampering cost without burdening normal development or user recovery.
Control unnecessary symbols, source maps, internal paths and debug leakage. Preserve authorized SDK/API boundaries and private diagnostics. No junk text, prompt traps, source pollution, arbitrary bloat or impossible anti-reversing guarantees.

## owner.privacy
Strength: required; scope: []
Keep project code, prompts, credentials and private documents local by default. Remote governance receives only necessary profile metadata, rule IDs and explicitly minimized evidence.
Public registry lookup must not upload a project or launch local commands.

## R43
Strength: required; scope: ["game"]
全方位診斷與可觀測性
明確原因與上下文、限額／脫敏、Build ID 對應符號，錯誤不被保護層吞掉
Authority: 共通診斷／CI／運維、REA 私有符號
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R48
Strength: reference; scope: ["game"]
產出 Markdown 並打包 ZIP
完整文件、相對鏈接、ZIP CRC、解壓後逐文件摘要一致
Authority: [交付驗證](11_delivery_validation.md)、[摘要](sha256_sums.md)
Apply current owner instructions first; dated observations and examples are not current technical facts.
