# 用 Claude 自動剪 DaVinci Resolve｜Claude × DaVinci Resolve Editing Guide

**中文**：用 Claude Code、Codex 等 AI 代理，透過 Python 腳本 API 控制 DaVinci Resolve Studio 剪片的完整教學——時間軸、轉場、字卡、關鍵影格、變速、Fusion 特效、調色、卡點。每一條都標明是否實測、在哪個版本測的，並附可以直接執行的範例程式。

**English**: A hands-on guide for driving DaVinci Resolve Studio with AI agents (Claude Code, Codex, …) through the Python scripting API — timelines, transitions, titles, keyframes, speed ramps, Fusion effects, color, and beat-synced editing. Every entry states whether it was verified, on which version, with a runnable example. English docs: [docs/en](docs/en/).

> **測試環境 / Tested on**：macOS 27.0.1（Apple Silicon）＋ DaVinci Resolve **Studio 21.1.0.14**。
> **Windows、Linux、免費版都沒有測過。** Windows / Linux / free edition are **not** tested.

## 給 AI 代理 / For AI agents

- Claude Code：載入 [SKILL.md](SKILL.md)。
- Codex 與其他代理：讀 [AGENTS.md](AGENTS.md)。
- 兩份都是精簡規則；細節與證據在各章。

## 目錄

| 章 | 主題 | 狀態（中文） |
|---|---|---|
| [0](docs/zh-TW/00-intro.md) | 前言：怎麼讀、測試環境、來源標示 | 完成 |
| [1](docs/zh-TW/01-setup.md) | 環境準備：Studio、外部腳本、內建 Python、官方 AI 接口、對話框卡死 | 完成 |
| [2](docs/zh-TW/02-first-script.md) | 第一支腳本：匯入、放上時間軸、輸出、照片 5 秒的雷 | 完成 |
| [3](docs/zh-TW/03-three-routes.md) | 讓 Claude 操作 Resolve 的三條路比較 | 完成 |
| [4](docs/zh-TW/04-clips.md) | 時間軸與片段：軌道、縮放位移裁切單位、疊圖模式 | 完成 |
| [5](docs/zh-TW/05-transitions.md) | 轉場：58 種實測可用名稱 | 完成 |
| [6](docs/zh-TW/06-titles.md) | 字卡：Text+、模板、放到指定軌 | 完成 |
| [7](docs/zh-TW/07-keyframes.md) | 推近與關鍵影格：Dynamic Zoom、FCPXML、Fusion | 完成 |
| [8](docs/zh-TW/08-speed.md) | 變速：定速、變速曲線 | 完成 |
| [9](docs/zh-TW/09-roundtrip.md) | 修改已存在的時間軸：匯出改檔再匯入 | 完成 |
| [10](docs/zh-TW/10-fusion-basics.md) | Fusion 特效入門：程式接節點、內建特效代號 | 完成 |
| [11](docs/zh-TW/11-fusion-advanced.md) | Fusion 進階與地雷：Burn Away、Loader 卡死、Lock | 完成 |
| [12](docs/zh-TW/12-templates.md) | 自製轉場／字卡模板（.setting） | 完成 |
| [13](docs/zh-TW/13-color.md) | 調色：CDL、自製 LUT、調色存檔 | 完成 |
| [14](docs/zh-TW/14-dctl.md) | DCTL：自己寫遮罩與選色 | 完成 |
| [15](docs/zh-TW/15-power-windows.md) | Power Window 與限定器 | 完成 |
| [16](docs/zh-TW/16-beat-sync.md) | 卡點：拆音樂、抓鼓點與人聲、對拍、輸出後驗切點 | 完成 |
| [17](docs/zh-TW/17-case-study.md) | 完整案例：照參考影片做照片卡點快剪 | 完成 |
| [18](docs/zh-TW/18-verification.md) | 怎麼驗證做對了、交片前整支檢查 | 完成 |
| [19](docs/zh-TW/19-beyond-limits.md) | 「API 做不到」重測：音量音高、剃刀切段、讀回轉場、字幕與字幕檢查 | 完成 |
| [20](docs/zh-TW/20-intro-generator.md) | 用程式產生片頭（Remotion）再接進 Resolve：隨機產生器、提示詞模板、透明背景疊加 | 完成 |
| [21](docs/zh-TW/21-studio-ai.md) | Studio 版限定功能實測：Super Scale、Speed Warp、人聲分離、Fairlight FX、面部修飾、HDR、3D、窗口追蹤 | 完成 |
| [22](docs/zh-TW/22-jumpcut.md) | 跳剪：自動剪掉說話的停頓、字幕跟著平移 | 完成 |
| [A](docs/zh-TW/A-capability-table.md) | 能做／不能做總表 | 完成 |
| [B](docs/zh-TW/B-pitfalls.md) | 踩雷清單 | 完成 |
| [C](docs/zh-TW/C-references.md) | 參考資源與授權 | 完成 |

## 快速開始

```bash
git clone https://github.com/imeipopo/claude-davinci-resolve-editing.git
cd claude-davinci-resolve-editing/examples
./make_media.sh          # 產生測試素材（需要 ffmpeg）
"/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Applications/ResolvePython" 02_first_timeline.py
```

前提：Resolve Studio 已開啟，且 Preferences > System > General > External scripting using = **Local**。

## 致謝與來源

本教學整合了 [samuelgursky/davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp)（MIT）的大量知識，內容以本教學的話重新整理並標明出處；**需要現成的 MCP 工具請直接使用該專案**。交片檢查、跳剪、字幕檢查的想法整理自 [Hao0321/video-autopilot-kit](https://github.com/Hao0321/video-autopilot-kit)（MIT），程式為本 repo 重寫。授權聲明見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 授權

MIT，見 [LICENSE](LICENSE)。
