"""Chapter 8: constant speed (SetSpeed) and a speed ramp (Fusion TimeStretcher), measured on ramp_src.mp4,
whose frame N shows a white bar at x = 2N (640-px wide source)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, Frame, append, connect, fresh_timeline, import_media, open_project, render, report

r = connect()
p = open_project(r)
mp = p.GetMediaPool()
RAMP = os.path.join(MEDIA, "ramp_src.mp4")
pool = import_media(mp, [RAMP])
results = {}


def src_frame(video, t):
    """Which source frame is on screen at time t: bar x (in 640-px space) / 2."""
    f = Frame(video, t, 640, 360)
    xs = [x for x in range(640) if sum(f.px(x, 180)) > 300]
    return None if not xs else round(sum(xs) / len(xs) / 2)


tl = fresh_timeline(p, "ch08_speed")
a = append(mp, tl, pool[RAMP], 0, 60)                 # 0-2 s, will be set to 200 %
results["SetSpeed 200%"] = (a.SetSpeed({"Percentage": 200.0}), (a.GetStart() - tl.GetStartFrame(), a.GetDuration()))
b = append(mp, tl, pool[RAMP], 90, 90)                # 3-6 s, Fusion ramp
comp = b.AddFusionComp()
mi, mo = comp.FindTool("MediaIn1"), comp.FindTool("MediaOut1")
ts = comp.AddTool("TimeStretcher", -32768, -32768)
ts.ConnectInput("Input", mi)
mo.ConnectInput("Input", ts)
ts.AddModifier("SourceTime", "BezierSpline")
for out_f, src_f in [(0, 0), (30, 60), (90, 90)]:    # 2x for 1 s, then 0.5x for 2 s
    ts.SetInput("SourceTime", src_f, out_f)
results["after SetSpeed: clip length on timeline"] = (True, a.GetDuration())

out = render(r, p, tl, "ch08_speed")
sp = [src_frame(out, t) for t in (0.5, 1.0)]
results["SetSpeed 200%: source advances 2 frames per output frame"] = (
    sp[0] is not None and sp[1] is not None and abs((sp[1] - sp[0]) - 30) <= 2, sp)
rp = {t: src_frame(out, 3 + t) for t in (0.0, 0.5, 1.0, 2.0, 2.9)}
results["TimeStretcher: 0-1 s at 2x (source 0 -> 60)"] = (abs(rp[0.5] - 30) <= 2 and abs(rp[1.0] - 60) <= 2, rp)
results["TimeStretcher: 1-3 s at 0.5x (source 60 -> 90)"] = (abs(rp[2.0] - 75) <= 2 and abs(rp[2.9] - 88) <= 3, rp)
report(results)
