# cpp
Snapshot: 6575834e2f9560f90defb39cad9e2e2e0dd013a1ce73c2d7af47378826e6e33a

## owner.toolchains
Strength: required; scope: []
Use the latest applicable compatible toolchain already installed. Detect actual IDE, compiler, SDK and runtime capabilities; do not force installation/upgrades of large components.
This overrides older whitepaper wording that could force a new toolchain. Use official latest selectors where supported, otherwise detect. Missing hard capabilities are blockers, not permission to downgrade.

## owner.cpp_modules
Strength: required; scope: ["cpp"]
All owned C++ core and interfaces require C++26 or a newer usable standard, including the latest available experimental mode, and a real named Modules/import/export architecture with toolchain-provided import std;.
Use export module module_name; for module interface units, export only intended public declarations, import module_name; at consumers, and module module_name; for implementation units. Separate public declarations and implementation definitions where practical; keep justified template/inline definitions in interfaces or appropriate partitions. Use the real standard-library module, never a fabricated stdmodule shim. Includes are limited to necessary SDK, third-party and non-module boundaries, not an alternate owned-core header architecture. Use the newest compatible installed compiler/SDK mode. Missing C++26, named-module or standard-library-module support is a blocker, not permission to downgrade or force a large toolchain installation.

## owner.cpp_style
Strength: required; scope: ["cpp"]
Use Allman braces without omission, semantic snake_case, RAII and clear single ownership; avoid unnecessary macros, globals, shared_ptr and goto.
Order access public/protected/private; separate member functions. Evaluate PIMPL when more than one member exists, without sacrificing measured efficiency. Expected errors use explicit outcomes; preserve real exception roots at boundaries.

## R10
Strength: invariant; scope: ["game"]
自研核心是純 C++26 模組化產品代碼
核心語言與特性探針；必要 C 庫、shader、平台橋接和外部工具語言分列
Authority: 共通架構〈C++ 模組〉、平台矩陣
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R11
Strength: invariant; scope: ["game"]
使用 `import std;`
真正標準庫模組、正確 compiler／STL／SDK／scanner／BMI、compile/link/run 證據
Authority: [平台矩陣](05_platform_qualification.md)、兩端工具鏈章
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R20
Strength: required; scope: ["game"]
嚴格命名、用語、語言、排版
全小寫 snake_case 與完整語意；工具可檢查、生成器一致、外部契約精確例外和有效診斷
Authority: 共通架構〈代碼標準〉、Agent 啟動模板
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R58
Strength: invariant; scope: ["game"]
自有命名全小寫 snake_case，涵蓋代碼識別字、代碼文件和目錄，並以完整語意降低誤解
類型／模板／函數／成員／枚舉／常量與自有路徑一致；單位、狀態、副作用明確；禁止任意編號、序數、地址、修訂與撞名後綴；真實領域數字及固定 `README_AI.md`／外部身份保留。檢查器以固定工具及正反例證明作用，語意及舊符號重建另有證據；不捏造效率數值
Authority: [共通命名規範](01_common_architecture.md#section-05)、[Agent 啟動](09_agent_bootstrap.md)
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R61
Strength: required; scope: ["game"]
架構同時考慮編譯速度、PCH、合理頭文件自足、PIMPL 及其它構建優化
真正 Modules／import std 不變；接口／生成／增量正確性、合格加速選型、同條件乾淨／增量／鏈接成本與主機峰值、多 Agent 隔離；不以 runtime 退化、漏依賴或失效緩存冒充加速
Authority: [構建效能專卷](16_build_throughput.md)、共通接口／CI、兩端、平台、依賴及重構流程
Apply current owner instructions first; dated observations and examples are not current technical facts.
