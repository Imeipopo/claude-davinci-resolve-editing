# 第 2 章　第一支腳本：匯入、放上時間軸、輸出

> 英文版：[docs/en/02-first-script.md](../en/02-first-script.md)
> 範例：[examples/02_first_timeline.py](../../examples/02_first_timeline.py)（9 條全部 PASS）、共用函式 [examples/common.py](../../examples/common.py)

本章所有條目的驗證環境：macOS 27.0.1／Resolve Studio 21.1.0.14／2026-10-10，除非另外註明。

### 2.1 切換專案前先存檔

- 結論：`LoadProject`／`CreateProject` 會切走目前的專案，**沒存的改動會丟掉**。
- 驗證：整理自 samuelgursky（ProjectManager.CreateProject discards an unsaved current project），未實測丟失情境；本 repo 範例一律先存再切。
- 做法：

```python
pm = r.GetProjectManager()
cur = pm.GetCurrentProject()
if cur and cur.GetName() not in (name, "Untitled Project"):
    pm.SaveProject()
p = pm.LoadProject(name) or pm.CreateProject(name)
```

- 確認：`p.GetName() == name`。
- 不要：對 Resolve 剛啟動時自動開的 **`Untitled Project`** 呼叫 `SaveProject()`。它會跳出「保存目前專案」要你輸入名稱的對話框，之後所有 API 呼叫都被擋住（見 1.5）。
- 驗證（不要那條）：本 repo 實測（2026-10-10，重開 Resolve 後第一次執行範例時遇到）。

### 2.2 解析度與影格率要在建時間軸之前設；播放影格率設不了

- 結論：
  - `timelineResolutionWidth`、`timelineResolutionHeight`、`timelineFrameRate` 用 `Project.SetSetting` 設得了，但 **`timelineFrameRate` 在專案已有時間軸後就改不動**（回傳 `False`）。所以開新專案後、建任何時間軸之前先設。
  - **`timelinePlaybackFrameRate` 一律回傳 `False`，讀回來還是 24**，新專案也一樣。它只影響監看播放，不影響輸出：時間軸是 30fps，輸出就是 30fps。
- 驗證：整理自 samuelgursky，本 repo 已實測｜新專案設 25／30 都成功；已有時間軸的專案改 25 回傳 `False`；播放影格率不論新舊專案都回傳 `False`、讀回 24；輸出檔 `ffprobe` 為 30fps。
- 做法：

```python
for k, v in {"timelineResolutionWidth": "1920", "timelineResolutionHeight": "1080",
             "timelineFrameRate": "30"}.items():
    assert p.SetSetting(k, v), k
```

- 不要：拿 `SetSetting` 的回傳值當作「設好了」，一定要 `GetSetting` 讀回來確認。
> 人類補充：播放影格率真的需要改時，到「專案設定 > 主設定」手動改一次；或複製一個已經設好的專案來用。

### 2.3 時間軸從 01:00:00:00 開始，`recordFrame` 是絕對格數

- 結論：新時間軸起點是 `01:00:00:00`，30fps 下等於第 **108000** 格。`AppendToTimeline` 的 `recordFrame` 要填「起點 + 偏移」，不是從 0 算。
- 驗證：本 repo 實測通過（`GetStartFrame() == 108000`；放在偏移 90 的片段 `GetStart() == 108090`）。
- 做法：

```python
s = tl.GetStartFrame()
mp.AppendToTimeline([{"mediaPoolItem": item, "startFrame": 0, "endFrame": 90,
                      "trackIndex": 1, "recordFrame": s + 90, "mediaType": 1}])
```

- 不要：寫 `"recordFrame": 90`，片段會跑到時間軸開頭之前。

### 2.4 `endFrame` 不含，長度＝`endFrame - startFrame`

- 結論：`startFrame=30, endFrame=75` 放上去是 45 格，第 75 格不包含在內。
- 驗證：本 repo 實測通過（要求 90 格與 45 格，`GetDuration()` 回傳 90、45；`GetSourceStartFrame()` 回傳 30）。

### 2.5 `CreateEmptyTimeline` 遇到同名回傳 `None`

