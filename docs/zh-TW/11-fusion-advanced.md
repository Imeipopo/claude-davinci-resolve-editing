# 第 11 章　Fusion 進階與地雷

> 英文版：[docs/en/11-fusion-advanced.md](../en/11-fusion-advanced.md)
> 範例：[examples/10_fusion_effects.py](../../examples/10_fusion_effects.py)（後半）

驗證環境：macOS 27.0.1／Resolve Studio 21.1.0.14／2026-10-10。

### 11.1 Burn Away 燃燒轉場：在 Fusion 裡做

- 結論：Burn Away 不能用 `AddTransition` 加（5.6），但它在 Fusion 裡是一個工具，有 `SourceFrom`、`SourceTo` 兩個輸入和 `Transition`（0～1）進度。做法：上一張放在**上層軌**，在它的 comp 裡讓它「燒成透明」，下層軌的下一張就露出來。
- 驗證：實測通過——燒之前是上層畫面、燒完是下層畫面、中間是燒到一半的混合（差異分別 133／73／64）。
- 做法：

```python
up = append(mp, tl, clip_a, 0, 60, track=2)        # 上層：要燒掉的那張
append(mp, tl, clip_b, 0, 90, track=1)              # 下層：燒完露出的那張
comp = up.AddFusionComp()
mi, mo = comp.FindTool("MediaIn1"), comp.FindTool("MediaOut1")
clear = comp.AddTool("Background", -32768, -32768)  # 全透明背景
for k in ("TopLeftRed", "TopLeftGreen", "TopLeftBlue", "TopLeftAlpha"):
    clear.SetInput(k, 0)
ba = comp.AddTool("ofx.com.blackmagicdesign.resolvefx.BurnAway", -32768, -32768)
ba.ConnectInput("SourceFrom", mi)
ba.ConnectInput("SourceTo", clear)
mo.ConnectInput("Input", ba)
ba.AddModifier("Transition", "BezierSpline")
for frame, v in [(0, 0.0), (30, 0.0), (59, 1.0)]:   # 後半秒開始燒
    ba.SetInput("Transition", v, frame)
```

- 同樣做法適用其他有 `SourceFrom`／`SourceTo` 的 Resolve FX。

![Burn Away 燒掉上一張、露出下一張](../../assets/demo/burn_away.jpg)


### 11.2 Burn Away 的 `SourceTo` 一定要接

- 結論：`SourceTo` 沒接時，`Transition` 一大於 0，**輸出就失敗**。
- 驗證：實測通過（輸出停在 35%，`JobStatus: Failed`）。
- 做法：要燒成透明就接 alpha 為 0 的 Background；要燒成黑色就接黑色不透明的 Background。

### 11.3 輸出失敗時，先看是不是有工具輸入沒接

- 結論：本 repo 遇到的兩次「輸出失敗」都是 Fusion 工具的影像輸入沒接上（11.2；Resolve FX 接錯成 `Input`，10.3）。
- 做法：輸出失敗時，列出每個工具的影像輸入和連接狀態：

```python
for t in comp.GetToolList(False).values():
    for v in t.GetInputList().values():
        if v.GetAttrs()["INPS_DataType"] == "Image":
            print(t.Name, v.GetAttrs()["INPS_ID"], v.GetConnectedOutput())
```

### 11.4 `Lock()`／`Unlock()`

- 結論：在 `comp.Lock()` 與 `comp.Unlock()` 之間改參數值，**改動有出現在輸出**（與不鎖定時結果相同）。
- 驗證：實測通過（SoftGlow Gain 0→3，鎖定中修改與不鎖定修改的輸出差異都是 20.79）。
- 補充：samuelgursky 記錄 `Composition.Lock` 會抑制數值寫入後的重新算圖（未實測其條件）；在本 repo 的測試條件下沒有觀察到這個現象。`Lock()` 的主要用途是擋住新增 Loader 時跳出的開檔視窗（11.5）。

### 11.5 加 Loader 會跳出開檔視窗，卡死整個 Resolve

- 結論：`comp.AddTool("Loader")` 會跳出「Open File」開檔對話框。對話框開著時，Resolve 的所有 API 呼叫都回傳 `None`（1.5），腳本看起來像當掉。
- 驗證：本 repo 實測（2026-10-10）。用 System Events 送 Esc 關掉對話框後恢復。
- 做法：
  - 盡量不要在 comp 裡用 Loader。要用第二張圖，改成把它放在另一軌、用疊圖或 11.1 的上下軌做法。
  - 一定要用時，先 `comp.Lock()` 再 `AddTool("Loader")`，對話框不會跳出；設好 `ld.Clip[1] = path` 後 `comp.Unlock()`。
- 未解決：本 repo 用 Loader 讀 PNG／mp4 當 Burn Away 的 `SourceTo` 時，輸出沒有出現該圖（mp4 甚至輸出失敗），原因未查明。以上面「上下軌」做法取代。

### 11.6 輸出卡住時

- 結論：偶爾輸出會卡在某一格不動（本 repo 遇過一次，卡在含 Digital Glitch 字卡的那一格，同一條時間軸前後幾次都正常）。卡住時：
  - `p.StopRendering()` **沒有用**，`IsRenderingInProgress()` 一直是 `True`。
  - 在 Resolve 視窗按 Esc 可以取消工作（畫面顯示「作業已取消」），但 API 仍回報輸出中。
  - 最後只能結束 Resolve 重開；正常結束會跳出「輸出工作未完成」的確認視窗，按「Cancel Jobs and Quit」後仍未結束，需強制結束。
- 驗證：本 repo 實測（2026-10-10，當時螢幕曾經鎖定，是否相關未確認）。
- 做法：輸出時設逾時（`common.render(..., timeout=300)`），逾時就停下來回報，不要無限等。長時間執行用 `caffeinate`（1.7）。
- 不要：Resolve 被強制結束後跳出的「問題報告」對話框，未經使用者同意不要按「傳送」，按「忽略」。
