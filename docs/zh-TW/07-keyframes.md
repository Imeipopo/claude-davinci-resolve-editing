# 第 7 章　推近與關鍵影格

> 英文版：[docs/en/07-keyframes.md](../en/07-keyframes.md)
> 範例：[examples/07_keyframes.py](../../examples/07_keyframes.py)（6 條 PASS）

驗證環境：macOS 27.0.1／Resolve Studio 21.1.0.14／2026-10-10。素材：黑底中央 120 px 白方塊（量方塊大小與位置）。

腳本 API **沒有**設定剪輯頁檢查器關鍵影格的函式。要讓縮放、位置隨時間變化，有三條路：

| 做法 | 能控制 | 使用者在哪裡改 | 適用 |
|---|---|---|---|
| A. Dynamic Zoom | 開關、緩動；**不能設方向與幅度** | 檢查器 Dynamic Zoom | 簡單的慢推／慢拉 |
| B. 匯入帶關鍵影格的 FCPXML | 縮放、位置、旋轉任意關鍵影格 | 檢查器（已確認，見 7.2） | 建新時間軸時一次排好 |
| C. Fusion Transform 關鍵影格 | 任何 Fusion 參數 | Fusion 頁 | 已存在的時間軸、複雜動畫 |

### 7.1 Dynamic Zoom：預設是「拉遠」

- 結論：`SetProperties({"DynamicZoomEnabled": True, "DynamicZoomEase": r.DYNAMIC_ZOOM_EASE_OUT})` 會讓畫面在片段期間動態縮放，輸出看得到。**預設方向是由大到小（拉遠）**，API 沒有設定方向或起訖框的屬性。
- 驗證：實測通過（方塊寬度從 148 px 變成 118 px）。
- 緩動常數：`DYNAMIC_ZOOM_EASE_LINEAR`、`_IN`、`_OUT`、`_IN_AND_OUT`。
- 要改成推近：使用者在檢查器的 Dynamic Zoom 按「Swap」；或改用 B、C。

> 人類補充：作者早期記錄「用 API 開 Dynamic Zoom 輸出是靜止的」，這次重測是會動的，舊說法作廢。

### 7.2 匯入帶關鍵影格的 FCPXML

- 結論：用程式寫一份 FCPXML 1.10，片段的 `<adjust-transform>` 裡寫 `scale`、`position`、`rotation` 的 `<keyframeAnimation>`，再用 `MediaPool.ImportTimelineFromFile` 匯入，Resolve 會建出一條動畫正確的新時間軸。
- 驗證：實測通過——縮放 1→2（方塊 120→236 px）；位置 (0,0)→(20,10) 對應往右約 216 px、往上約 108 px。
- 單位：FCPXML 的 `position` **1 單位 ＝ 畫面高度的 1%**（1080p 下 10.8 px），y 正值向上。`scale` 是倍率。關鍵影格的 `time` 用片段的**來源時間**（從 `start` 算起）。
- 做法（片段部分）：

```xml
<asset-clip ref="r2" offset="3600/1s" start="1/1s" duration="3/1s" format="r1" tcFormat="NDF">
  <adjust-transform>
    <param name="scale"><keyframeAnimation>
      <keyframe time="1/1s" value="1 1"/><keyframe time="4/1s" value="2 2"/>
    </keyframeAnimation></param>
  </adjust-transform>
</asset-clip>
```

```python
tl = mp.ImportTimelineFromFile(path, {"timelineName": "kf_v1", "importSourceClips": False,
                                      "sourceClipsFolders": [mp.GetRootFolder()]})
```

- 不要：
  - 期待它幫「已存在的時間軸」加關鍵影格——匯入一定是建新時間軸。
  - 用同一個 `timelineName` 重複匯入；samuelgursky 記錄重複名稱會靜默失效，而且檔案內部的名稱可能蓋過 `timelineName`（未完整實測）。每次用新名字。
- 已確認（2026-10-10 開畫面檢查）：匯入後就是**剪輯頁檢查器的關鍵影格**。選取片段，檢查器「縮放」顯示內插中的值（1→2 途中顯示 1.333），旁邊出現「◀ ◆ ▶」關鍵影格切換鈕，使用者可以直接拖、直接改。
- 素材要先在媒體池裡（`importSourceClips: False` 搭配 `sourceClipsFolders`），否則 Resolve 會再匯入一份。

### 7.3 Fusion Transform 關鍵影格

- 結論：在片段的 Fusion comp 裡加 Transform，對 `Size`（或 `Center`、`Angle`）加 `BezierSpline` 修改器，再在指定格數設值，就是關鍵影格。可以用在已經存在的時間軸上。
- 驗證：實測通過（Size 1→1.5，方塊 118→178 px）。
- 做法：

```python
comp = item.AddFusionComp()
mi, mo = comp.FindTool("MediaIn1"), comp.FindTool("MediaOut1")
tr = comp.AddTool("Transform", -32768, -32768)
tr.ConnectInput("Input", mi)
mo.ConnectInput("Input", tr)
tr.AddModifier("Size", "BezierSpline")
tr.SetInput("Size", 1.0, 0)     # 第 0 格
tr.SetInput("Size", 1.5, 59)    # 第 59 格（comp 的第 0 格 = 片段第一格）
```

- 注意：comp 的時間從片段的第一格算起（0），不是時間軸格數。
- 驗證時別截到片段之後：60 格的片段，最後一格在 59/30 = 1.967 秒，截 1.97 秒會拿不到畫面。
