# 第 3 章　讓 AI 操作 Resolve 的三條路

> 英文版：[docs/en/03-three-routes.md](../en/03-three-routes.md)

三條路底層都是同一套腳本 API（`DaVinciResolveScript`），能做和不能做的事一樣。差別在「誰負責連線、怎麼重跑、怎麼驗證」。

| | A. 官方 MCP（21.1 內建） | B. 社群 MCP（samuelgursky） | C. AI 直接寫 .py 檔執行 |
|---|---|---|---|
| 安裝 | File > Setup AI Assistants | `npx davinci-resolve-mcp setup` 等，見其 README | 不用裝，用 ResolvePython |
| 能力 | 腳本 API＋產生 LUT／DCTL | 腳本 API 全覆蓋＋離線改寫 .drp／.drt／.drx、卡節拍、Fusion 模板等 | 腳本 API＋你自己寫的任何東西（ffmpeg、numpy、Vision……） |
| 長流程重跑 | 每次經過 AI 客戶端 | 有整合好的工作流程工具 | 腳本存成檔案，改一個數字重跑 |
| 驗證 | 自己另外做 | 部分內建 | 自己寫（本教學的做法） |
| 本 repo 實測 | 只讀了工具清單（1.8） | 未安裝 | 全部範例都是這條 |

### 3.1 建議怎麼選

- 結論：
  - 一次性的小動作（改名、套 LUT、加標記）→ A 或 B 最方便。
  - 要反覆修改的成品（卡點影片、每週固定格式的影片）→ C：把整個流程寫成腳本（素材 → 切點 JSON → 建時間軸 → 輸出 → 截格驗證），改版只改參數。
  - 需要「API 做不到、但改檔案做得到」的事（離線寫遮罩調色存檔、改 .drt）→ B 已經做好，不用自己破解。
- 驗證：經驗建議，非實測結論。本 repo 作者用 C 做了 19 支卡點影片。

### 3.2 C 路線的檔案分工

- 結論：分析和剪輯分開。分析（音樂節拍、人臉位置、顏色）在一般 Python venv 跑，輸出 JSON；ResolvePython 的腳本只讀 JSON、操作 Resolve。
- 理由：ResolvePython 不能 `pip install`（1.3）；分開後，分析結果可以重複使用，剪輯腳本也比較短。
- 做法（本 repo 作者的實際分工）：

```
plan.py      (venv：librosa / numpy)  → plan.json   每個片段：素材、起點、長度、軌道、屬性
build.py     (ResolvePython)          讀 plan.json → 建新時間軸 vN
render.py    (ResolvePython)          輸出 vN → renders/
verify       (ffmpeg / PIL)           截格、量位置、比顏色
```

### 3.3 讓 AI 好好用這份教學

- 結論：把這個 repo 放進專案或技能資料夾。Claude Code 讀 `SKILL.md`，Codex 讀 `AGENTS.md`。兩份都只列「實測通過」的規則，避免 AI 照著未驗證的說法做。
