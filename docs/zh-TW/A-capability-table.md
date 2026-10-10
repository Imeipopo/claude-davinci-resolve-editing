# 附錄 A　能做／不能做總表

> 英文版：[docs/en/A-capability-table.md](../en/A-capability-table.md)

macOS 27.0.1／Resolve Studio 21.1.0.14。「實測」＝本 repo 輸出影片驗證過；「sg」＝整理自 samuelgursky 未實測。

## 剪輯

| 想做的事 | 能不能 | 怎麼做 | 章節 | 依據 |
|---|---|---|---|---|
| 建時間軸、放片段到指定軌與格數 | 能 | `AppendToTimeline`（絕對格數、endFrame 不含） | 2 | 實測 |
| 照片放指定長度 | 繞路 | 先轉成影片 | 2.6 | 實測 |
| 加軌道 | 能 | `AddTrack` | 4.1 | 實測 |
| 位移、縮放、旋轉、裁切 | 能 | `SetProperties`（注意單位） | 4 | 實測 |
| 透明度、疊圖模式 | 能 | `Opacity`、`CompositeMode` | 4.5–4.6 | 實測 |
| 移動、修剪、切斷已放好的片段 | 不能（直接） | 匯出 .drt 改檔再匯入；或重建 | 4.9、9.1 | 實測 |
| 轉場（58 種內建＋自製模板） | 能 | `AddTransition` | 5、12 | 實測 |
| OFX／Resolve FX 轉場（Burn Away 等） | 不能（直接） | 改在 Fusion 裡做 | 5.6、11.1 | 實測 |
| 讀已建立轉場的參數 | 不能（直接） | 匯出 .drt 讀回 | 5.7、19.3 | 實測 |
| 字卡（Text+ 與 14 種模板） | 能 | `InsertFusionTitleIntoTimeline` | 6 | 實測 |
| 字卡放在指定軌 | 繞路 | 巢狀時間軸或透明佔位＋Fusion | 6.3–6.4 | 實測 |
| 改字卡文字 | 能 | comp 裡的 TextPlus `StyledText` | 6.2 | 實測 |
| 動態推近 Dynamic Zoom | 能（方向不能設） | `DynamicZoomEnabled`／`Ease` | 7.1 | 實測 |
| 剪輯頁檢查器關鍵影格 | 不能（直接） | 匯入 FCPXML、或 Fusion 關鍵影格 | 7.2–7.3 | 實測 |
| 定速 | 能 | `SetSpeed` | 8.1 | 實測 |
| 變速曲線 | 繞路 | Fusion TimeStretcher | 8.2 | 實測 |
| 淡入淡出 | 能 | `SetFades` | — | 實測（2026-10-10 早期測試） |
| 播放影格率 | 不能 | 專案設定手動改 | 2.2 | 實測＋sg |
| 切斷片段（剃刀） | 繞路 | 改 .drt 複製片段（換新 DbId） | 19.2 | 實測 |
| 讀回轉場種類與長度 | 繞路 | 匯出 .drt 讀 `Sm2TiTransition` | 19.3 | 實測 |
| 字幕（文字與時間） | 繞路 | 匯入 .srt，先放字幕再放影片 | 19.4 | 實測 |
| 字幕燒進畫面 | 能 | `ExportSubtitle`＋`SubtitleFormat: BurnIn` | 19.5 | 實測 |
| 音量、左右聲道、音高 | 能 | `AudioVolume`／`AudioPan`／`AudioPitchSemiTones` | 19.1 | 實測 |
| 聲道對應、單聲道／立體聲 | 能 | `SetSourceAudioChannelMapping`／`SetAudioMapping` | 19.7 | 實測 |
| 插入、覆蓋、取代、適配填滿 | 繞路 | 合併 .drt／`ReplaceClip`／`SetSpeed` | 19.11 | 實測（覆蓋未單獨測） |
| Render in Place | 繞路 | MarkIn/MarkOut 輸出該段再放回 | 19.10 | 實測 |

## 特效

| 想做的事 | 能不能 | 怎麼做 | 章節 | 依據 |
|---|---|---|---|---|
| Fusion 節點特效 | 能 | `AddFusionComp`＋接節點 | 10 | 實測 |
| 100 種 Resolve FX | 能 | 在 Fusion 裡用（輸入叫 `Source`） | 10.3–10.4 | 實測 |
| Fusion 參數關鍵影格 | 能 | `AddModifier(..., "BezierSpline")` | 7.3 | 實測 |
| 剪輯頁特效庫的 Effects 直接套到片段 | 不能 | 改用 Fusion comp | 10 | 實測（API 無此函式） |
| 自製模板讓使用者在剪輯頁調 | 能 | .setting | 12 | 實測 |
| Fusion 裡讀第二張圖（Loader） | 不建議 | 會跳開檔視窗；改用上下軌 | 11.5 | 實測 |

## 調色

| 想做的事 | 能不能 | 怎麼做 | 章節 | 依據 |
|---|---|---|---|---|
| CDL | 能（不能讀回） | `SetCDL` | 13.1 | 實測 |
| 自製 LUT 並套用 | 能 | 寫 .cube、`SetLUT`（只認主 LUT 資料夾） | 13.2–13.3 | 實測 |
| 存調色、套到別的片段 | 能 | `GrabStill`＋`ExportStills`＋`ApplyGradeFromDRX` | 13.4 | 實測 |
| 新增節點、改調色輪數值 | 不能 | LUT／CDL／DRX／DCTL 代替 | 13.5 | sg |
| 遮罩、選色（程式產生） | 繞路 | DCTL | 14 | 實測 |
| 可拖曳、會追蹤的 Power Window | 不能（直接） | 畫面做一次存 .drx 再用程式套用；或 sg 離線寫 .drx | 15 | 實測（做法 B） |
| Magic Mask | 不能（直接） | CGEvent 滑鼠自動點選＋追蹤 | 15.3、19.6 | 實測 |

## 專案與輸出

| 想做的事 | 能不能 | 怎麼做 | 章節 | 依據 |
|---|---|---|---|---|
| 輸出 MP4 | 能 | deliver 設定＋`StartRendering` | 2.9 | 實測 |
| 代理檔 | 繞路 | ffmpeg 自己做＋`LinkProxyMedia` | 19.8 | 實測 |
| 媒體夾改名 | 繞路 | 新資料夾＋`MoveClips`＋`DeleteFolders` | 19.9 | 實測 |
| 智慧媒體夾 | 繞路 | 滑鼠＋keystroke 建立 | 19.12 | 實測 |
| AI 自動混音 | 繞路 | AppleScript 點選單觸發（純音樂效果不佳） | 19.13 | 實測 |
| 停止卡住的輸出 | 不能（`StopRendering` 無效） | 重開 Resolve | 11.6 | 實測 |
| 匯出／匯入時間軸 | 能 | `Export`／`ImportTimelineFromFile` | 9 | 實測 |
| 從音樂抓切點 | Resolve 外做 | librosa＋分軌 | 16 | 實測＋經驗 |
| 點畫面（必要時） | 能 | CGEvent 模擬滑鼠（AppleScript 的 click at 不可靠） | 1.11 | 實測 |
