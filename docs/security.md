# Security and privacy boundaries

## Trust model

This is user-account automation, **not** a sandbox against a hostile process running as the same user. The installer preserves unrelated configuration, uses managed blocks, an OS lock and an undo journal, and refuses detected symlinks/conflicting edits. An attacker who can change Python, the database, trusted hook configuration or the OS can bypass this system. File hashes detect accidental/tampered content against a known identity; they are not signatures proving publisher identity. Upstream content uses fixed-origin HTTPS and immutable Git commit URLs; signed attestation distribution is not implemented.

Authority operations use exact candidate digests and compare-and-swap publication. Distinct actor IDs and evidence attestations are required, but actor IDs alone do not cryptographically prove different models/processes. Genuine independent review must be supplied by the native host's actual delegation mechanism. No review has occurred merely because a fixture test passes.

## Data handling

Local SQLite stores profile facts, session identifiers, rule versions/fingerprints, minimal audit events and review evidence. Original task prompts are used transiently for local topic extraction and not saved. Audit retention is bounded to 2,000 events. Original whitepaper import, repair backups and source excerpts stay local. Uninstall preserves them intentionally.

The public Registry accepts only bounded tags/topics/rule identities, not project source, filenames, prompts, credentials or private evidence. It is read-only and has no application-level persistent user records. Hosting-provider network/security logs remain subject to the provider's policy; no claim of zero provider logging is made.

Optional local RPC binds numeric loopback, validates Host, rejects browser Origin, uses a private unpredictable bearer token, bounds bodies/concurrency/timeouts and disables proxy use. It exposes no shell execution or authority publication. Embedded fallback logs causes and restores ambiguous context. Never expose it publicly.

## Coverage

Codex/Claude/OpenCode adapter contracts are tested independently of authenticated model sessions. Native hosts can disable hooks, bypass unsupported tool paths, or truncate context. Arbitrary shell side effects are not parsed as trusted file operations; the only command-style write recognized is an explicit Codex `apply_patch` invocation (direct tool, `["apply_patch", patch]` argv, or `apply_patch` heredoc with an optional `cd <dir> &&`). Supported direct-write checks cover available path/content facts only: names are checked only for path components the write creates, so existing directories are never treated as new names; `Move to` destinations are new names, deletions are not; relative paths resolve from the host working directory. Content checks use the reconstructed postimage (Write content, unique Edit replacement, apply_patch additions, and update hunks matched with the Codex exact/trailing/surrounding-whitespace order) and deny only regressions: a preimage that already fails the same check, is not UTF-8, is unreadable or exceeds the limit, a derived postimage above the limit, or hunks that cannot be matched are reported as `not_checked` and announced to the agent as not verified. Hooks, the `gate` CLI and RPC accept the same tool-input shapes (object, argv array, raw patch, null); other scalars fail explicitly. Full application correctness and semantic policy compliance still require the actual project checks and agent evidence.

The ChatGPT package includes no lifecycle hooks and cannot intercept all ChatGPT responses or unrelated tools. Public listing requires OpenAI review. Never weaken host trust prompts, developer verification, domain verification or safety restrictions to make installation look automatic.
