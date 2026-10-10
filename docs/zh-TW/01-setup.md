# 第 1 章　環境準備

> 英文版：[docs/en/01-setup.md](../en/01-setup.md)

### 1.1 外部程式控制要用 Studio 版

- 結論：從終端機（Resolve 外面）用程式控制 Resolve，要 DaVinci Resolve **Studio**。免費版只能在 Resolve 裡面的「工作區 > 腳本」選單或主控台執行腳本。
- 驗證：官方文件（Developer/Scripting/README.md）＋整理自 samuelgursky，未實測（本 repo 只有 Studio）。
- 確認：見 1.4 的連線測試，`scriptapp("Resolve")` 回傳 `None` 就是連不上。

> 人類補充：samuelgursky 的工具另外做了一個「免費版也能用」的橋接方式，需要的話看他的 README「Free edition」一節。

### 1.2 打開外部腳本權限

- 結論：Studio 預設不允許外部程式連線，要在 **Preferences > System > General > External scripting using** 設成 **Local**。
- 驗證：官方文件。本 repo 的測試環境就是設成 Local（沒有測其他設定值）。
- 不要：設成 Network，除非你真的要讓區網其他電腦控制 Resolve（安全風險）。

### 1.3 用 Resolve 內建的 Python（21.1 起）

- 結論：Resolve 21.1 內建 Python 3.14，`import DaVinciResolveScript` 直接可用，**不用設任何環境變數**。
- 驗證：官方文件＋本 repo 實測通過｜macOS 27.0.1／Resolve Studio 21.1.0.14／Python 3.14.4｜2026-10-10。
- 做法：

| 系統 | 路徑 | 狀態 |
|---|---|---|
| macOS | `/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Applications/ResolvePython` | 實測通過 |
| Windows | `C:\Program Files\Blackmagic Design\DaVinci Resolve\ResolvePython\ResolvePython.exe` | 官方文件，未實測 |
| Linux | `/opt/resolve/bin/ResolvePython` | 官方文件，未實測 |

- 不要：
  - 用 `pip` 幫它裝套件，官方寫明不支援。需要 numpy、librosa、PIL 時，另開一個 venv 跑分析，把結果存成 JSON，再讓 ResolvePython 的腳本讀 JSON。兩邊分開。
  - 以為它會把腳本所在資料夾加進 `sys.path`。**實測不會**，`from common import ...` 會 `ModuleNotFoundError`。在腳本開頭自己加：

```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```

### 1.4 連線測試

- 結論：Resolve 要先開著、完全載入完成；`scriptapp` 回傳 `None` 代表沒開、還在啟動，或 1.2 沒設。
- 驗證：本 repo 實測通過｜macOS 27.0.1／Resolve Studio 21.1.0.14｜2026-10-10。剛啟動 Resolve 的前約 10 秒會回傳 `None`。
- 做法：

```python
import DaVinciResolveScript as dvr
r = dvr.scriptapp("Resolve")
print(r.GetProductName(), r.GetVersionString())   # DaVinci Resolve Studio 21.1.0.14
```

- 確認：等 Resolve 啟動時用迴圈每 5 秒試一次，拿到版本字串才往下做。

### 1.5 API 回傳 `None`：先分清楚是「正在輸出」還是「被對話框卡住」

- 結論：Resolve 在兩種情況下，`GetCurrentPage()`、`OpenPage()`、`SaveProject()`、`LoadProject()`、`SetCurrentRenderFormatAndCodec()` 等都會回傳 `None`／失敗，而且不報錯：
  1. **正在輸出影片**（包括你的腳本已經結束、但 Resolve 還在跑的輸出工作）。
  2. **跳出了對話框**（例如開檔視窗）。
- 驗證：本 repo 實測｜macOS 27.0.1／Resolve Studio 21.1.0.14｜2026-10-10。兩種都遇過：Fusion 加 Loader 觸發開檔視窗（11.5）；以及螢幕鎖定時輸出變得極慢（1.7），期間所有呼叫都回傳 `None`。samuelgursky 也記錄了同類情況（免費版呼叫 Studio 功能會跳視窗擋住後續呼叫，未實測）。
- 做法：先查是不是在輸出，再查對話框。

```python
p = r.GetProjectManager().GetCurrentProject()
if p.IsRenderingInProgress():
    ...   # 等它跑完（或 p.StopRendering()）
```

  不是在輸出，就查視窗名稱（macOS）：

```bash
osascript -e 'tell application "System Events" to tell process "Resolve" to get name of every window'
```

  多出主視窗以外的名稱（例如 `Open File`），送 Esc 關掉（等於按「取消」）：

```bash
osascript -e 'tell application "System Events" to tell process "Resolve"
set frontmost to true
key code 53
end tell'
```

- 不要：送 Return。不知道對話框內容時按 Return 可能選到預設的危險選項。
- 前提：執行指令的程式要有「輔助使用」權限。螢幕鎖定時查不到任何視窗（會回傳空的），要先解鎖。

### 1.6 Resolve 縮到 Dock 也能用 API，但截圖看不到

- 結論：Resolve 視窗縮小時 API 照常運作、照常輸出；但 `screencapture` 截不到它（只會截到桌面）。
- 驗證：本 repo 實測通過｜macOS 27.0.1／Resolve Studio 21.1.0.14｜2026-10-10。
- 做法（要看畫面時）：

