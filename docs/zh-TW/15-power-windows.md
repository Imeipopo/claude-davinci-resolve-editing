# 第 15 章　Power Window 與限定器

> 英文版：[docs/en/15-power-windows.md](../en/15-power-windows.md)

腳本 API 不能建立 Power Window（遮罩）或限定器（選色），也不能新增調色節點。有三條路：

| 做法 | 程式能不能完成 | 能拖、會追蹤 | 狀態 |
|---|---|---|---|
| A. DCTL 自製遮罩／選色（第 14 章） | 可以 | 不能 | 本 repo 實測通過 |
| B. 畫面上做一次，存成 .drx，程式套到其他片段（13.4） | 第一次要人或滑鼠操作 | 可以 | 實測通過 |
| C. 離線直接寫 .drx（samuelgursky） | 可以 | 可以 | 整理自 samuelgursky，未實測 |

### 15.1 做法 B：畫面上做一次，之後程式重複套用

- 結論：在調色頁手動（或用滑鼠自動化）建立含 Power Window／限定器的調色，存成 .drx（13.4 的匯出流程），之後用 `ApplyGradeFromDRX` 套到任何片段。遮罩的位置、形狀會一起套過去；在新片段上需要的話再調。
- 驗證：實測通過（2026-10-10）。片段 A 先用 API 設 CDL（Slope 1.5/1.0/0.5），再用滑鼠在調色頁加一個圓形 Power Window；存成 .drx 後套到片段 B。輸出量測：A、B 的圓內都是 (193,127,63)、角落都是原本的 (128,128,128)，完全一致——遮罩跟著 .drx 一起套過去。
- 做法（滑鼠部分見 1.11）：調色頁 → 點「窗口」面板 → 點「圓形」新增 → 依需要拖曳大小位置 → 回到程式做 13.4 的存檔與套用。

### 15.2 做法 C：離線寫 .drx

- 結論：samuelgursky 的進階伺服器（resolve-advanced，Node.js）能在不開 Resolve 的情況下直接寫 .drx，包含 Power Window、限定器、HSL 曲線等，並以 Resolve 面板讀回校正過。
- 驗證：整理自 samuelgursky，未實測（需要安裝其 Node 程式；本 repo 尚未審閱與安裝）。
- 參考：其 README「Advanced (offline) server」一節與 [color-grade-kernel.md](https://github.com/samuelgursky/davinci-resolve-mcp/blob/main/docs/kernels/color-grade-kernel.md)。

### 15.3 Magic Mask

- 結論：`TimelineItem.CreateMagicMask(mode)` 存在（mode：`F` 往後、`B` 往前、`BI` 雙向），但需要先在畫面上點選物件。
- 驗證：本 repo 呼叫回傳 `False`；samuelgursky 記錄「需要操作者點選」，兩者一致。
- 繞路：用滑鼠自動化完成點選與追蹤，實測可行，見 19.6。
