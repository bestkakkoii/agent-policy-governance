# requirements
Snapshot: 6575834e2f9560f90defb39cad9e2e2e0dd013a1ce73c2d7af47378826e6e33a

## owner.requirements
Strength: required; scope: []
For a new ambiguous product task, group substantive questions with options and recommended defaults before implementation; skip formal interviews for simple facts, confirmed continuations or explicit autonomous execution.
Do not let interview machinery replace completing an authorized task.

## owner.latest
Strength: required; scope: []
Prefer and adopt the newest publicly released or published technologies, algorithms and concepts when reliable primary evidence and explicit reasoning support a theoretical advantage for the actual task; measured superiority is not an adoption prerequisite.
Include previews, experimental implementations, research papers, preprints and emerging designs, not just library versions. Do not wait for stability labels, popularity or mature benchmarks. Check publication/source identity, assumptions and applicability; implement a published idea when feasible rather than inventing an existing API. Preserve installed-large-toolchain limits, legal access, hard requirements and necessary correctness/security checks. Label expected benefits as theoretical until measured; record and pin available versions/commits for each run.

## owner.architecture
Strength: required; scope: []
Prefer high cohesion, low coupling, explicit contracts/ownership, traceable data flow and independently modifiable boundaries.
Avoid needless abstraction, split files, frameworks or duplicate state. Preserve correctness/recoverability before speed and footprint.

## owner.documentation
Strength: required; scope: []
Keep README_AI.md as the authority entry; use minimal native AGENTS.md/CLAUDE.md referrals instead of duplicating full policy documents.
Document rationale, invariants, ownership, threading, side effects and failure behavior, not obvious code. Keep prior project instructions intact.

## owner.desktop_stack
Strength: required; scope: ["desktop_gui"]
For desktop GUI without an explicit alternative: Go+Wails, Rust+Tauri, Python+pywebview, C++26+saucer, C#/.NET+Photino.NET, Java+webview_java.
Use latest supported installed/environment-qualified versions. React+TypeScript plus both shadcn/ui and Ant Design must serve real nonduplicate functions; shared visual/state design and light/dark modes. This does not apply to a CLI, library or service. Evidence is required for a minimal exception; never silently default to Qt.

## owner.cpp_modules
Strength: required; scope: ["cpp"]
All owned C++ core and interfaces require C++26 or a newer usable standard, including the latest available experimental mode, and a real named Modules/import/export architecture with toolchain-provided import std;.
Use export module module_name; for module interface units, export only intended public declarations, import module_name; at consumers, and module module_name; for implementation units. Separate public declarations and implementation definitions where practical; keep justified template/inline definitions in interfaces or appropriate partitions. Use the real standard-library module, never a fabricated stdmodule shim. Includes are limited to necessary SDK, third-party and non-module boundaries, not an alternate owned-core header architecture. Use the newest compatible installed compiler/SDK mode. Missing C++26, named-module or standard-library-module support is a blocker, not permission to downgrade or force a large toolchain installation.

## owner.reuse
Strength: required; scope: []
Evaluate actual cross-project reuse at meaningful boundaries; extract a package only when consumers, dependencies and total cost justify it.
Keep identity, license, ABI/schema, ownership and consumer verification explicit. Never manufacture a generic engine just to satisfy reuse.

