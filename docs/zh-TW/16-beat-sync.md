# 第 16 章　卡點：從音樂找切點

> 英文版：[docs/en/16-beat-sync.md](../en/16-beat-sync.md)
> 範例：[examples/16_beats.py](../../examples/16_beats.py)（在一般 venv 執行，不是 ResolvePython）；輸出後對拍：[examples/tools/cut_check.py](../../examples/tools/cut_check.py)（16.10）

本章分兩種來源：

- **合成測試音軌**（已知每一下的時間）上的自動測試：實測通過｜macOS 27.0.1／librosa 1.0.0／2026-10-10。
- **作者用真實流行歌做 19 支卡點影片的經驗**：標「作者實作經驗」，是真實歌曲上觀察到的現象，沒有做成自動測試（歌曲有版權，不能放進 repo）。

### 16.1 分析在 venv，剪輯在 ResolvePython

- 結論：ResolvePython 不能裝 librosa（1.3），所以分析腳本在一般 venv 跑，輸出 `cuts.json`；Resolve 腳本只讀 JSON。
- 做法：

```bash
python3 -m venv .venv && .venv/bin/pip install librosa soundfile numpy
.venv/bin/python examples/16_beats.py song.wav      # → examples/out/cuts.json
```

### 16.2 不要只用「節拍格線」，要用「真的有聲音的那一下」

- 結論：`librosa.beat.beat_track` 給的是規律的拍子格線，但很多歌的前奏、主歌**根本沒有鼓**，照格線切等於對著空氣切。要用 onset（聲音起點）偵測，抓實際有重音的時間。
- 驗證：作者實作經驗——一首歌前 24.9 秒完全沒有鼓，照節拍格線切的第一版被嫌「卡點不準、只是在放照片」；改抓各分軌的 onset 後才對上。合成測試中，前 3 秒沒有鼓，偵測結果也正確地沒有在 3 秒前出現大鼓。

### 16.3 先拆分軌，再分頻段抓

- 結論：混音後的歌，人聲、合成器、鼓的起點會互相干擾。先用 Demucs 把歌拆成鼓、人聲、貝斯、其他四軌，再對每一軌、在特定頻段抓 onset：
  - 大鼓：鼓軌，≤150 Hz
  - 小鼓：鼓軌，180–5000 Hz
  - 人聲切片：人聲軌
  - 合成器連打：其他軌
- 驗證：作者實作經驗（拆分軌工具：`audio-separator -m htdemucs_ft.yaml`）。頻段抓法在合成音軌上實測通過。
- 做法：

```bash
pip install "audio-separator[cpu]"
audio-separator song.wav -m htdemucs_ft.yaml --output_dir stems
```

### 16.4 頻段內的音量要用該頻段算

- 結論：判斷「這一下夠不夠大聲」時，要用**該頻段的能量**，不能用整首歌的音量。否則一個很響的高頻聲音，會在大鼓頻段也被當成一下大鼓。
- 驗證：實測通過——用整體音量時，2 kHz 的短音被誤判成 5 下大鼓；改用頻段能量後大鼓 10 下全對、0 誤判。
- 做法：見範例 `onsets()`：`band = S[m].sum(axis=0)`，並把 `band` 傳給 `onset_detect(..., backtrack=True, energy=band)`。

### 16.5 偵測時間的誤差

- 結論：`backtrack=True` 時，偵測結果比真實起點**早約 25 毫秒**；不加 backtrack 則**晚約 28 毫秒**。都小於 30fps 的一格（33 毫秒）。
- 驗證：實測通過（合成音軌 10 下大鼓、6 下高音，誤差全部在 30 毫秒內）。
- 做法：換算成格數時用四捨五入（`round(t * 30)`），不要無條件捨去。

### 16.6 速度（BPM）常常被算成一半或兩倍

- 結論：`beat_track` 回報的 BPM 常是實際的一半或兩倍。
- 驗證：合成音軌（120 BPM）回報 117.5，可接受；作者實作經驗：一首歌被判成 172 BPM，實際聽感是 86。
- 做法：BPM 只當參考，切點以 onset 為準；需要 BPM 時用人耳確認是哪一個倍數。

### 16.7 歌詞對字：看人聲軌的音量谷底

