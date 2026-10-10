"""Chapter 12: a hand-written Fusion transition template (.setting) used through AddTransition.

Install first, then restart Resolve (templates are indexed at launch):
    mkdir -p "$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/Transitions"
    cp "templates/Claude Flash Cut.setting" "$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/Transitions/"
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, Frame, append, connect, fresh_timeline, import_media, open_project, render, report

r = connect()
p = open_project(r)
mp = p.GetMediaPool()
A, B = os.path.join(MEDIA, "clip_1.mp4"), os.path.join(MEDIA, "clip_3.mp4")
pool = import_media(mp, [A, B])
results = {}

tl = fresh_timeline(p, "ch12_template")
a = append(mp, tl, pool[A], 0, 60, src_start=60)
append(mp, tl, pool[B], 60, 60, src_start=60)
t = a.AddTransition({"type": "Claude Flash Cut", "category": "fusion", "position": "end", "alignment": "center",
                     "duration": 20})
results["custom template found by name (category fusion)"] = (t is not None, t.GetName() if t else None)
out = render(r, p, tl, "ch12_template")
pa, pb, mid = Frame(out, 0.5), Frame(out, 3.5), Frame(out, 2.0)
results["middle of the transition is flashed to near white"] = (min(mid.mean()) > 220, (pa.mean(), mid.mean(), pb.mean()))
early = Frame(out, 1.75).mean()
results["flash ramps: brighter at the cut than 1/4 of the way in"] = (min(mid.mean()) > min(early), (early, mid.mean()))
report(results)
