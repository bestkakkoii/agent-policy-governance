# control_api
Snapshot: 6575834e2f9560f90defb39cad9e2e2e0dd013a1ce73c2d7af47378826e6e33a

## R29
Strength: required; scope: ["game"]
0 畫面、純封包、脫機極低佔用
protocol 無表現初始化；offline 無外網；必要權威碰撞／姿勢／規則仍成立
Authority: 客戶端〈單一客戶端與多模式〉
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R30
Strength: invariant; scope: ["game"]
客戶端永遠一體，不編成兩個應用
同平台／架構／版本應用摘要相同；適用 OCI platform digest 相同；模式只改運行配置
Authority: 客戶端模式章、平台矩陣
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R62
Strength: invariant; scope: ["game"]
全部合法功能操作及數據讀寫，共用同一 API 供手動 UI、操控端、嵌入、腳本、本機及 remote 使用
功能帳／操作目錄／唯一處理器／全部入口對照；無漏掉的 UI 或腳本專用能力；內部所有者不被迫逐字段 RPC
Authority: [統一 API](17_unified_control_api.md#section-03)、共通架構、兩端、信任與防禦
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R63
Strength: invariant; scope: ["game"]
一個進程／EXE 內多個完整客戶端 class，獨立或作 lib／SDK 嵌入
真實同 PID 的多 `client_instance`、獨立身份／狀態與共享有界服務；專用 headers／模組／ABI、嵌入宿主生命週期及同一核心證據
Authority: [實例責任](17_unified_control_api.md#section-02)、[SDK](17_unified_control_api.md#section-12)、客戶端與平台
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R64
Strength: invariant; scope: ["game"]
所有公開操作具線程安全入口，可同步／異步使用
並發准入／觀察、單一狀態所有者、buffer／回調／銷毀生命期、同步死鎖拒絕、取消／排空及有界過載證據
Authority: [並發契約](17_unified_control_api.md#section-07)、共通線程／所有權
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R65
Strength: invariant; scope: ["game"]
狀態成功／失敗準確，失敗原因與定位適合 Agent 協作
准入／本地／權威／持久里程碑分開，穩定操作 ID、效果與結構化錯誤；超時未知不假稱失敗，原始原因與私有診斷可追查
Authority: [操作結果](17_unified_control_api.md#section-05)、[重試取消](17_unified_control_api.md#section-06)、網絡與服務端
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R66
Strength: conditional; scope: ["game"]
各實例腳本自由、安全操作其他已授權實例
顯式目標／世代、範圍授權、異步跨實例調度、循環／配額、逐目標結果與取消；無可變 current_client 路由或假跨實例原子性
Authority: [跨實例腳本](17_unified_control_api.md#section-09)、信任與 Agent 契約
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R67
Strength: required; scope: ["game"]
每個實例隨時請求純封包與有畫面切換，窗口如獨立桌面客戶端般操作
同一實例保住會話／世界；獨立窗口路由、首窗口關閉、最後視圖排空、失敗恢復；純封包與離線兩維度不混淆
Authority: [即時切換](17_unified_control_api.md#section-10)、客戶端、平台與更新
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R68
Strength: invariant; scope: ["game"]
全部 API 納入專用 README_AI.md 與 docs，方便未來 Agent 完整使用
同一描述來源生成或機械核對型別／綁定／wire／目錄／文檔；SDK 入口、完整正常／失敗例、產物身份及缺漏檢查
Authority: [文檔與協作](17_unified_control_api.md#section-15)、Agent 啟動、構建與 CI
Apply current owner instructions first; dated observations and examples are not current technical facts.

## R70
Strength: invariant; scope: ["game"]
全文無衝突，新項目與既有項目完整無損重構都採同一控制架構
原全部入口／合法功能／資料映射、可變單例退出、逐功能等價與完整符合證據；視圖／實例／進程／安裝更新作用域一致，不以白皮書冒稱任意源碼已無損重構
Authority: [落地](17_unified_control_api.md#section-16)、[驗收](17_unified_control_api.md#section-17)、完整重構及更新
Apply current owner instructions first; dated observations and examples are not current technical facts.
