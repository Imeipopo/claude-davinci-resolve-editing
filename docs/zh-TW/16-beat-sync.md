# 第 16 章　卡點：從音樂找切點

> 英文版：[docs/en/16-beat-sync.md](../en/16-beat-sync.md)
> 範例：[examples/16_beats.py](../../examples/16_beats.py)（在一般 venv 執行，不是 ResolvePython）

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
