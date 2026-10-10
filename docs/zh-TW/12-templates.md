# 第 12 章　自製轉場／字卡模板（.setting）

> 英文版：[docs/en/12-templates.md](../en/12-templates.md)
> 範例：[examples/templates/Claude Flash Cut.setting](../../examples/templates/Claude%20Flash%20Cut.setting)、[examples/12_templates.py](../../examples/12_templates.py)（3 條 PASS）

驗證環境：macOS 27.0.1／Resolve Studio 21.1.0.14／2026-10-10。本章的格式知識主要整理自 samuelgursky 的 [.setting 撰寫指南](https://github.com/samuelgursky/davinci-resolve-mcp/tree/main/docs/authoring/setting-files)，本 repo 用自己寫的「閃白轉場」實測。

為什麼要做模板：第 10、11 章的 Fusion 特效，使用者要進 Fusion 頁才能調。做成模板後，它會出現在特效庫，**用 `AddTransition` 叫得到**，使用者也能在剪輯頁的檢查器直接調你開放的參數。

### 12.1 .setting 是什麼

- 結論：一個 Lua table 格式的純文字檔，描述一組 Fusion 節點（通常包在一個 `GroupOperator` 裡），加上對外開放的輸入（`InstanceInput`）與輸出（`InstanceOutput`）。可以手寫。
- 驗證：整理自 samuelgursky，本 repo 已實測（手寫的轉場可用）。

### 12.2 放哪裡、什麼時候生效

- 結論（macOS，使用者層級）：`~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/<類別>/名稱.setting`，類別為 `Transitions`、`Titles`、`Effects`、`Generators`。**類別資料夾不能省略**。
- 生效時機：
  - 新放進去的模板，**重開 Resolve 後**才找得到（啟動時建立索引）。整理自 samuelgursky，本 repo 已實測。
  - 已經被索引的模板，**修改檔案內容後不用重開**，下一次 `AddTransition` 就用新版本。本 repo 實測（2026-10-10）。
- Windows 路徑：`%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Templates\...`（整理自 samuelgursky，未實測）。

### 12.3 用程式叫自製轉場

- 結論：檔名（不含 `.setting`）就是名稱，分類用 `fusion`。
- 驗證：實測通過（`AddTransition({"type": "Claude Flash Cut", "category": "fusion", ...})` 回傳轉場，輸出正確）。

![自製閃白轉場](../../assets/demo/flash_cut.jpg)


### 12.4 轉場的骨架

- 結論：轉場有兩個輸入 `MainInput1`（前一段）與 `MainInput2`（後一段），一個輸出 `MainOutput1`。進度（0→1）不是一個參數，而是用 `LUTLookup`（`Source = Duration`）在轉場期間自動產生，接到 Dissolve 的 `Mix`。
- 驗證：整理自 samuelgursky，本 repo 已實測。
- 最小骨架見 samuelgursky 的 `MCP Test Cross Dissolve.setting`；本 repo 的閃白轉場在它之上加了「白色背景＋Merge，Blend 依三角曲線 0→1→0」。

### 12.5 自訂曲線要把 `Curve` 設成 `Custom`

- 結論：`LUTLookup` 的 `Curve = "Easing"` 時只用 `EaseIn`／`EaseOut`，**接上的 `LUTBezier`（`Lookup`）會被忽略**。要用自己畫的曲線（例如中間最高的三角形），`Curve` 要設 `FuID { "Custom" }`。
- 驗證：實測通過（本 repo 發現）。設 `Easing` 時，閃白從頭到尾線性變亮、最後一格突然切走；改 `Custom` 後變成中間最白（230）、兩端回到原畫面（103／108）。
- 做法（三角曲線）：

```lua
Peak = LUTLookup {
    Inputs = {
        Source = Input { Value = FuID { "Duration" }, },
        Curve  = Input { Value = FuID { "Custom" }, },
        Lookup = Input { SourceOp = "PeakLookup", Source = "Value", },
    },
},
PeakLookup = LUTBezier {
    KeyColorSplines = { [0] = {
        [0]   = { 0, RH = { 0.1667, 0.3333 }, Flags = { Linear = true } },
        [0.5] = { 1, LH = { 0.3333, 0.6667 }, RH = { 0.6667, 0.6667 }, Flags = { Linear = true } },
        [1]   = { 0, LH = { 0.8333, 0.3333 }, Flags = { Linear = true } },
    } },
},
```

### 12.6 開放參數給使用者

- 結論：在 GroupOperator 的 `Inputs` 裡加 `InstanceInput { SourceOp = "節點", Source = "參數", Name = "顯示名稱", Default = ..., MinScale = ..., MaxScale = ... }`，使用者就能在檢查器調。
- 驗證：整理自 samuelgursky，本 repo 已實測（2026-10-10 開畫面確認：點選轉場後，檢查器顯示「效果 - Claude Flash Cut」與 `Flash Strength` 滑桿）。

### 12.7 其他類別

- 字卡（Titles）、特效（Effects）、產生器（Generators）的骨架、縮圖規格、常見錯誤，見 samuelgursky 的 [category-patterns.md](https://github.com/samuelgursky/davinci-resolve-mcp/blob/main/docs/authoring/setting-files/references/category-patterns.md) 與 [gotchas.md](https://github.com/samuelgursky/davinci-resolve-mcp/blob/main/docs/authoring/setting-files/references/gotchas.md)（未實測）。
- 最快的起點：在 Fusion 頁把節點做好 → 選取 → 右鍵 Macro → Create Macro 存檔，再用文字編輯器修改（整理自 samuelgursky）。
