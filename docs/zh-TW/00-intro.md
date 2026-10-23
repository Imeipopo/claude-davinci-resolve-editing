# 第 0 章　前言：這份教學怎麼讀

> 英文版：[docs/en/00-intro.md](../en/00-intro.md)

## 0.1 這是什麼

用程式（Python）控制 DaVinci Resolve Studio 剪片的完整教學，對象是 **AI 代理（Claude Code、Codex 等）以及要指揮它們的人**。每一條都是「可以直接照做」的格式：結論、做法、怎麼確認做對了。給人看的白話解釋放在每條最後的「人類補充」。

內容來自兩個地方：

1. 本 repo 作者用 Claude Code 剪婚紗照卡點影片時，逐一實測出來的結果。
2. 整理自 [samuelgursky/davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp)（MIT 授權）的文件。這是目前最完整的 Resolve AI 控制工具，**要找現成工具請直接用它**；本教學是把它的知識和我們的實測合在一起、改寫成教學順序。

## 0.2 測試環境（重要）

| 項目 | 版本 |
|---|---|
| 作業系統 | macOS 27.0.1（Apple Silicon） |
| Resolve | DaVinci Resolve **Studio** 21.1.0.14 |
| Python | Resolve 內建的 ResolvePython（Python 3.14.4） |
| 其他 | ffmpeg（產生測試素材與驗證輸出） |

**只在 macOS 測過。Windows、Linux、免費版 Resolve 都沒有測過**，路徑、行為、可用的 API 都可能不同。文中凡是 Windows／Linux 的路徑，都是照抄官方文件，標註「未實測」。

## 0.3 每一條的格式

```
### 章.節  標題（一句話講完結論）
- 結論：哪個 API、會發生什麼
- 驗證：來源｜系統／版本｜日期｜對應的範例程式
- 做法：可以直接跑的程式
- 不要：常見錯誤
- 確認：怎麼檢查做對了
> 人類補充：白話解釋
```

「驗證」欄的來源標示：

| 標示 | 意思 |
|---|---|
| **實測通過** | 本 repo 在上表環境實際跑過，並**輸出影片逐格檢查**（不是只看 API 回傳 True） |
| **實測失敗** | 照做不行，寫出失敗的樣子和替代做法 |
| **整理自 samuelgursky，本 repo 已實測** | 他的說法，我們在 21.1 重測過，結果一致 |
| **整理自 samuelgursky，未實測** | 照錄他的說法與他測的版本，本 repo 沒有重測 |
| **整理自 Hao0321** | 想法或起始門檻來自 [Hao0321/video-autopilot-kit](https://github.com/Hao0321/video-autopilot-kit)（MIT），程式為本 repo 重寫；有沒有實測逐條標明 |
| **官方文件，未實測** | 只出自 Blackmagic 官方文件 |

## 0.4 為什麼「輸出驗證」很重要

Resolve 的 API 很常「回傳成功但其實沒效果」，或「回傳失敗但其實做了」。本教學的原則是：**以輸出的影片為準**。每個範例都會輸出 MP4，再用 ffmpeg 截格、算顏色數值或量位置來判斷。第 18 章整理了這些驗證方法。

## 0.5 範例程式

- `examples/make_media.sh`：產生所有測試素材（測試圖、測試影片、透明片段、測試音），不需要任何個人素材。
- `examples/NN_*.py`：每章對應的範例，用 Resolve 內建的 Python 執行，每一條結論印一行 `PASS`／`FAIL`。
- 範例都在獨立專案 `claude-davinci-tutorial` 裡建立時間軸，不會動到你的其他專案（切換專案前會先存檔，見 2.1）。

```bash
cd examples
./make_media.sh
"/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Applications/ResolvePython" 02_first_timeline.py
```

## 0.6 目錄

見 [README](../../README.md#目錄)。
