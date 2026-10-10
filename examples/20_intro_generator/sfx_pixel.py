import json, sys, wave
import numpy as np

SR = 48000
DUR = 6.0
rng = np.random.default_rng(7)
out = np.zeros(int(SR * DUR))

def place(sig, t):
    i = int(round(t * SR))
    n = min(len(sig), len(out) - i)
    out[i:i + n] += sig[:n]

def env(n, a=0.002, d=0.1):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)

def square(f, n):
    ph = np.cumsum(np.broadcast_to(f, n) / SR)
    return np.sign(np.sin(2 * np.pi * ph))

def tri(f, n):
    ph = np.cumsum(np.broadcast_to(f, n) / SR) % 1
    return 4 * np.abs(ph - 0.5) - 1

# charge riser 1.5 -> 2.5
n = int(SR * 1.0)
tt = np.arange(n) / SR
f = 220 * 2 ** (tt * 2.2) * (1 + 0.03 * np.sin(2 * np.pi * 14 * tt))
place(square(f, n) * (0.05 + 0.25 * tt) * np.minimum(1, (1 - tt) / 0.02), 1.5)
# cast whoosh 2.6
n = int(SR * 0.35)
noise = rng.standard_normal(n)
kern = np.ones(8) / 8
place(np.convolve(noise, kern, 'same') * env(n, 0.03, 0.12) * 0.5, 2.6)
# impact 2.95
n = int(SR * 0.5)
tt = np.arange(n) / SR
place(tri(90 * np.exp(-tt * 4), n) * env(n, 0.001, 0.18) * 0.9 + rng.standard_normal(n) * env(n, 0.001, 0.05) * 0.5, 2.95)
# char landing blips
for i in range(5):
    land = 2.95 + i * 0.12 + 0.24
    n = int(SR * 0.09)
    place(square(660 * 2 ** (i * 3 / 12), n) * env(n, 0.001, 0.04) * 0.35, land)
# lock chime on the bar (4.0)
for k, semis in enumerate([0, 4, 7, 12]):
    n = int(SR * 1.2)
    place(tri(523.25 * 2 ** (semis / 12), n) * env(n, 0.002, 0.35) * 0.3, 4.0 + k * 0.06)
fade = int(SR * 0.3)
out[-fade:] *= np.linspace(1, 0, fade)
out /= np.max(np.abs(out)) * 1.05
pcm = (out * 32767).astype(np.int16)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
