# Agent Policy Governance

讓 Agent 安裝一次，之後按專案與任務自動取得適用規範，不必反覆要求它閱讀白皮書。

## 給 Agent 一句話

> Clone and install bestkakkoii/agent-policy-governance. Follow README_AI.md, preserve existing settings, verify activation, and use the applicable policies automatically for this and future projects.

Agent 安裝入口：`python install.py`。Bootstrap 會選擇已安裝、符合要求的最新 Python；不下載大型工具鏈、不要求安裝套件、不強制常駐服務。需要已安裝 Python 3.13 或更新版本。預設接入 Codex、Claude Code、OpenCode；Orca 透過實際使用的底層 CLI 接入。其他環境可使用 `--project` 的通用 AGENTS.md 入口，不能冒稱有未驗證的原生 Hook。

**v0.2.1 是可安裝的預發行版，不是所有平台皆已端到端認證的正式版。** Codex 原生 Hook 信任、Claude 工作區信任及新工作階段重新載入，仍遵守各平台自己的程序；安裝器不繞過。`doctor` 區分已配置、設定損壞與尚未驗證的原生執行。

## 本次規範補充

C++ 專案強制 C++26 或更新可用標準（包含實驗性模式）、真正的 `import std;`、`export module`／`import`／`export` 與合理的模組介面／實作分離。最新技術、演算法與新概念，只要有可靠來源與符合任務的理論優勢即可優先採用，不必等待成熟或先取得實測勝出；理論效果不得冒充已驗證成果。仍遵守現有大型工具鏈限制及必要的正確性／安全驗證。詳見 [規範修訂與證據契約](docs/policy_amendments.md)。

## 已實作

| 能力 | 行為 |
| --- | --- |
| 99 條規範 | 28 條擁有者共通工程規範，加上白皮書 R01–R71；遊戲規範只套用真正遊戲專案 |
| 持久規範 | SQLite 交易、不可變內容雜湊快照、各專案版本鎖定、並行任務安全邊界切換 |
| Context | 按任務提供實際規則文字、差異回傳、壓縮後恢復；不把 ID 當作規則內容 |
| 原生接入 | Codex／Claude Hook、OpenCode Plugin、通用專案入口；保留既有設定，可重裝和移除 |
| 有界檢查 | 直接寫檔（含 Codex `apply_patch` 工具、argv 與 heredoc 形式）只檢查本次新建路徑的命名，既有目錄不要求改名；JSON／Python 內容只阻擋本次造成的錯誤，無法驗證時明確告知；不假裝能攔截任意 shell 副作用 |
| 自主演進 | 證據提案、不同 Agent 的審查紀錄、風險分級、CAS 發布、已接受版本的回復提案 |
| 更新 | 每日首次工作階段檢查固定 GitHub 倉庫，鎖定實際 commit；新規範先存候選，獨立審查後才啟用 |
| 混合執行 | 預設無常駐程序；已有本機服務時自動重用，故障留診斷並改用相同嵌入核心 |
| ChatGPT | 可打包私人 Skills 預覽；正式 MCP Registry、公開套件建置器及審查案例已提供 |

不保證模型永不產生幻覺、不宣稱所有操作強制受控、不保證固定 Token 節省百分比。原生完整 Hook 信任與實際模型行為，必須在真實主機上驗證。完整白皮書不是公開套件的一部分；`import-source` 將原文驗證後留在本機。

## ChatGPT 網站

`python tools/package.py` 產生私人 Skills 預覽 ZIP。正式公開版使用不同識別名稱，需先部署真實 HTTPS MCP 端點，再以 `--mcp-url` 產生包含 MCP 的套件。GitHub Release **不等於** ChatGPT 官方目錄上架。開發者帳號驗證、網域權限、審查影片與 OpenAI 審核無法由本倉庫假冒完成；詳見 [發布契約](docs/publication.md)。

## 驗證與移除

```sh
python -W error -m unittest discover -s tests -v
node --test tests/registry.test.mjs tests/opencode.test.mjs
python tools/verify.py
python tools/package.py
python apg.py doctor
python apg.py uninstall
```

不要讓使用者手動維護這些命令；由安裝／維護 Agent 執行並解讀。解除安裝只移除受管理的接入設定，保留使用者資料、證據及快照。更多契約見 [README_AI.md](README_AI.md)、[架構與驗收](docs/architecture.md)、[安全與隱私](docs/security.md)。
