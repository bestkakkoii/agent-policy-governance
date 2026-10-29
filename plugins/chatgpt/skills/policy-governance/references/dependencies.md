# dependencies
Snapshot: 6575834e2f9560f90defb39cad9e2e2e0dd013a1ce73c2d7af47378826e6e33a

## owner.latest
Strength: required; scope: []
Prefer and adopt the newest publicly released or published technologies, algorithms and concepts when reliable primary evidence and explicit reasoning support a theoretical advantage for the actual task; measured superiority is not an adoption prerequisite.
Include previews, experimental implementations, research papers, preprints and emerging designs, not just library versions. Do not wait for stability labels, popularity or mature benchmarks. Check publication/source identity, assumptions and applicability; implement a published idea when feasible rather than inventing an existing API. Preserve installed-large-toolchain limits, legal access, hard requirements and necessary correctness/security checks. Label expected benefits as theoretical until measured; record and pin available versions/commits for each run.

## owner.toolchains
Strength: required; scope: []
Use the latest applicable compatible toolchain already installed. Detect actual IDE, compiler, SDK and runtime capabilities; do not force installation/upgrades of large components.
This overrides older whitepaper wording that could force a new toolchain. Use official latest selectors where supported, otherwise detect. Missing hard capabilities are blockers, not permission to downgrade.

## owner.dependencies
Strength: required; scope: []
For open-source dependencies, identify the official actual main development branch, resolve its current commit once, and freeze all direct/indirect inputs for each build and validation.
Do not substitute a familiar release/tag/package version merely for convenience. Record source, observed date, version, commit, options and necessary locks. Exceptions require concrete incompatibility, defects, security or measured harm.

## owner.desktop_stack
Strength: required; scope: ["desktop_gui"]
For desktop GUI without an explicit alternative: Go+Wails, Rust+Tauri, Python+pywebview, C++26+saucer, C#/.NET+Photino.NET, Java+webview_java.
Use latest supported installed/environment-qualified versions. React+TypeScript plus both shadcn/ui and Ant Design must serve real nonduplicate functions; shared visual/state design and light/dark modes. This does not apply to a CLI, library or service. Evidence is required for a minimal exception; never silently default to Qt.

## owner.evolution
Strength: required; scope: []
Improve replaceable policies using reliable facts or theory-supported expected advantages, after independent risk-proportionate agent review. Published algorithms, new concepts and experimental technologies qualify without a prior measured win.
For theory evidence, record the primary source, comparison baseline, assumptions and task applicability. The reviewer checks the reasoning, not a nonexistent benchmark. Do not self-approve, alter core boundaries or fabricate evidence. Empirical performance claims still need measured artifacts; theoretical benefits remain explicitly unverified in the target environment. Required compatibility/correctness/security checks and safe-boundary activation remain; harmful changes require independent recovery review.

## R01
Strength: reference; scope: ["game"]
以當前 2026 年網頁／深度研究為基礎
查核日期、正式來源、固定輸入、事實／推論／未測狀態分開
Authority: [上游快照](10_upstream_snapshots.md)、各專項官方來源
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R25
Strength: required; scope: ["game"]
所有組件、依賴、工具與庫採用最新主線
官方主線身份或最新適用 SDK build、不可變鎖定、選項／補丁／間接閉包；不偷換舊版為最新
Authority: 共通架構〈最新依賴〉、[上游快照](10_upstream_snapshots.md)
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R38
Strength: default; scope: ["game"]
所有實驗性功能、技術、架構、庫均可選
無 stable-only 禁令、無新增人類批准；實驗仍需正確、兼容、性能與退出證據
Authority: 共通底線、平台矩陣、密碼學與 REA 卷
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R40
Strength: conditional; scope: ["game"]
包含 OpenSSL 和完整依賴
`libssl`／`libcrypto`、Provider、CA、Perl 等主機工具、GNS／curl／DB 的真實閉包
Authority: [密碼學與信任鏈](04_crypto_network_trust.md)、依賴總表
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R57
Strength: required; scope: ["game"]
持續評估 HTTP/3／TLS 1.3／後續標準及尚未列出的最新技術
網絡、密碼學、渲染、存儲、編譯器、部署等官方狀態／來源／身份；真實比較、兼容與退出；新技術不等於全部強制啟用
Authority: [技術演進](13_technology_evolution.md)、密碼學／平台／依賴契約
Apply current owner instructions first; dated observations and examples are not current technical facts.
