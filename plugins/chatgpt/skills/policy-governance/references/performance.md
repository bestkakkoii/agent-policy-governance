# performance
Snapshot: 6575834e2f9560f90defb39cad9e2e2e0dd013a1ce73c2d7af47378826e6e33a

## owner.performance
Strength: required; scope: []
Preserve correctness and recoverability, remove useless work, and adopt theoretically better new algorithms or designs when credible reasoning fits the workload; do not require measured superiority before selection.
State assumptions and expected gains separately from observations. Claims of actual latency, throughput or footprint improvement require measurements. Perform risk-relevant correctness/security validation; separate instrumented and release builds. Never trade safety for undefined behavior or unbounded queues.

## R03
Strength: reference; scope: ["game"]
速度與延遲排序、簡介、差異及逐項解釋
相同用途與條件的工作量排序及真實測量；不編造全局最快庫名榜
Authority: 共通架構〈資源格式〉、客戶端／服務端性能章
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R04
Strength: required; scope: ["game"]
不預設獨顯或足夠顯存
核顯／UMA、無 GPU protocol、共享內存及峰值預算的真實證據
Authority: [客戶端](02_client_whitepaper.md)、[平台矩陣](05_platform_qualification.md)
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R05
Strength: required; scope: ["game"]
低配到頂級硬件都考慮
明確最低至高配的能力、默認值、品質底線、持續負載與真實證據；不把高配默認 Ultra 或任意硬件無限容量當保證
Authority: 兩端性能章、平台矩陣、[統一性能政策](15_performance_policy.md)
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R24
Strength: required; scope: ["game"]
運行安全且高效
RAII、生命週期、單一寫入者、限制與可恢復錯誤；不以 UB 或關安全換速度
Authority: 共通架構〈語義／接口／線程〉
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R26
Strength: required; scope: ["game"]
排除網絡條件後的極低本地延遲
分開接收、排隊、權威處理／適用 tick、提交、render、present；p95／p99、負載和時鐘方法可審查
Authority: 兩端性能章
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R27
Strength: required; scope: ["game"]
最好可達畫質與低 CPU／GPU／RAM
保住功能／品質底線及安全，優先有用持續實際效能、穩定節奏與本地延遲，去無益成本，再取可辨品質；記錄 UMA、熱、峰值與取捨
Authority: [統一性能政策](15_performance_policy.md)、客戶端性能、服務端容量
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R60
Strength: required; scope: ["game"]
所有項目低至高配默認追求最高有用效能／FPS、最少無益占用及此前提下最佳畫質／流暢度
固定品質底線、原生／生成／顯示幀分列、有用速率／p95／p99／本地延遲、有限自調、UMA／熱／背景及峰值；相同效果與新舊默認兩線證據，不保證互斥指標絕對同時最優
Authority: [統一性能政策](15_performance_policy.md)、客戶端、服務端、平台與演進
Apply current owner instructions first; dated observations and examples are not current technical facts.
