"""Chapter 16: find cut points from audio. Runs in a normal venv (NOT ResolvePython):

    python3 -m venv .venv && .venv/bin/pip install librosa soundfile numpy
    .venv/bin/python 16_beats.py [song.wav]

Without an argument it synthesises a test track with known hit times and checks the detector against them.
Output: out/cuts.json  {"kick": [...], "high": [...], "tempo": bpm}
"""
import json
import os
import sys

import librosa
import numpy as np
import soundfile as sf

SR, HOP = 22050, 128
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def synth():
    """8 s: no drums for the first 3 s (like many pop intros), kicks every 0.5 s after, a 2 kHz stab run at 1.0-1.85 s."""
    y = np.zeros(SR * 8)
    t = np.arange(int(0.15 * SR)) / SR
    kick = np.sin(2 * np.pi * 60 * t) * np.exp(-t * 30)
    stab = np.sin(2 * np.pi * 2000 * t[: int(0.06 * SR)]) * np.exp(-t[: int(0.06 * SR)] * 60) * 0.5
    kicks = [3.0 + 0.5 * k for k in range(10)]
    stabs = [round(1.0 + 0.17 * k, 2) for k in range(6)]
    for s in kicks:
        i = int(s * SR); y[i:i + len(kick)] += kick
    for s in stabs:
        i = int(s * SR); y[i:i + len(stab)] += stab
    return y, kicks, stabs


def onsets(y, fmin=None, fmax=None, delta=0.3):
    """Band-limited onset times (s) with a relative loudness 0-1 for each hit."""
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=HOP))
    f = librosa.fft_frequencies(sr=SR, n_fft=1024)
    m = np.ones_like(f, bool)
    if fmin:
        m &= f >= fmin
    if fmax:
        m &= f <= fmax
    env = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S[m]), sr=SR, hop_length=HOP)
    band = S[m].sum(axis=0)   # loudness inside the band, so a loud high stab does not count as a kick
    frames = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP, delta=delta,
                                        backtrack=True, energy=band)
    return [(round(float(librosa.frames_to_time(i, sr=SR, hop_length=HOP)), 3),
             round(float(band[i:i + 20].max() / (band.max() + 1e-9)), 2)) for i in frames]


def match(found, truth, tol=0.03):
    hits = [min(found, key=lambda x: abs(x - t)) for t in truth]
    return all(abs(h - t) <= tol for h, t in zip(hits, truth)) and len(found) == len(truth)


if len(sys.argv) > 1:
    y, _ = librosa.load(sys.argv[1], sr=SR)
    truth = None
else:
    y, kicks, stabs = synth()
    os.makedirs(OUT, exist_ok=True)
    sf.write(os.path.join(OUT, "beats_test.wav"), y, SR)

kick = [t for t, lvl in onsets(y, fmax=150) if lvl > 0.15]
high = [t for t, lvl in onsets(y, fmin=1000) if lvl > 0.05]
tempo = float(np.atleast_1d(librosa.beat.beat_track(y=y, sr=SR)[0])[0])
os.makedirs(OUT, exist_ok=True)
json.dump({"kick": kick, "high": high, "tempo": round(tempo, 1)}, open(os.path.join(OUT, "cuts.json"), "w"))
print("kick", kick)
print("high", high)
print("tempo", round(tempo, 1))
if len(sys.argv) == 1:
    print("PASS" if match(kick, kicks) else "FAIL", "| kicks found within 30 ms, none before 3 s |", len(kick))
    print("PASS" if match(high, stabs) else "FAIL", "| 0.17 s stab run found |", high)
    print("PASS" if abs(tempo - 120) < 3 or abs(tempo - 60) < 2 or abs(tempo - 240) < 5 else "FAIL",
          "| tempo is 120 or an octave of it (beat_track often halves/doubles) |", round(tempo, 1))
