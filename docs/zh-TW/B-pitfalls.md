# 附錄 B　踩雷清單

> 英文版：[docs/en/B-pitfalls.md](../en/B-pitfalls.md)

依「會讓你浪費最多時間」排序。每條附章節。

## 會讓整個 Resolve 卡住的

1. **對話框一跳，所有 API 都回傳 `None`**，不報錯。觸發來源：Fusion 加 Loader（開檔視窗）、匯入壞掉的 .drt（「導入項目失敗」）、對 `Untitled Project` 存檔（要你輸入名稱）。先查 `IsRenderingInProgress()`，再用 System Events 查視窗、按 Esc。（1.5、2.1、9.1、11.5）
2. **正在輸出時，`GetCurrentPage()` 等也回傳 `None`**，看起來跟被對話框卡住一樣。（1.5）
3. **輸出偶爾卡在某一格**，`StopRendering()` 無效，只能重開 Resolve。輸出要設逾時。（11.6）
4. **螢幕鎖定時，含 Fusion 字卡的輸出慢到幾乎停住**。長時間執行用 `caffeinate -dimsu`。（1.7）

## 回傳值騙人的

5. 同一軌重疊放片段：回傳成功，實際沒放上去。（4.8）
6. `ApplyGradeFromDRX`：回傳值時而 `None`、時而 `True`，兩次都實際套用成功。（13.4）
7. Resolve FX 輸入接錯（`Input` 而非 `Source`）、Burn Away 的 `SourceTo` 沒接：設定時都成功，**輸出時才失敗**。（10.3、11.2）
8. `SetSetting("timelinePlaybackFrameRate")` 永遠 `False`；`timelineFrameRate` 在有時間軸後也改不動。（2.2）

## 結果跟你想的不一樣的

9. 照片放上時間軸一律 150 格，`endFrame` 被忽略。（2.6）
10. 純數字檔名被合併成影像序列。（2.7）
11. `recordFrame` 是絕對格數（起點 108000），不是從 0 算。（2.3）
12. 直幅素材的 `Pan` 會乘上「顯示寬度 ÷ 1920」；裁切單位是素材在畫面中的像素、從素材自己的邊算。（4.2、4.4）
13. **字卡插入會把 V1 的片段切開、後面整段往後推**，而且一定在 V1；鎖 V1 就失敗。（6.1）
14. `Slide In` 字卡模板預設沒有文字。（6.2）
15. Dynamic Zoom 預設是拉遠，方向不能用程式設。（7.1）
16. 轉場名稱分大小寫，手冊寫法不一定對（`Dip To Color Dissolve`）。（5.5）
17. Resolve FX 有些預設值等於沒效果（Chromatic Aberration）。（10.5）
18. 模板的 `LUTLookup` 要設 `Curve = Custom`，自訂曲線才會生效。（12.5）
19. `.drt` 匯入忽略 `timelineName`；FCPXML 1.10 匯出是資料夾。（9.1、9.2）
20. FCPXML／OTIO 來回會掉轉場、調色、Fusion，只有 .drt 完整保留。（9.2）
21. 字幕放上時間軸會無視 `recordFrame`、接在最後面；先放字幕再放影片。（19.4）

## 環境

22. ResolvePython 不會把腳本資料夾加入 `sys.path`，也不能 pip。（1.3）
23. `SetLUT` 只認主 LUT 資料夾內的相對路徑。（13.3）
24. 新模板要重開 Resolve 才找得到（修改既有模板則不用）。（12.2）
25. Resolve 縮到 Dock 時截圖看不到它，API 照常可用。（1.6）

## 點畫面時

26. AppleScript 的 `click at` 對 Resolve 常常只有游標移過去、沒有真的按下；用 CGEvent 送滑鼠事件。（1.11）

## 點畫面時（續）

27. AI 音頻助手對純音樂會把音量壓低（-20.4 → -28.8 LUFS），卡點影片別用。（19.13）
28. 選單項目用 AppleScript `click menu item` 就能點，比找座標穩。（19.13）

## 跟人合作的

29. 做法改變（例如從 Resolve 原生改成預先算好整段影片）要主動告訴使用者，否則對方會以為還在用 Resolve 的功能。（17.4）
30. 使用者講效果的用詞很短時，先複述理解再做。（17.5）
31. 說「API 做不到」之前，先查本機 .pyi 與 CHANGELOG。（1.9）
32. 強制結束 Resolve 後的「問題報告」對話框，按「忽略」，不要替使用者傳送。（11.6）