## R06
Strength: required; scope: ["game"]
所有開源／自製技術與框架用準確正式名稱
每個啟用功能的庫、適配器、依賴閉包、角色和官方來源
Authority: [依賴總表](07_dependency_catalog.md)、共通庫與自製責任
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R07
Strength: invariant; scope: ["game"]
不採用 Godot
不在直接／間接產品方案中悄悄重新引入；實驗許可不取消此排除
Authority: 共通架構〈免費條件與引擎〉
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R08
Strength: default; scope: ["game"]
考慮 Unreal Engine、其他免費框架及可複用組件
比較授權、取得、平台、無畫面、Agent 開發與運行成本；不把 UE 免費起步視為永久零權利金
Authority: 共通架構〈免費條件與引擎〉
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R09
Strength: default; scope: ["game"]
允許不同部分使用不同技術
薄適配、明確所有權、可替換接口；沒有無需求的重複引擎／運行時
Authority: 共通架構〈模組與接口〉、依賴總表
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R13
Strength: default; scope: ["game"]
2D、2.5D、3D 共通方案
共享規則、資源、身份、同步與工程層；按模擬維度選物理／導航，表現可不同
Authority: 共通架構〈同一套組裝方案〉
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R14
Strength: reference; scope: ["game"]
易懂、準確、表格化、正式英文名配中文意圖
名稱、用途、成本、責任和限制可直接找到，不用術語掩蓋未實作部分
Authority: [總入口](README_AI.md)、各卷表格與術語章
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R15
Strength: required; scope: ["game"]
整個遊戲固定流水框架
判斷新建／接管→產品與既有基準→固定來源→探針→在線切片→全功能→默認校準／驗收→同產物發布及恢復
Authority: 總入口〈固定流水線〉、[Agent 啟動](09_agent_bootstrap.md)
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R16
Strength: reference; scope: ["game"]
未來新項目及既有項目直接交給 LLM／Agent 使用
固定從 `README_AI.md` 讀起；新建／接管分流、實際產品／基準、兩端角色閱讀與可恢復交接；不依賴原始聊天或舊白皮書
Authority: 總入口、Agent 啟動、[完整重構](14_existing_project_migration.md)、共通完成定義
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R17
Strength: invariant; scope: ["game"]
以網路遊戲為標準，非單機基線
真實准入、權威決策及宣告的時間推進、同步與重連；固定步長和持久業務在玩法需要或原有功能存在時落地，離線是獨立合法模式
Authority: 共通架構〈網絡／時間線／身份〉、[服務端](03_server_whitepaper.md)
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R18
Strength: required; scope: ["game"]
人類只定理念，技術全由 Agent 主導
在既有合法權限內自動執行；不為日常技術選擇反覆問人；外部缺項如實記錄
Authority: 共通架構〈決策權／Agent 自治〉、Agent 啟動
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R19
Strength: required; scope: ["game"]
目錄理念、架構和代碼結構
責任目錄、無環依賴、公共接口、狀態所有者和單一事實來源
Authority: 共通架構〈目錄／模組〉
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R23
Strength: required; scope: ["game"]
企業級設計與可靠性
有界工作、持久承諾、權限、審計、恢復、滾動更新；不靠服務數量判企業級
Authority: 共通架構〈企業級／業務持久化〉、服務端運維
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R28
Strength: required; scope: ["game"]
全部必需軟件免費且 Agent 可取得安裝
工具、素材、字體、權重、codec、運維和間接庫全部檢查；平台身份／硬件條件如實區分
Authority: 共通架構〈免費與依賴〉、依賴總表
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R32
Strength: required; scope: ["game"]
任意功能可拆裝的獨立模組
功能依賴、所有權、限額、狀態及最小宿主；構建選擇、交付、啟停、卸載、熱換／恢復分別聲明，不用功能不做常駐工作
Authority: 共通架構〈功能總帳／熱更新〉
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R35
Strength: reference; scope: ["game"]
同時提供服務端與客戶端兩套白皮書
兩卷各自角色、流程和驗收成立，共同規則只維護一份
Authority: [客戶端](02_client_whitepaper.md)、[服務端](03_server_whitepaper.md)
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R39
Strength: required; scope: ["game"]
所有之前和現在要求同時涵蓋兩端
相同安全／來源／自治／成本底線；按角色實現，不強迫服務端安裝表現庫
Authority: 共通架構〈兩端適用〉、全部專項
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R50
Strength: default; scope: ["game"]
標準允許 Agent 自己定義
在全小寫 snake_case 底線內決定具體名字與其它標準、受控變更與遷移；排版不被冒稱性能技術
Authority: 共通決策權／風格、Agent 啟動
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R51
Strength: required; scope: ["game"]
未來所有工作可準確審查
文檔、實作、構建、運行、性能、發布資格分層；作者不能自填成功或自行降 gates
Authority: 共通 CI／完成定義、交付驗證
Apply current owner instructions first; dated observations and examples are not current technical facts.
