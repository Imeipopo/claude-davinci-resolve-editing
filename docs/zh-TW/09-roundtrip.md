# 第 9 章　修改已經存在的時間軸：匯出、改檔、再匯入

> 英文版：[docs/en/09-roundtrip.md](../en/09-roundtrip.md)
> 範例：[examples/09_roundtrip.py](../../examples/09_roundtrip.py)（8 條 PASS）

驗證環境：macOS 27.0.1／Resolve Studio 21.1.0.14／2026-10-10。

API 不能移動、修剪、切斷已經在時間軸上的片段（4.9）。可行的路：把時間軸匯出成檔案，改檔案，再匯入成一條新時間軸。

### 9.1 用 .drt 來回，什麼都不會掉

- 結論：`.drt` 是 Resolve 自己的時間軸格式。匯出 → 改 → 匯入後，**轉場、CDL 調色、Dynamic Zoom、Fusion 特效全部保留**。
- 驗證：實測通過——來回後的輸出和原本逐格比對，五個檢查點差異都是 0。
- 做法：

```python
tl.Export("/path/x.drt", r.EXPORT_DRT, r.EXPORT_NONE)
```

`.drt` 是 zip 壓縮檔，內容：

```
project.xml                     時間軸名稱 <ProjectName>
MediaPool/Master/MpFolder.xml   媒體池
SeqContainer/<uuid>.xml         時間軸內容：每個片段的 <Start> <Duration> <In> ……
```

片段的欄位是明文，例如：

```xml
<Name>clip_4.mp4</Name>
<Start>108270</Start>      <!-- 時間軸絕對格數（起點 108000） -->
<Duration>90</Duration>
<In>30</In>                <!-- 來源起點 -->
```

改完重新壓縮（**zip 的根目錄要直接是這三樣**，不能多一層資料夾）：

```bash
cd extracted && zip -q -r ../moved.drt .
```

```python
new_tl = mp.ImportTimelineFromFile("/path/moved.drt")
```

- 驗證（移動與修剪）：把最後一段從第 270 格移到第 300 格、長度 90 改 60，匯入後讀回 `(300, 60)`，輸出正確。
- 不要：
  - 用 `open(path, "w").write(open(path).read()...)` 這種寫法改檔。開寫入模式會先把檔案清空，讀到的是空字串——本 repo 就這樣產生了 0 位元組的 `project.xml`，匯入時 Resolve 跳出「導入項目失敗」對話框，之後所有呼叫都被擋住（1.5）。先讀完再寫。
  - 期待 `timelineName` 參數有用：**.drt 匯入會忽略 `timelineName`**，名稱取自檔案裡的 `<ProjectName>`／`<Name>`。要改名就改檔案內容。（整理自 samuelgursky，本 repo 已實測）
- 確認：匯入回傳 `None` 時，Resolve 已經跳出錯誤對話框，先去關掉（1.5）。

> 人類補充：這招讓 AI 可以接手修改「使用者已經手動調過」的時間軸，不用整條重建，也不會弄丟使用者的調整。

### 9.2 FCPXML、OTIO 來回會掉東西

- 結論：用 FCPXML 1.10 或 OTIO 匯出再匯入，**只保留片段本身**：

| 項目 | .drt | FCPXML 1.10 | OTIO |
|---|---|---|---|
| 片段位置、長度 | 保留 | 保留 | 保留 |
| 轉場（Cross Dissolve） | 保留 | **遺失** | **遺失** |
| CDL 調色 | 保留 | **遺失** | **遺失** |
| Dynamic Zoom | 保留 | **遺失** | 保留 |
| Fusion 特效 | 保留 | **遺失** | **遺失** |

- 驗證：實測通過（以輸出差異判斷：差異 0 為保留，14～33 為遺失）。
- 用途：FCPXML／OTIO 適合「從零產生時間軸」（7.2），不適合來回修改。
- 注意：
  - **FCPXML 1.10 匯出的是一個資料夾**（`x.fcpxml/Info.fcpxml`），不是單一檔案。匯入時指向裡面的 `Info.fcpxml`。（整理自 samuelgursky，本 repo 已實測）
  - 匯入 FCPXML／OTIO 時加 `"importSourceClips": False, "sourceClipsFolders": [mp.GetRootFolder()]`，讓它連到媒體池裡已有的素材。samuelgursky 記錄 OTIO 這樣匯入可能整條離線，本 repo 實測在素材已在媒體池時是正常的。

### 9.3 離線直接寫 .drt

- 結論：samuelgursky 的工具可以完全不開 Resolve，直接產生可匯入、可輸出的 .drt（剪接、變速、轉場、淡入淡出、標記……），並整理了相關規則。
- 驗證：整理自 samuelgursky，未實測。詳見其 [Native DRT Authoring](https://github.com/samuelgursky/davinci-resolve-mcp/blob/main/docs/guides/native-drt-authoring.md)，他們的原則是「讀回不可信，以輸出為準」，和本教學一致。
