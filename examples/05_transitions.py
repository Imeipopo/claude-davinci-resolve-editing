"""Chapter 5: every transition name accepted by TimelineItem.AddTransition, verified in the render."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, OUT, Frame, append, connect, fresh_timeline, import_media, open_project, render, report

SIMPLE = ["Additive Dissolve", "Blur Dissolve", "Cross Dissolve", "Smooth Cut", "Arrow Iris", "Cross Iris",
          "Diamond Iris", "Eye Iris", "Oval Iris", "Pentagon Iris", "Square Iris", "Triangle Iris", "Barn Door",
          "Push", "Slide", "Split", "Box", "Star", "Triangle Left", "Triangle Right", "Band Wipe", "Center Wipe",
          "Clock Wipe", "Edge Wipe", "Radial Wipe", "Spiral Wipe", "Venetian Blind Wipe", "X Wipe", "Heart",
          "Dip To Color Dissolve", "Spin Blur"]
FUSION = ["Brightness Flash", "Camera Shake", "Circles", "Crash Zoom", "Cross Dissolve", "Drop Warp",
          "Fall and Bounce", "Film Strip", "Flip 3D", "Foreground Wipe", "Glitch", "Noise Dissolve", "Paint On",
          "Pan Down", "Pan Left", "Pan Right", "Pan Up", "Rotate", "Rotate 90", "Round and Down", "Slice Push",
          "Slide Down", "Slide Left", "Slide Right", "Slide Up", "Tunnel of Light", "Warp", "Zoom In and Out"]
OFX = ["Burn Away"]
CANDS = [("simple", n) for n in SIMPLE] + [("fusion", n) for n in FUSION] + [("ofx", n) for n in OFX]
SEG = 30   # each clip is 1 s; the transition is centred on the cut between clip k and k+1

r = connect()
p = open_project(r)
mp = p.GetMediaPool()
A, B = (os.path.join(MEDIA, n) for n in ("clip_1.mp4", "clip_3.mp4"))
pool = import_media(mp, [A, B])

tl = fresh_timeline(p, "ch05_transitions")
items = [append(mp, tl, pool[A if k % 2 == 0 else B], k * SEG, SEG, src_start=60) for k in range(len(CANDS) + 1)]
added = {}
for k, (cat, name) in enumerate(CANDS):
    t = items[k].AddTransition({"type": name, "category": cat, "position": "end", "alignment": "center",
                                "duration": 12})
    added[(cat, name)] = t.GetName() if t else None

results = {}
t0 = next(t for t in tl.GetItemListInTrack("video", 1) if t.GetType() == "transition")
results["transition item: GetType == 'transition', duration 12"] = (t0.GetDuration() == 12, (t0.GetType(), t0.GetDuration(), t0.GetStart() - tl.GetStartFrame()))
results["transition readback: GetProperty()"] = (True, t0.GetProperty())

out = render(r, p, tl, "ch05_transitions")
fa, fb = Frame(out, 0.3, 480, 270), Frame(out, 1.7, 480, 270)   # pure A and pure B frames
table = []
for k, (cat, name) in enumerate(CANDS):
    if not added[(cat, name)]:
        table.append((cat, name, None, None))
        continue
    mid = Frame(out, (k + 1) * SEG / 30 + 0.02, 480, 270)
    pure = fa if k % 2 == 0 else fb
    nxt = fb if k % 2 == 0 else fa
    table.append((cat, name, added[(cat, name)], (mid.diff(pure), mid.diff(nxt))))

ok_names = [(c, n) for c, n, loc, d in table if loc and min(d) > 2]
bad = [(c, n, loc, d) for c, n, loc, d in table if loc and min(d) <= 2]
missing = [(c, n) for c, n, loc, d in table if not loc]
results["accepted and visibly different from both clips"] = (not bad, f"{len(ok_names)} ok, suspicious: {bad}")
results["names AddTransition rejected"] = (True, missing)
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "ch05_transitions.json"), "w") as f:
    json.dump([{"category": c, "type": n, "localized_name": loc, "diff_vs_clips": d} for c, n, loc, d in table],
              f, ensure_ascii=False, indent=1)
report(results)
