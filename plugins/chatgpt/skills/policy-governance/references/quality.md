# quality
Snapshot: 6575834e2f9560f90defb39cad9e2e2e0dd013a1ce73c2d7af47378826e6e33a

## owner.toolchains
Strength: required; scope: []
Use the latest applicable compatible toolchain already installed. Detect actual IDE, compiler, SDK and runtime capabilities; do not force installation/upgrades of large components.
This overrides older whitepaper wording that could force a new toolchain. Use official latest selectors where supported, otherwise detect. Missing hard capabilities are blockers, not permission to downgrade.

## owner.dependencies
Strength: required; scope: []
For open-source dependencies, identify the official actual main development branch, resolve its current commit once, and freeze all direct/indirect inputs for each build and validation.
Do not substitute a familiar release/tag/package version merely for convenience. Record source, observed date, version, commit, options and necessary locks. Exceptions require concrete incompatibility, defects, security or measured harm.

## owner.naming
Strength: required; scope: []
Use meaningful lowercase snake_case for owned projects, directories, files and identifiers. Preserve required external names and README_AI.md/AGENTS.md/CLAUDE.md.
No meaningless ordinal/address/collision suffixes. Legitimate domain numbers such as sha256/ipv6 are not automatically violations. Do not rename existing external ABI, protocol fields or user data blindly.

## owner.encoding
Strength: required; scope: []
Store text as UTF-8; choose BOM only when the actual format or toolchain requires or benefits from it.
Do not impose BOM on every file or accept invalid UTF-8 as success.

## owner.cpp_modules
Strength: required; scope: ["cpp"]
All owned C++ core and interfaces require C++26 or a newer usable standard, including the latest available experimental mode, and a real named Modules/import/export architecture with toolchain-provided import std;.
Use export module module_name; for module interface units, export only intended public declarations, import module_name; at consumers, and module module_name; for implementation units. Separate public declarations and implementation definitions where practical; keep justified template/inline definitions in interfaces or appropriate partitions. Use the real standard-library module, never a fabricated stdmodule shim. Includes are limited to necessary SDK, third-party and non-module boundaries, not an alternate owned-core header architecture. Use the newest compatible installed compiler/SDK mode. Missing C++26, named-module or standard-library-module support is a blocker, not permission to downgrade or force a large toolchain installation.

## owner.cpp_style
Strength: required; scope: ["cpp"]
Use Allman braces without omission, semantic snake_case, RAII and clear single ownership; avoid unnecessary macros, globals, shared_ptr and goto.
Order access public/protected/private; separate member functions. Evaluate PIMPL when more than one member exists, without sacrificing measured efficiency. Expected errors use explicit outcomes; preserve real exception roots at boundaries.

## owner.static_quality
Strength: required; scope: []
Run the strongest relevant effective static, type, lint and build checks, with warnings as errors where viable. Fix scope-relevant real issues; never hide diagnostics to obtain green results.
Do not blanket suppress rules, exclude code arbitrarily or stack redundant tools. Distinguish pre-existing issues and minimal evidenced false-positive exceptions.

## owner.risk_tests
Strength: required; scope: []
Select dynamic tests by change risk, impact and benefit; preserve relevant existing tests and meaningful assertions.
Do not pursue artificial counts/coverage or test trivialities for ceremony. Necessary correctness risks unsupported by static analysis need runtime verification.

## owner.diagnostics
Strength: required; scope: []
Preserve stage, location, original error code/message, necessary context and outcome for real failures. Bound retries and retain the first cause.
Never swallow exceptions, silently fall back, suppress distinct failures or present failure as success. Keep diagnostics bounded and redact secrets.

## R22
Strength: required; scope: ["game"]
Git、CI、單元測試完整
Git 集成 tree、可信 gates、Catch2／CTest 或等價基礎及核心規則／失敗測試
Authority: 共通架構〈Git／CI／測試〉
Apply current owner instructions first; dated observations and examples are not current technical facts.
