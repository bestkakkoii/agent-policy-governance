# Owner-authorized policy amendments

Authority: explicit project-owner requests in the current conversation on 2026-10-29, supplementing the engineering instructions and whitepaper v6.3.1. This is an owner-authorized baseline change, not a claimed independent agent review. The immutable original whitepaper and its source hashes are unchanged. Execution authority remains policies/catalog.json; this record explains provenance and acceptance.

## cpp_modules

The owner requested mandatory C++26 or newer, including experimental modes, the real standard-library module, and Modules/import/export architecture. This amendment explicitly covers `export module module_name;`, public `export` declarations, consuming `import module_name;`, real `import std;`, and `module module_name;` implementation units. Separate interfaces/declarations from definitions where practical, retaining justified template/inline definitions or partitions. The requirement applies to C++ profiles, not unrelated languages, and is present even when the task prompt omits C++ keywords.

Use the newest applicable compiler/SDK already installed. Missing hard support is a blocker; do not create a fake `stdmodule`, fall back to owned header-only architecture/old standards, or force a large toolchain installation. This amendment is a policy requirement, not a claim that the governance runtime compiles or mechanically proves every C++ module graph.

## latest_technology

The owner's threshold is the newest publicly published or released technology with a credible theoretical advantage, explicitly including algorithms and new concepts. Stable releases, popularity, maturity, prior production use or a benchmark win are not admission gates. A published idea without an existing package may be implemented when feasible and legally usable in the actual environment. Publication alone does not prove an advantage: record the source, assumptions, baseline and workload applicability. Do not invent implementation availability, versions or APIs.

Selection and empirical claims are separate. Theory can justify adoption without a measured artifact; actual improvement claims require measurement. Necessary compatibility, correctness, security and recoverability checks remain. Existing installed-large-toolchain limits and hard product constraints take precedence. Apply changes to technology choices and architecture, not merely version numbers. Normal autonomous policy evolution retains genuinely independent risk-based review and safe-boundary activation; the owner need not participate in technical selection.

## theory_evidence_contract

Existing evidence kinds `fact`, `compatibility`, `performance`, and `security` retain their contract. New `kind: theory` accepts `artifact_sha256: null` and additionally requires nonempty `baseline`, `assumptions`, and `applicability` strings. It also retains `url`, `observed_on`, and `claim`. The claim must explicitly describe expected/theoretical benefit, not pretend to be a measurement. The independent reviewer checks the real primary source and reasoning. Schema acceptance is not proof that a theory is sound or that cited evidence was actually read.

A fixture example (not real research evidence):

```json
{"kind":"theory","url":"https://example.org/theory-fixture","observed_on":"2026-10-29","claim":"Expected lower work under the stated input assumptions; not measured on the target.","artifact_sha256":null,"baseline":"Current full-scan algorithm","assumptions":"Inputs are ordered and updates are sparse.","applicability":"The task already guarantees these input properties."}
```

## acceptance

- Latest-technology preference is in the compact common baseline, without loading all domain rules.
- C++ module/export requirements load for C++ profiles and never leak into a generic non-C++ profile.
- Chinese and English algorithm/concept/research prompts select relevant technology policies.
- Theory proposals without a measured artifact are accepted for independent review; incomplete reasoning, self-review, stale authority and unsupported empirical claims remain rejected.
- Python runtime, remote MCP policy view and packaged Skills share the same content-addressed catalog. References and selector fixtures are regenerated from it.
- Updating an existing installation preserves its admitted snapshot. The installing/maintenance agent must reconcile and admit a newer candidate under the existing review rules; do not claim a running device silently changed policy. New installations use the new bundled baseline. Active tasks switch only at a safe boundary.
