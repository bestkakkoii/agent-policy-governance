# platform
Snapshot: 08cba5b9a39218449c769d90644644cf7f6d11973a96b08f0fdb30d38535d13d

## owner.toolchains
Strength: required; scope: []
Use the latest applicable compatible toolchain already installed. Detect actual IDE, compiler, SDK and runtime capabilities; do not force installation/upgrades of large components.
This overrides older whitepaper wording that could force a new toolchain. Use official latest selectors where supported, otherwise detect. Missing hard capabilities are blockers, not permission to downgrade.

## R12
Strength: required; scope: ["game"]
Windows、macOS、Linux 兼容
指定最新正式系統、架構、運行庫、原生設備與打包後行為；模擬不冒充原生
Authority: 兩端白皮書、平台矩陣
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R34
Strength: conditional; scope: ["game"]
iOS／iPadOS／Android 橫向
真機橫屏、safe area、輸入、記憶壓力、背景／恢復、16 KB 等適用平台要求
Authority: 客戶端手機章、平台矩陣、服務端手機契約
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R36
Strength: required; scope: ["game"]
主流服務部署含 Windows
Windows Server／Linux 原生、Windows 11 開發測試、macOS 可移植性、VM／物理／容器資格分明
Authority: 服務端原生平台章、平台矩陣
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R37
Strength: conditional; scope: ["game"]
Docker 同時支持服務器與客戶端
必需 Linux 鏡像，客戶端無 GPU protocol 與指定圖形容器實測；宿主／來賓／平台摘要區分
Authority: 兩端 Docker 章、平台矩陣
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R69
Strength: required; scope: ["game"]
任意目標的嵌入／獨立／remote 同一能力，兼顧低至高配與共享庫限制
真實主線程、共享 renderer／音頻／網絡、手機 Surface／前後景、Docker 能力、總量／增量／公平性；不承諾未知設備或同進程崩潰隔離
Authority: [平台](17_unified_control_api.md#section-11)、[remote](17_unified_control_api.md#section-13)、平台資格／性能／依賴
Apply current owner instructions first; dated observations and examples are not current technical facts.
