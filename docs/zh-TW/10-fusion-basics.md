# 第 10 章　Fusion 特效入門：用程式接節點

> 英文版：[docs/en/10-fusion-basics.md](../en/10-fusion-basics.md)
> 範例：[examples/10_fusion_effects.py](../../examples/10_fusion_effects.py)
> Resolve FX 代號清單（本機 21.1 實際列出，100 個）：[docs/resolvefx_ids.txt](../resolvefx_ids.txt)

驗證環境：macOS 27.0.1／Resolve Studio 21.1.0.14／2026-10-10。

腳本 API 沒有「在片段上套用剪輯頁特效」的函式，但可以替片段建立 Fusion comp，在裡面接任何 Fusion 工具，**包括所有 Resolve FX**。這是用程式做特效的主要路線。

### 10.1 Fusion comp 加的特效，輸出看得到

- 結論：`item.AddFusionComp()` 建立 comp 後接好節點，剪輯頁與輸出**都會**反映。
- 驗證：實測通過（11 種工具都讓畫面改變，只接 Transform 不改參數的對照組差異 ≈0）。
- 不要：只把工具加進 comp 卻沒接到 `MediaOut1`。沒接上的工具不會有效果——作者早期記錄「Fusion comp 只有 Fusion 頁看得到、輸出吃不到」，原因多半就是這個，舊說法作廢。

### 10.2 基本接法

```python
comp = item.AddFusionComp()
mi, mo = comp.FindTool("MediaIn1"), comp.FindTool("MediaOut1")
t = comp.AddTool("SoftGlow", -32768, -32768)     # -32768 = 讓 Fusion 自己排位置
t.ConnectInput("Input", mi)
t.SetInput("Gain", 1.0)
mo.ConnectInput("Input", t)
```

- 串多個工具：前一個的輸出接下一個的輸入，最後一個接 `MediaOut1`。
- 讀已有的 comp：`item.GetFusionCompByIndex(1)`；列出工具：`comp.GetToolList(False)`；工具種類：`tool.GetAttrs()["TOOLS_RegID"]`。

### 10.3 Resolve FX 在 Fusion 裡的輸入叫 `Source`

- 結論：Resolve FX（代號 `ofx.com.blackmagicdesign.resolvefx.*`）的影像輸入名稱是 **`Source`**，不是 Fusion 原生工具的 `Input`。接錯的話輸出會**失敗**（`JobStatus: Failed`）。
- 驗證：實測通過——用 `Input` 接 Resolve FX Glow，輸出停在 33% 失敗；改 `Source` 後正常。
- 做法：

```python
t.ConnectInput("Source" if reg_id.startswith("ofx.") else "Input", mi)
```

- 查任何工具的影像輸入名稱：

```python
[v.GetAttrs()["INPS_ID"] for v in t.GetInputList().values() if v.GetAttrs()["INPS_DataType"] == "Image"]
```

### 10.4 列出所有可用的 Resolve FX

- 結論：`r.Fusion().GetRegList(1)` 列出所有已註冊的工具；篩 `resolvefx` 得到 100 個（21.1 Studio）。
- 驗證：實測通過，完整清單見 [resolvefx_ids.txt](../resolvefx_ids.txt)。
- 卡點常用：`Glow`、`Lightray`、`ZoomBlur`、`DirectionalBlur`、`RadialBlur`、`ChromaticAberration`、`CameraShake`、`FilmDamage`、`FilmGrain`、`FilmLook`、`AnalogDamage`、`Vignette`、`HalationPlugin`、`VideoCollage`、`PictureInPicture`。

### 10.5 有些 Resolve FX 預設參數看不出效果

- 結論：部分特效的預設值等於「沒效果」，要自己設參數。
- 驗證：實測通過——`ChromaticAberration` 預設各色 `curvature*` 為 0，畫面不變；設 `curvatureRed=5`、`curvatureBlue=-5` 才出現色散。`FilmGrain` 預設強度很低，縮小檢查時看不出來，設 `Opacity=1`、`GrainStrength=0.6` 並用原尺寸比對才量得到。
- 做法：列出工具的數值參數與目前值：

```python
for v in t.GetInputList().values():
    a = v.GetAttrs()
    if a["INPS_DataType"] == "Number":
        print(a["INPS_ID"], a["INPS_Name"], t.GetInput(a["INPS_ID"]))
```

（`INPS_Name` 會依介面語言顯示；設定時用 `INPS_ID`。）

### 10.6 實測過的工具

| 工具 | RegID | 備註 |
|---|---|---|
| Transform | `Transform` | 不設參數 = 不變（對照組）；關鍵影格見 7.3 |
| Soft Glow | `SoftGlow` | `Gain` |
| Camera Shake | `CameraShake` | `Deviation` |
| Glow | `ofx.com.blackmagicdesign.resolvefx.Glow` | 輸入接 `Source` |
| Light Rays | `ofx.com.blackmagicdesign.resolvefx.Lightray` | |
| Zoom Blur | `ofx.com.blackmagicdesign.resolvefx.ZoomBlur` | |
| Chromatic Aberration | `ofx.com.blackmagicdesign.resolvefx.ChromaticAberration` | 預設無效果，見 10.5 |
| Film Damage | `ofx.com.blackmagicdesign.resolvefx.FilmDamage` | |
| Film Grain | `ofx.com.blackmagicdesign.resolvefx.FilmGrain` | 預設很淡，見 10.5 |
| Vignette | `ofx.com.blackmagicdesign.resolvefx.Vignette` | |
| Directional Blur | `ofx.com.blackmagicdesign.resolvefx.DirectionalBlur` | |
| Camera Shake（Resolve FX） | `ofx.com.blackmagicdesign.resolvefx.CameraShake` | |
| Burn Away | `ofx.com.blackmagicdesign.resolvefx.BurnAway` | 當轉場用，見 11.1 |
| TimeStretcher | `TimeStretcher` | 變速曲線，見 8.2 |
| TextPlus＋Merge | `TextPlus`、`Merge` | 字卡，見 6.4 |

### 10.7 使用者怎麼改

- 結論：這些特效在 Fusion 頁。使用者點片段 → 切到 Fusion 頁 → 選節點，在檢查器調參數。比剪輯頁多一步。
- 取捨：要讓使用者在剪輯頁直接調，可以做成 Fusion 模板（`.setting`），見第 12 章。
