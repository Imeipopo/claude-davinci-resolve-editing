"""Chapters 13-14: CDL, generated LUT, LUT path rules, DRX save/apply, DCTL window and qualifier."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, OUT, Frame, append, connect, fresh_timeline, import_media, open_project, render, report

LUT_ROOT = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT"   # macOS master LUT folder
SUB = "claude-tutorial"
HERE = os.path.dirname(os.path.abspath(__file__))


def write_cube(path, size=17):
    """Warm highlights / cool shadows, mild contrast. Pure Python: ResolvePython has no numpy."""
    lines = ['TITLE "warm teal"', f"LUT_3D_SIZE {size}"]
    for bi in range(size):
        for gi in range(size):
            for ri in range(size):
                r_, g_, b_ = ri / (size - 1), gi / (size - 1), bi / (size - 1)
                l = 0.2126 * r_ + 0.7152 * g_ + 0.0722 * b_
                sh, hi = (1 - l) ** 2, l ** 2
                c = [r_ - 0.04 * sh + 0.06 * hi, g_ + 0.01 * sh + 0.02 * hi, b_ + 0.05 * sh - 0.05 * hi]
                lines.append(" ".join(f"{min(1, max(0, 0.5 + (v - 0.5) * 1.08)):.6f}" for v in c))
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


r = connect()
p = open_project(r)
mp = p.GetMediaPool()
GREY, CLIP = os.path.join(MEDIA, "grey.mp4"), os.path.join(MEDIA, "clip_1.mp4")
pool = import_media(mp, [GREY, CLIP])
results = {}

os.makedirs(os.path.join(LUT_ROOT, SUB), exist_ok=True)
write_cube(os.path.join(LUT_ROOT, SUB, "warm_teal.cube"))
outside = os.path.join(OUT, "warm_teal_outside.cube")
os.makedirs(OUT, exist_ok=True)
write_cube(outside)
for name in ("oval_window.dctl", "skin_qualifier.dctl"):
    src = open(os.path.join(HERE, "dctl", name)).read()
    results[f"ValidateDCTL {name}"] = (r.ValidateDCTL(src) is None, r.ValidateDCTL(src))
    with open(os.path.join(LUT_ROOT, SUB, name), "w") as f:
        f.write(src)
p.RefreshLUTList()

tl = fresh_timeline(p, "ch13_color")
segs = [append(mp, tl, pool[CLIP if k in (5, 6) else GREY], k * 30, 30, src_start=60) for k in range(7)]
# 0 plain grey | 1 CDL | 2 LUT relative path | 3 LUT absolute path outside master folder | 4 DCTL oval | 5 plain clip | 6 DCTL skin
results["SetCDL"] = (segs[1].SetCDL({"NodeIndex": "1", "Slope": "1.2 1.0 0.8", "Offset": "0 0 0",
                                     "Power": "1 1 1", "Saturation": "1.0"}), None)
g2, g3, g4, g6 = (segs[i].GetNodeGraph(1) for i in (2, 3, 4, 6))
results["SetLUT relative to master LUT folder"] = (g2.SetLUT(1, f"{SUB}/warm_teal.cube"), g2.GetLUT(1))
results["SetLUT with an absolute path outside the master folder"] = (True, (g3.SetLUT(1, outside), g3.GetLUT(1)))
results["SetLUT a DCTL (oval window)"] = (g4.SetLUT(1, f"{SUB}/oval_window.dctl"), g4.GetLUT(1))
results["SetLUT a DCTL (skin qualifier)"] = (g6.SetLUT(1, f"{SUB}/skin_qualifier.dctl"), g6.GetLUT(1))

out = render(r, p, tl, "ch13_color")
F = [Frame(out, k + 0.5) for k in range(7)]
grey = F[0].mean(600, 300, 1300, 800)
cdl = F[1].mean(600, 300, 1300, 800)
results["CDL slope 1.2/1.0/0.8 warms grey (R up, B down)"] = (cdl[0] > grey[0] + 8 and cdl[2] < grey[2] - 8, (grey, cdl))
lut = F[2].mean(600, 300, 1300, 800)
results["relative-path LUT changes the picture"] = (F[2].diff(F[0]) > 1, (grey, lut))
results["absolute-path LUT outside master folder: effect?"] = (True, F[3].diff(F[0]))
centre, corner = F[4].mean(860, 440, 1060, 640), F[4].mean(0, 0, 200, 200)
results["DCTL oval: centre brighter than corner on flat grey"] = (centre[0] > corner[0] + 30, (centre, corner))
results["DCTL skin qualifier changes a colourful clip"] = (F[6].diff(F[5]) > 2, F[6].diff(F[5]))

# 13.x DRX: grab a still of the CDL clip, export as .drx, apply to another clip
r.OpenPage("color")
tl.SetCurrentTimecode(tl.GetCurrentTimecode())
fps = 30
f = tl.GetStartFrame() + 45
tl.SetCurrentTimecode("%02d:%02d:%02d:%02d" % (f // fps // 3600, f // fps // 60 % 60, f // fps % 60, f % fps))
still = tl.GrabStill()
album = p.GetGallery().GetCurrentStillAlbum()
drx_dir = os.path.join(OUT, "drx")
os.makedirs(drx_dir, exist_ok=True)
for x in os.listdir(drx_dir):
    os.remove(os.path.join(drx_dir, x))
exported = album.ExportStills([still], drx_dir, "cdl", "drx") if still else False
drx = [os.path.join(drx_dir, x) for x in os.listdir(drx_dir) if x.endswith(".drx")]
results["GrabStill + ExportStills -> .drx"] = (bool(drx), (bool(still), exported, drx))
r.OpenPage("edit")
if drx:
    tl2 = fresh_timeline(p, "ch13_drx_apply")
    t = append(mp, tl2, pool[GREY], 0, 30)
    results["ApplyGradeFromDRX"] = (t.GetNodeGraph(1).ApplyGradeFromDRX(drx[0], 0), None)
    o2 = render(r, p, tl2, "ch13_drx_apply")
    m = Frame(o2, 0.5).mean(600, 300, 1300, 800)
    results["DRX grade reproduces the CDL warm shift"] = (abs(m[0] - cdl[0]) < 4 and abs(m[2] - cdl[2]) < 4, (cdl, m))
report(results)
