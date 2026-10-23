# 附錄 C　參考資源與授權

> 英文版：[docs/en/C-references.md](../en/C-references.md)

## 官方

- Resolve 腳本 API 文件（安裝 Resolve 後就在本機）：`/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/`（`DaVinciResolveScript.pyi`、`README.md`、`CHANGELOG.md`、`Examples/`）。
- Resolve 使用手冊（本機）：`/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Resources/DaVinci Resolve.pdf`。
- 官方 MCP（21.1 Studio 內建）：選單 File > Setup AI Assistants；本機檔案 `Contents/Applications/ResolveMCP`、`Contents/Resources/DaVinciResolve.mcpb`。

## 社群

- [samuelgursky/davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp)（MIT）：最完整的 Resolve MCP 工具與文件。本教學引用的版本：commit `94c7a885d53f13be78522ce96561a9e9e21d64c5`（2026-10-09）。特別推薦：
  - [docs/reference/api-limitations.md](https://github.com/samuelgursky/davinci-resolve-mcp/blob/main/docs/reference/api-limitations.md)：API 做不到什麼（99 條）
  - [docs/guides/native-drt-authoring.md](https://github.com/samuelgursky/davinci-resolve-mcp/blob/main/docs/guides/native-drt-authoring.md)：離線寫 .drt
  - [docs/guides/headless-edit-loop.md](https://github.com/samuelgursky/davinci-resolve-mcp/blob/main/docs/guides/headless-edit-loop.md)：各交換格式保留什麼
  - [docs/authoring/setting-files/](https://github.com/samuelgursky/davinci-resolve-mcp/tree/main/docs/authoring/setting-files)：.setting 模板撰寫
- [Hao0321/video-autopilot-kit](https://github.com/Hao0321/video-autopilot-kit)（MIT）：用 ffmpeg 產生與檢查影片的工具組。本教學引用的版本：commit `a50c73bde0c5bcb5b82e4d28f812e780e20cb1a7`。交片檢查（18.7）、切點與鏡頭長度（16.10）、字幕讀速與抽聽（19.15）、跳剪（22）、模糊填底（2.6）的想法與起始門檻整理自它，程式為本 repo 重寫；它文件中引用的第三方網站數據本教學沒有採用。
- 其他相關 repo（未實測）：[lordhoell/davinci-resolve-mcp](https://github.com/lordhoell/davinci-resolve-mcp)、[wassermanproductions/unofficial-davinci-mcp](https://github.com/wassermanproductions/unofficial-davinci-mcp)（含免費版可用的 FCPXML 路線與卡拍工具）、[deetisdale/davinci-resolve-automation](https://github.com/deetisdale/davinci-resolve-automation)（照片卡點）。

## 片頭（第 20 章）

- [Remotion](https://www.remotion.dev/)：用 React 寫畫面、逐格輸出影片。授權見 [remotion.dev/license](https://www.remotion.dev/license)。
- [Skillry：Opus 5.5 影片與提示詞](https://skillry.dev/ai-videos/opus-5-5)、[yihui-dev/awesome-opus5-5-videos](https://github.com/yihui-dev/awesome-opus5-5-videos)：513 支用程式做的影片與作者公開的提示詞。本 repo 的片頭模板參考了其中的寫法；中譯放在 `prompts/third-party/`，版權屬原作者。
- [google/fonts](https://github.com/google/fonts)：產生器用的 SIL OFL 字型來源。

## 本教學與 samuelgursky 的對照

本教學實測後與 samuelgursky 記錄**一致**的：播放影格率設不了（2.2）、同軌重疊先放的贏（4.8）、轉場讀不回（5.7）、字卡無法指定軌與巢狀時間軸做法（6.1、6.3）、.drt 忽略 timelineName（9.1）、FCPXML 1.10 匯出為資料夾（9.2）、SetLUT 只認主資料夾（13.3）、Magic Mask 需點選（15.3）。

本教學實測結果與 samuelgursky 記錄**不同或未重現**的：
- `Composition.Lock` 抑制改動：在本教學條件下改動仍有出現在輸出（11.4）。
- OTIO 以 `importSourceClips: False` 匯入會離線：素材已在媒體池時，本教學匯入正常（9.2）。
- 速度只能從匯入檔建立：21.1 已有 `SetSpeed` 可直接設定（8.1）。
- 沒有 API 能調音量：21.1 有 `AudioVolume`／`AudioPan`／`AudioPitchSemiTones`，實測有效（19.1）。
- 字幕燒入設定在 19.x 無效：21.1 實測有效（19.5）。

本教學**新增**、samuelgursky 未記錄的：Fusion TimeStretcher 變速曲線（8.2）、Burn Away 在 Fusion 中的接法與 `SourceTo` 必接（11.1–11.2）、Resolve FX 輸入叫 `Source`（10.3）、透明佔位＋Fusion 字卡（6.4）、字卡插入會切開並後推 V1（6.1）、FCPXML 匯入關鍵影格與單位（7.2）、58 種轉場名稱與大小寫（5）、直幅 Pan 與裁切單位（4.2、4.4）、`ApplyGradeFromDRX` 回傳值不可靠（13.4）、畫面做的 Power Window 可透過 .drx 套到其他片段（15.1）、FCPXML 匯入的關鍵影格就是檢查器關鍵影格（7.2）、CGEvent 點擊（1.11）、模板曲線要設 Custom（12.5）、螢幕鎖定時 Fusion 輸出變慢（1.7）、DCTL 遮罩與選色（14）、改 .drt 切斷片段（19.2）、從 .drt 讀回轉場含 Fusion 模板名稱（19.3）、匯入 .srt 做字幕與「先放字幕」的雷（19.4）。

## 授權

- 本 repo：MIT（[LICENSE](../../LICENSE)）。
- 引用 samuelgursky/davinci-resolve-mcp 的內容：MIT，版權聲明見 [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)。
- 整理自 Hao0321/video-autopilot-kit 的內容：MIT，版權聲明見 [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)。
- `prompts/third-party/` 的提示詞中譯：版權屬各原作者，不適用本 repo 的 MIT，見 [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)。
- DaVinci Resolve、Fusion 為 Blackmagic Design 的商標；本 repo 與 Blackmagic Design 無關。