- 結論：要讓字卡「跟著唱的字」出現，用人聲分軌的 RMS 音量曲線找字與字之間的谷底，比語音辨識（Whisper）的字級時間準。
- 驗證：作者實作經驗——Whisper 的字級時間整體早 0.8～1 秒，而且在快歌段落完全對不上；看人聲 RMS 的谷底能切出每個字（例如「where／we／both／fell／in／love」分別在 6.08／6.45／6.72／7.15／7.41／7.59 秒）。

### 16.8 人耳最後確認

- 結論：偵測結果只是建議。關鍵的字或重拍，請使用者聽過確認，以人耳為準。
- 驗證：作者實作經驗——自動推估 MOON 這個字在 4.68 秒，使用者聽出 4.68 其實是「the」，MOON 在 5.27 秒。

### 16.9 把切點變成剪輯計畫

- 結論：`cuts.json` 的時間 → 換算格數 → 每一段的「素材、起點、長度、軌道、屬性」寫成 `plan.json`，再由 ResolvePython 的建置腳本照表放片段（第 3.2 節的分工）。
- 做法（換算）：

```python
frames = [round(t * 30) for t in cuts["kick"]]
segments = [{"start": a, "dur": b - a} for a, b in zip(frames, frames[1:])]
```

### 16.10 輸出後對拍：`cut_check.py`

- 結論：計畫裡的切點和輸出影片裡的切點要逐一比。`examples/tools/cut_check.py` 用 ffmpeg 的場景分數（`select='gt(scene,0.3)',showinfo`）抓出影片裡每個硬切的第一格，和計畫比對，容許 ±1 格，列出**漏掉**、**偏早／偏晚**、**計畫外多出來**的切點。漏掉或偏移就 FAIL（exit code 1），多出來的是 WARN。
- 驗證：本 repo 實測通過｜macOS 27.0.1／Resolve Studio 21.1.0.14／ffmpeg 8.1.2／2026-10-23。跑 `16_beats.py` 得到 `cuts.json` 的 10 個大鼓時間，換算成格數（89、104、119…224），在 Resolve 照這些格數交替放四段不同的片段、輸出，再檢查：
  - 照原計畫：10 個切點全部 0 格誤差，PASS。切點的場景分數 0.40～0.60，非切點最高 0.00075，0.3 的門檻兩邊都很遠。
  - 計畫裡一個切點故意晚 2 格：FAIL「早了 2 格」。
  - 計畫少寫一個：WARN「多出 5.467 秒」。
  - 計畫多寫一個不存在的（5.2 秒）：FAIL「漏掉 5.2 秒」，其他 10 個仍判正確。
- 做法：

```bash
python3 examples/tools/cut_check.py out.mp4 examples/out/cuts.json --key kick     # 16_beats.py 的輸出
python3 examples/tools/cut_check.py out.mp4 plan.json                              # 16.9 的 [{"start": 格數, "dur": ...}]
python3 examples/tools/cut_check.py out.mp4 times.json --offset 2.0                # 歌從影片第 2 秒才開始
```

  計畫可以是秒數清單（`--frames` 表示是格數）、`cuts.json`（用 `--key` 選哪一軌）、或 16.9 的分段計畫。秒數一律用 `round(t * fps)` 換格（16.5）。
- 雷：配對要分兩輪——先配 ±1 格內的，剩下的再找 0.5 秒內最近的。只做一輪「找最近的」時，計畫多寫一個切點，就會搶走隔壁的偵測結果，後面 5 個全部被誤判成晚 15 格（實測過）。
- 只抓硬切：溶解轉場的場景分數每格都很低，會被當成「漏掉」。有溶解的段落只看硬切的那幾個，或用 18.2 截格看。
- 選用：`--max-shot "0-30:7,30-180:15,180-:30"` 檢查「每一段最長的鏡頭不超過幾秒」（前 30 秒 7 秒、30 秒到 3 分鐘 15 秒、之後 30 秒）。這組數字是整理自 Hao0321 的**起始值，未驗證**，只會給 WARN；卡點影片通常遠短於此。

> 人類補充：分析算出來的切點、Resolve 時間軸上的切點、輸出檔裡的切點，三個要一致才算卡到拍。這支工具檢查的是最後一個——觀眾真正看到的。
