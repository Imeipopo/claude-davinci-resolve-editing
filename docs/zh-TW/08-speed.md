# 第 8 章　變速

> 英文版：[docs/en/08-speed.md](../en/08-speed.md)
> 範例：[examples/08_speed.py](../../examples/08_speed.py)（5 條 PASS）

驗證環境：macOS 27.0.1／Resolve Studio 21.1.0.14／2026-10-10。素材 `ramp_src.mp4`：第 N 格在 x = 2N 畫一條白線，輸出後量白線位置就知道播的是原片第幾格（18.4）。

### 8.1 定速：`SetSpeed`

- 結論：`item.SetSpeed({"Percentage": 200.0})` 改片段速度；`0.0` 是凍結畫面。片段在時間軸上的長度**不變**（還是原本放的格數），只是播得比較快。
- 驗證：實測通過（200% 時每輸出 1 格前進原片 2 格；片段長度仍是 60 格）。
- 其他選項：`PitchCorrection`、`StretchKeyframesToFit`、`RippleTimeline`（見 .pyi 的 `SpeedOptions`，未逐一實測）。
- 補充：samuelgursky 記錄 `SetProperty` 改不了速度、只能從匯入檔建定速（OTIO 的 LinearTimeWarp、EDL 的 M2）；21.1 新增的 `SetSpeed` 已可直接設定速度。

### 8.2 變速曲線：Fusion TimeStretcher

- 結論：API 沒有變速曲線。在片段的 Fusion comp 裡加 **TimeStretcher**，對 `SourceTime`（「現在要顯示原片第幾格」）設關鍵影格，就能做任意的快→慢變速。
- 驗證：實測通過（本 repo 想出的做法）。設定「輸出第 0 格→原片 0、第 30 格→原片 60、第 90 格→原片 90」，實測第 0.5／1.0／2.0／2.9 秒分別播原片第 30／60／75／89 格：前 1 秒準確 2 倍速、後 2 秒準確 0.5 倍速。
- 做法：

```python
comp = item.AddFusionComp()
mi, mo = comp.FindTool("MediaIn1"), comp.FindTool("MediaOut1")
ts = comp.AddTool("TimeStretcher", -32768, -32768)
ts.ConnectInput("Input", mi)
mo.ConnectInput("Input", ts)
ts.AddModifier("SourceTime", "BezierSpline")
for out_frame, src_frame in [(0, 0), (30, 60), (90, 90)]:
    ts.SetInput("SourceTime", src_frame, out_frame)
```

- 要更平滑的曲線：多加幾個點。
- 注意：放到時間軸上的素材長度要夠，`SourceTime` 不能超過片段實際有的來源格數。

> 人類補充：照片轉成的影片每一格都一樣，變速看不出差別；這招給真的會動的影片（實拍、AI 讓照片動起來的片段）用。