```bash
osascript -e 'tell application "System Events" to tell process "Resolve"
set value of attribute "AXMinimized" of window 1 to false
set frontmost to true
end tell'
/usr/sbin/screencapture -x shot.png
```

- 前提：截圖程式要有「螢幕錄製」權限。

> 人類補充：我們一開始看到截圖只有桌布，誤以為是螢幕鎖定，其實是 Resolve 被縮到 Dock。

### 1.7 長時間自動化時，別讓 Mac 鎖定或進螢幕保護

- 結論：螢幕鎖定或螢幕保護期間，含 Fusion 字卡的時間軸輸出會**慢到幾乎停住**（同一支平常十幾秒，鎖定後跑了十幾分鐘只到 78%）。單純影片片段的輸出在鎖定時則正常。
- 驗證：本 repo 實測（2026-10-10，第 6 章字卡模板輸出時遇到）。只觀察到一次，原因推測是鎖定後 GPU／畫面相關工作被系統降速，未進一步確認。
- 做法：跑測試或整批輸出時，用 macOS 內建的 `caffeinate` 讓系統在這段時間保持喚醒，指令結束就恢復：

```bash
caffeinate -dimsu python3 run_all_tests.py
```

- 取捨：這段時間 Mac 不會自動鎖定，旁人可以直接使用電腦。

### 1.8 官方 AI 接口（21.1 內建 MCP）

- 結論：Resolve Studio 21.1 內建 MCP 伺服器，選單 **File > Setup AI Assistants** 會偵測 Claude Desktop、Claude Code、Codex 等並完成設定。它提供的工具就是同一套腳本 API，外加 LUT／DCTL 產生工具。
- 驗證：工具清單讀自本機 `DaVinci Resolve.app/Contents/Resources/DaVinciResolve.mcpb` 的 manifest（實際檔案）；設定流程為官方文件，未實測。
- 工具清單：`launch_resolve`、`get_resolve_status`、`get_whats_new`、`get_scripting_api`、`search_scripting_api`、`run_script`（沙盒，不能碰檔案、網路）、`run_script_unsafe`（完整權限）、`get_scripting_docs`、`list_dctls`、`list_luts`、`update_dctl`、`delete_dctl`、`delete_lut`、`generate_lut`。
- 取捨：能力和直接跑 ResolvePython 一樣。好處是不用自己寫連線程式；壞處是每次執行都經過 AI 客戶端，長流程（建時間軸、輸出、驗證）直接寫 .py 檔比較好重跑。第 3 章比較三種做法。

### 1.9 先查本機文件，再說「做不到」

- 結論：每次改版都會新增 API。說「API 做不到」之前，先查本機三份文件。
- 驗證：本 repo 實測通過——作者曾誤以為不能加轉場，其實 21.1 新增了 `TimelineItem.AddTransition`，就寫在 CHANGELOG。
- 做法：

| 檔案 | 用途 |
|---|---|
| `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/DaVinciResolveScript.pyi` | 所有函式與參數型別（21.1 起是 .pyi，最準） |
| 同資料夾 `CHANGELOG.md` | 每版新增了什麼 |
| 同資料夾 `README.md` | 屬性鍵、路徑、限制 |
| `DaVinci Resolve.app/Contents/Resources/DaVinci Resolve.pdf` | 使用手冊（4300 多頁，可用 `pdftotext` 轉文字後搜尋，例如找轉場、字卡名稱） |

```bash
grep -n "def AddTransition" -A3 "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/DaVinciResolveScript.pyi"
```

### 1.10 社群工具

- [samuelgursky/davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp)：最完整，四百多個工具，包含離線改寫 .drt／.drx 檔、卡節拍、Fusion 模板製作。MIT 授權。本 repo 沒有安裝測試。
- 它的 [docs/reference/api-limitations.md](https://github.com/samuelgursky/davinci-resolve-mcp/blob/main/docs/reference/api-limitations.md) 是目前最完整的「API 做不到什麼」清單，本教學多處引用。

### 1.11 真的需要點畫面時：用 CGEvent 模擬滑鼠

- 結論：少數事情只能在畫面上做（例如畫 Power Window、Magic Mask 點選）。用 AppleScript 的 `System Events ... click at {x, y}`，**Resolve 只會收到游標移動、不會真的按下**（部分按鈕有反應、部分沒有）；改用 CoreGraphics 送真正的滑鼠按下／放開事件才穩定。
- 驗證：本 repo 實測（2026-10-10：調色頁「窗口」面板用 `click at` 點不開，用 CGEvent 一次就開）。
- 做法：[examples/tools/click.swift](../../examples/tools/click.swift)，編譯一次即可：

```bash
swiftc -O examples/tools/click.swift -o /tmp/click
/tmp/click 630 664          # 點一下（螢幕座標，左上為原點）
/tmp/click 630 664 double   # 雙擊
```

- 流程：截圖（1.6）→ 讀圖找座標 → 點 → 再截圖確認。座標以 `screencapture` 的圖為準（本機為 1920×1080，與點座標 1:1；Retina 螢幕要除以縮放倍率）。
- 前提：執行的程式要有「輔助使用」與「螢幕錄製」權限；螢幕不能鎖定（1.7 的 caffeinate）。
- 建議：操作前告訴使用者「這段時間不要動電腦」，並錄影（`ffmpeg -f avfoundation -i "0:none" ...`）讓使用者事後能看到做了什麼。

