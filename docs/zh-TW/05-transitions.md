# 第 5 章　轉場

> 英文版：[docs/en/05-transitions.md](../en/05-transitions.md)
> 範例：[examples/05_transitions.py](../../examples/05_transitions.py)（58 種轉場全部輸出驗證）

驗證環境：macOS 27.0.1／Resolve Studio 21.1.0.14（介面語言：簡體中文）／2026-10-10。

### 5.1 用 `AddTransition` 加轉場（21.1 新增）

- 結論：`TimelineItem.AddTransition(options)` 在片段的開頭或結尾加轉場，成功回傳轉場本身（一個 `TimelineItem`），失敗回傳 `None`。
- 驗證：實測通過。
- 做法：

```python
t = clip.AddTransition({
    "type": "Cross Dissolve",   # 名稱，見 5.3／5.4，大小寫要完全一樣
    "category": "simple",       # simple / fusion / ofx / audio
    "position": "end",          # 加在這個片段的 start 或 end
    "alignment": "center",      # left / center / right：相對剪接點的位置
    "duration": 12,             # 格數；不給則自動
})
```

- 確認：`t.GetType() == "transition"`；`t.GetDuration()` 是指定的格數；置中時 `t.GetStart()` 在剪接點前 `duration/2` 格（實測：剪接點 30、長度 12 → 起點 24）。輸出後看剪接點那一格是否跟前後兩段都不同。

### 5.2 片段要有「把手」才能置中

- 結論：置中轉場會用到剪接點前後各 `duration/2` 格的素材。前一段的素材尾端、後一段的素材開頭都要有多出來的長度（把手）。
- 驗證：實測通過（範例中每段都從素材第 60 格開始放 30 格，前後都有把手）。
- 做法：`AppendToTimeline` 時 `startFrame` 不要從 0 開始，結尾也不要用到素材最後一格。

### 5.3 一般轉場（`category: "simple"`）：30 種實測可用

| `type` | 回傳名稱（簡中介面） |
|---|---|
| `Additive Dissolve` | 加亮叠化 |
| `Blur Dissolve` | 模糊叠化 |
| `Cross Dissolve` | 交叉叠化 |
| `Smooth Cut` | 平滑剪接 |
| `Arrow Iris` | 箭头划像 |
| `Cross Iris` | 十字展开 |
| `Diamond Iris` | 菱形展开 |
| `Eye Iris` | 眼形转场 |
| `Oval Iris` | 椭圆展开 |
| `Pentagon Iris` | 五边形划像 |
| `Square Iris` | 方形光圈 |
| `Triangle Iris` | 三角形划像 |
| `Barn Door` | 双侧平推门 |
| `Push` | 推移 |
| `Slide` | 滑动（Slide） |
| `Split` | 分割 |
| `Box` | 四方形 |
| `Star` | 星形 |
| `Triangle Left` | 三角形左侧 |
| `Triangle Right` | 三角形右侧 |
| `Band Wipe` | 栅条划像 |
| `Center Wipe` | 中心划像 |
| `Clock Wipe` | 时钟划像 |
| `Edge Wipe` | 边缘划像 |
| `Radial Wipe` | 径向划像 |
| `Spiral Wipe` | 螺旋划像 |
| `Venetian Blind Wipe` | 百叶窗划像 |
| `X Wipe` | X划像 |
| `Heart` | 心形 |
| `Dip To Color Dissolve` | 浸入颜色叠化 |

### 5.4 Fusion 轉場（`category: "fusion"`）：28 種實測可用

| `type` | 回傳名稱（簡中介面） |
|---|---|
| `Brightness Flash` | Brightness Flash |
| `Camera Shake` | Camera Shake |
| `Circles` | Circles |
| `Crash Zoom` | Crash Zoom |
| `Cross Dissolve` | Cross Dissolve |
| `Drop Warp` | Drop Warp |
| `Fall and Bounce` | Fall and Bounce |
| `Film Strip` | Film Strip |
| `Flip 3D` | Flip 3D |
| `Foreground Wipe` | Foreground Wipe |
| `Glitch` | Glitch |
| `Noise Dissolve` | Noise Dissolve |
| `Paint On` | Paint On |
| `Pan Down` | Pan Down |
| `Pan Left` | Pan Left |
| `Pan Right` | Pan Right |
| `Pan Up` | Pan Up |
| `Rotate` | Rotate |
| `Rotate 90` | Rotate 90 |
| `Round and Down` | Round and Down |
| `Slice Push` | Slice Push |
| `Slide Down` | Slide Down |
| `Slide Left` | Slide Left |
| `Slide Right` | Slide Right |
| `Slide Up` | Slide Up |
| `Tunnel of Light` | Tunnel of Light |
| `Warp` | Warp |
| `Zoom In and Out` | Zoom In and Out |

> 人類補充：快切卡點常用的是 Brightness Flash（閃白）、Crash Zoom（甩鏡放大）、Glitch（故障）、Camera Shake（震動）、Slice Push（切條推）。Glitch 適合很短的幾格。

### 5.5 名稱大小寫要完全一致，手冊上的寫法不一定對

- 結論：`type` 分大小寫。手冊寫「Dip to Color Dissolve」，實際要寫 **`Dip To Color Dissolve`** 才叫得到。
- 驗證：實測通過（`Dip to Color Dissolve` → None；`Dip To Color Dissolve` → 成功）。
- 做法：叫不到時先換大小寫試。回傳的名稱會依介面語言翻譯（上表是簡體中文介面的結果），但**傳入時一律用英文**。

### 5.6 OFX／Resolve FX 轉場叫不到

- 結論：`category: "ofx"` 搭配 `Burn Away`、外掛代號 `ofx.com.blackmagicdesign.resolvefx.BurnAway`、各種大小寫與分類組合，全部回傳 `None`。
- 驗證：實測失敗（試了 10 種分類寫法 × 10 種名稱）。
- 做法：Burn Away 改在 Fusion 裡當工具用，效果相同，見 11.1。

### 5.7 轉場的參數讀不回來

- 結論：轉場建立後，`GetProperty()` 回傳空字典，讀不到種類和參數；也沒有函式修改已建立轉場的參數。
- 驗證：整理自 samuelgursky（21.1 建立可行、讀回不行），本 repo 已實測（`GetProperty()` → `{}`）。
- 做法：要改轉場就重建時間軸；要檢查時間軸上有哪些轉場，用 `GetType() == "transition"` 找出來，再用名稱（`GetName()`）判斷。
