# reuse
Snapshot: 08cba5b9a39218449c769d90644644cf7f6d11973a96b08f0fdb30d38535d13d

## owner.architecture
Strength: required; scope: []
Prefer high cohesion, low coupling, explicit contracts/ownership, traceable data flow and independently modifiable boundaries.
Avoid needless abstraction, split files, frameworks or duplicate state. Preserve correctness/recoverability before speed and footprint.

## owner.reuse
Strength: required; scope: []
Evaluate actual cross-project reuse at meaningful boundaries; extract a package only when consumers, dependencies and total cost justify it.
Keep identity, license, ABI/schema, ownership and consumer verification explicit. Never manufacture a generic engine just to satisfy reuse.

## R71
Strength: required; scope: ["game"]
每款遊戲製作時評估功能、模組、庫、SDK、資源及工具能否快速重用到其他項目
各實際邊界的選擇／理由；選中包的唯一來源、正式接入、平台及 ABI／schema／資源身份、許可、依賴閉包、獨立消費者證據、更新及回退影響；不強制全抽通用引擎或 DLL
Authority: [跨項目重用](18_cross_project_reuse.md)、共通目錄／功能、依賴、SDK、構建與遷移
Apply current owner instructions first; dated observations and examples are not current technical facts.
