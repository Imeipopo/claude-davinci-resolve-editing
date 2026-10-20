"""Chapter 21.5: AI Face Refinement (colour page only, not in Fusion) is applied by hand or with CGEvent (docs 1.11).
Setup: 21d_face_check.py --setup renders timeline ch21_face (groom_8625) untouched as the reference. Then on the colour
page drag Resolve FX Beauty > AI Face Refinement onto node 01, press "detect faces", track both ways, then set
Skin Texture > amount 1.0 and Skin Grading > midtones 1.0. This script renders again and checks that only the face
changed. (On an already retouched portrait the smoothing alone is subtle: face PSNR 42.6 dB vs the original.)"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import HERE, append, connect, fresh_timeline, import_media, open_project, render, report

r = connect()
p = open_project(r)
mp = p.GetMediaPool()
SRC = os.path.join(HERE, "media_photos", "groom_8625.mp4")
pool = import_media(mp, [SRC])

if "--setup" in sys.argv:
    tl = fresh_timeline(p, "ch21_face")
    append(mp, tl, pool[SRC], 0, 60)
    render(r, p, tl, "ch21_face_off")
    r.OpenPage("color")
    sys.exit(0)

tl = next(p.GetTimelineByIndex(i) for i in range(1, p.GetTimelineCount() + 1)
          if p.GetTimelineByIndex(i).GetName() == "ch21_face")
on = render(r, p, tl, "ch21_face_refined")
off = os.path.join(os.path.dirname(on), "ch21_face_off.mp4")


def crop_stats(video, t, box):
    """Mean luma of box (x, y, w, h)."""
    x, y, w, h = box
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", video, "-frames:v", "1", "-vf",
                          f"crop={w}:{h}:{x}:{y},format=gray", "-f", "rawvideo", "-"], capture_output=True,
                         check=True).stdout
    return round(sum(raw) / len(raw), 1)


# 1280x1920 portrait fitted into 1920x1080 (x 600-1320). Boxes measured on the rendered frame: cheeks and nose
# under the glasses, and the embroidered collar / sleeve area.
FACE, CLOTHES = (900, 200, 100, 70), (760, 700, 160, 120)
res = {}
for name, box in (("face", FACE), ("clothes", CLOTHES)):
    res[name] = []
    for t in (0.2, 1.8):
        a, b = crop_stats(off, t, box), crop_stats(on, t, box)
        res[name].append({"off": a, "on": b})
results = {
    "Face Refinement brightens the face at start and end of the clip": (
        all(v["on"] > v["off"] + 5 for v in res["face"]), res["face"]),
    "clothes are untouched (mean luma within 1; H.264 noise only)": (
        all(abs(v["on"] - v["off"]) <= 1 for v in res["clothes"]), res["clothes"]),
}
report(results)
