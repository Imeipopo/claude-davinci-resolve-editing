# 第 13 章　調色：CDL、自製 LUT、調色存檔

> 英文版：[docs/en/13-color.md](../en/13-color.md)
> 範例：[examples/13_color.py](../../examples/13_color.py)（15 條 PASS，含第 14 章 DCTL）

驗證環境：macOS 27.0.1／Resolve Studio 21.1.0.14／2026-10-10。素材：純灰 (128,128,128) 畫面，量平均顏色。

### 13.1 CDL

- 結論：`item.SetCDL({...})` 設定節點的 Slope／Offset／Power／Saturation。值是**字串**，三個數字用空格分開。
- 驗證：實測通過——Slope `1.2 1.0 0.8` 讓灰 (128,128,128) 變 (153,128,102)。
- 做法：

```python
item.SetCDL({"NodeIndex": "1", "Slope": "1.2 1.0 0.8", "Offset": "0 0 0",
             "Power": "1 1 1", "Saturation": "1.0"})
```

- 注意：只能寫不能讀（沒有 `GetCDL`）。（整理自 samuelgursky，本 repo 已實測：.pyi 無對應函式）

### 13.2 用程式產生 LUT

- 結論：`.cube` 是純文字格式，可以自己算。ResolvePython 沒有 numpy，用純 Python 迴圈即可（17³ 點瞬間完成）。
- 驗證：實測通過（範例的暖高光／冷陰影 LUT 套用後畫面改變）。
- 做法：見範例 `write_cube()`。格式：

```
TITLE "warm teal"
LUT_3D_SIZE 17
r g b          ← 共 17×17×17 行，紅色變化最快、藍色最慢
```

- 官方 MCP 也有 `generate_lut` 工具可產生 LUT（1.8）。

### 13.3 `SetLUT` 只認主 LUT 資料夾

- 結論：`item.GetNodeGraph(1).SetLUT(1, path)` 的路徑要寫**相對於主 LUT 資料夾**的路徑；給資料夾外的絕對路徑會回傳 `False`、沒有效果。放新檔後先 `p.RefreshLUTList()`。
- 驗證：整理自 samuelgursky，本 repo 已實測（資料夾外絕對路徑 → `False`，輸出差異 0；資料夾內相對路徑 → 成功）。
- 主 LUT 資料夾：

| 系統 | 路徑 | 狀態 |
|---|---|---|
| macOS | `/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT` | 實測通過 |
| Windows | `%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\LUT` | 整理自 samuelgursky，未實測 |

- 做法：

```python
os.makedirs(f"{LUT_ROOT}/my-luts", exist_ok=True)
# ……寫入 my-luts/look.cube……
p.RefreshLUTList()
item.GetNodeGraph(1).SetLUT(1, "my-luts/look.cube")
```

- 注意：`nodeIndex` 從 1 開始（官方文件：16.2 起改為 1-based）。

### 13.4 調色存檔（.drx）：存一次，套到別的片段

- 結論：把某個片段的調色存成 .drx，再用 `ApplyGradeFromDRX` 套到其他片段。流程：切到調色頁 → 播放頭移到該片段 → `GrabStill()` → `ExportStills([still], 資料夾, 前綴, "drx")` → 對目標片段 `GetNodeGraph(1).ApplyGradeFromDRX(drx路徑, 0)`。
- 驗證：實測通過——CDL 片段存成 .drx 套到純灰片段，得到 (151,128,104)，和原本 (153,128,102) 一致。
- 注意：
  - **`ApplyGradeFromDRX` 的回傳值不可靠**：同一版本兩次測試，一次回傳 `None`、一次回傳 `True`，兩次都實際套用成功。不要用回傳值判斷，要輸出確認。
  - `GrabStill` 抓的是播放頭位置**最上層**的片段；若上層有字卡等片段，會抓到它而不是底下的照片。
  - samuelgursky 記錄 `ExportStills` 需要調色頁的 Gallery 面板是開著的；本 repo 先 `OpenPage("color")` 後匯出成功。
  - .drx 裡的調色資料是二進位（hex 編碼）內容，不能直接手寫；samuelgursky 的工具做了離線寫入（第 15 章）。

```python
r.OpenPage("color")
tl.SetCurrentTimecode(tc_of_the_clip)
still = tl.GrabStill()
album = p.GetGallery().GetCurrentStillAlbum()
album.ExportStills([still], "/path/drx", "look", "drx")    # → look_1.2.1.drx 之類的檔名
target.GetNodeGraph(1).ApplyGradeFromDRX("/path/drx/look_1.2.1.drx", 0)
r.OpenPage("edit")
```

### 13.5 其他調色相關 API（未逐一實測）

- `item.CopyGrades([其他片段])`：複製調色。
- `graph.SetNodeEnabled`、`graph.GetNumNodes`、`graph.ResetAllGrades`。
- `item.ExportLUT(...)`：把片段的調色輸出成 LUT。
- 不能做：新增節點、改一級調色輪的數值（整理自 samuelgursky）。需要時用 LUT、CDL、DRX 或 DCTL（第 14 章）。
