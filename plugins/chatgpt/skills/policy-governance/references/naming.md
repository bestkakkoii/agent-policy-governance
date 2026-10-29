# naming
Snapshot: 08cba5b9a39218449c769d90644644cf7f6d11973a96b08f0fdb30d38535d13d

## owner.naming
Strength: required; scope: []
Use meaningful lowercase snake_case for owned projects, directories, files and identifiers. Preserve required external names and README_AI.md/AGENTS.md/CLAUDE.md.
No meaningless ordinal/address/collision suffixes. Legitimate domain numbers such as sha256/ipv6 are not automatically violations. Do not rename existing external ABI, protocol fields or user data blindly.

## owner.encoding
Strength: required; scope: []
Store text as UTF-8; choose BOM only when the actual format or toolchain requires or benefits from it.
Do not impose BOM on every file or accept invalid UTF-8 as success.

## owner.cpp_style
Strength: required; scope: ["cpp"]
Use Allman braces without omission, semantic snake_case, RAII and clear single ownership; avoid unnecessary macros, globals, shared_ptr and goto.
Order access public/protected/private; separate member functions. Evaluate PIMPL when more than one member exists, without sacrificing measured efficiency. Expected errors use explicit outcomes; preserve real exception roots at boundaries.

## owner.static_quality
Strength: required; scope: []
Run the strongest relevant effective static, type, lint and build checks, with warnings as errors where viable. Fix scope-relevant real issues; never hide diagnostics to obtain green results.
Do not blanket suppress rules, exclude code arbitrarily or stack redundant tools. Distinguish pre-existing issues and minimal evidenced false-positive exceptions.

## owner.diagnostics
Strength: required; scope: []
Preserve stage, location, original error code/message, necessary context and outcome for real failures. Bound retries and retain the first cause.
Never swallow exceptions, silently fall back, suppress distinct failures or present failure as success. Keep diagnostics bounded and redact secrets.
