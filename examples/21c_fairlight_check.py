"""Chapter 21.4: Fairlight FX have no API, so they are dropped on the clips by hand (or with CGEvent, docs 1.11),
then this script renders each audio track on its own and measures the effect.
Setup: 21c_fairlight_check.py --setup builds timeline ch21_fairlight_fx: A1 voice_noisy.wav, A2 voice_clean.wav.
Then drag Fairlight FX > Noise Reduction (auto speech mode) onto A1 and Fairlight FX > Reverb (default) onto A2."""
import array
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, append, connect, fresh_timeline, import_media, open_project, render, report

r = connect()
p = open_project(r)
mp = p.GetMediaPool()
M = lambda f: os.path.join(MEDIA, f)
GREY, NOISY, CLEAN = M("grey.mp4"), M("voice_noisy.wav"), M("voice_clean.wav")
pool = import_media(mp, [GREY, NOISY, CLEAN])
NAME = "ch21_fairlight_fx"

if "--setup" in sys.argv:
    tl = fresh_timeline(p, NAME)
    append(mp, tl, pool[GREY], 0, 240)
    append(mp, tl, pool[NOISY], 0, 340, media_type=2)
    tl.AddTrack("audio", "stereo")
    append(mp, tl, pool[CLEAN], 0, 340, track=2, media_type=2)
    r.OpenPage("edit")
    sys.exit(0)

tl = next(p.GetTimelineByIndex(i) for i in range(1, p.GetTimelineCount() + 1) if p.GetTimelineByIndex(i).GetName() == NAME)


def pcm(path):
    return array.array("h", subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "48000",
                                            "-f", "s16le", "-"], capture_output=True, check=True).stdout)


def db(x):
    return 20 * math.log10(math.sqrt(sum(v * v for v in x) / max(1, len(x))) / 32768 + 1e-9)


clean = pcm(CLEAN)
win = 4800
levels = [db(clean[i:i + win]) for i in range(0, len(clean) - win, win)]
quiet = [k for k, v in enumerate(levels) if v < -60]
# Reverb tail: the first 0.3 s of each pause (the three 100-ms windows right after speech stops).
starts = [k for k in quiet if k > 0 and levels[k - 1] >= -60]
tails = [k + j for k in starts for j in range(3) if k + j in quiet]


def level(a, ks):
    return round(db([v for k in ks for v in a[k * win:(k + 1) * win]]), 1)


def solo(track):
    for t in (1, 2):
        tl.SetTrackEnable("audio", t, t == track)


results = {}
solo(1)
nr = pcm(render(r, p, tl, "ch21_fairlight_nr"))
solo(2)
rv = pcm(render(r, p, tl, "ch21_fairlight_reverb"))
for t in (1, 2):
    tl.SetTrackEnable("audio", t, True)
noisy = pcm(NOISY)
results["Noise Reduction (A1): noise floor in pauses drops"] = (
    level(nr, quiet) < level(noisy, quiet) - 6, {"before": level(noisy, quiet), "after": level(nr, quiet)})
results["Reverb (A2): pauses right after speech now carry a tail"] = (
    level(rv, tails) > level(clean, tails) + 20, {"dry": level(clean, tails), "reverb": level(rv, tails)})
report(results)