- 結論：名稱已存在時不會覆蓋，也不會報錯，只回傳 `None`。
- 驗證：本 repo 實測通過。
- 做法：要重建就先刪舊的（見 `common.fresh_timeline()`）；要保留舊版就用新名字（`v2`、`v3`……）。改版開新時間軸是比較安全的習慣，不會蓋掉使用者手動改過的版本。

### 2.6 靜態圖片放上時間軸，長度一律 150 格（5 秒）

- 結論：用 `AppendToTimeline` 放 PNG／JPG 時，`endFrame` 被忽略，長度固定是 150 格（30fps 下 5 秒，也就是專案的預設靜態圖長度）。
- 驗證：本 repo 實測通過（要求 30 格，實得 150 格）。
- 做法：先用 ffmpeg 把每張圖轉成影片再匯入，長度就能精準控制：

```bash
# 先縮放一次再 loop 單格，比 -loop 1 對大圖快很多
ffmpeg -i photo.jpg -vf "loop=loop=239:size=1:start=0,fps=30,format=yuv420p" \
       -frames:v 240 -c:v libx264 -crf 18 -r 30 photo.mp4
```

- 不要：用 `-loop 1` 讀大張照片再輸出，速度慢很多（作者實測約十倍）。

> 人類補充：卡點影片每張照片只停零點幾秒，所以一定要轉成影片；轉成 8 秒長的影片後，想放幾格就放幾格。

### 2.7 純數字檔名會被當成影像序列

- 結論：`1001.png`、`1002.png` 這種檔名匯入時會被合併成**一個**序列片段（名稱 `[1001-1002].png`），不是兩張圖。相機原檔（例如 `KUM_8606.JPG` 轉檔後變成 `8606.png`）很容易中招。
- 驗證：本 repo 實測通過（匯入兩個檔案，媒體池只多一個片段 `[1001-1002].png`）。
- 做法：檔名加上非數字前綴，例如 `photo_1001.png`；或照 2.6 轉成影片。

### 2.8 聲音放第幾軌：`mediaType: 2`

- 結論：同一個 `AppendToTimeline` 字典加 `"mediaType": 2` 就放到音訊軌，`trackIndex` 指音訊軌編號。
- 驗證：本 repo 實測通過（135 格的音樂放在 A1）。

### 2.9 用程式輸出影片

- 結論：輸出流程是：切到 deliver 頁 → 清掉舊工作 → 設格式 → 設輸出設定 → 加工作 → 開始 → 等待。
- 驗證：本 repo 實測通過（輸出長度 9.58 秒，時間軸 9.5 秒，差異是音訊封裝多出的尾巴）。
- 做法：見 `common.render()`。重點：

```python
r.OpenPage("deliver")
p.DeleteAllRenderJobs()
p.SetCurrentRenderFormatAndCodec("mp4", "H264")
p.SetRenderSettings({"SelectAllFrames": True, "TargetDir": out_dir, "CustomName": name,
                     "FormatWidth": 1920, "FormatHeight": 1080})
job = p.AddRenderJob()
p.StartRendering([job])
while p.IsRenderingInProgress():
    time.sleep(1)
print(p.GetRenderJobStatus(job))   # {'JobStatus': 'Complete', 'CompletionPercentage': 100}
```

- 不要：
  - 只看 `JobStatus`。它是**介面語言的文字**（中文介面可能不是 `Complete`），整理自 samuelgursky，未實測；用 `CompletionPercentage == 100` 判斷比較穩。
  - `CustomName` 給空字串：整份設定會被拒絕（整理自 samuelgursky，未實測）。
- 確認：`SetCurrentRenderFormatAndCodec` 回傳 `None`（不是 `False`）通常代表 Resolve 被對話框卡住，見 1.5。輸出後用 `ffprobe` 量長度。

### 2.10 以輸出檔為準，不要只看 API 回傳值

- 結論：驗證放置結果時，用輸出的 MP4 截格檢查。`ExportCurrentFrameAsStill` 會慢一拍，截到上一個時間點的畫面。
- 驗證：「慢一拍」為作者 2026-10-08 在同版本實測；截格方法本 repo 實測通過。
- 做法：

```bash
ffmpeg -v error -ss 3.5 -i out.mp4 -frames:v 1 frame_3.5.png
```

第 18 章有完整的驗證方法（算顏色、量位置、自製測試影片）。
