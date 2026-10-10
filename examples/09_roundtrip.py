"""Chapter 9: edit an existing timeline by export -> modify file -> import, and what each format keeps."""
import os
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, OUT, Frame, append, connect, fresh_timeline, import_media, open_project, render, report

r = connect()
p = open_project(r)
mp = p.GetMediaPool()
C = [os.path.join(MEDIA, f"clip_{i}.mp4") for i in (1, 2, 3, 4)]
pool = import_media(mp, C)
results = {}
os.makedirs(OUT, exist_ok=True)


def tl_by_name(name):
    for i in range(1, p.GetTimelineCount() + 1):
        if p.GetTimelineByIndex(i).GetName() == name:
            return p.GetTimelineByIndex(i)


def drop(*names):
    old = [t for t in (tl_by_name(n) for n in names) if t]
    if old:
        mp.DeleteTimelines(old)


# Source timeline: dissolve, CDL, Dynamic Zoom, Fusion glow, each on its own 3-s clip.
drop("ch09_source", "ch09_source import", "ch09_moved", "ch09_fcpxml", "ch09_otio")
src = fresh_timeline(p, "ch09_source")
A = append(mp, src, pool[C[0]], 0, 90, src_start=30)
B = append(mp, src, pool[C[1]], 90, 90, src_start=30)
Cc = append(mp, src, pool[C[2]], 180, 90, src_start=30)
D = append(mp, src, pool[C[3]], 270, 90, src_start=30)
A.AddTransition({"type": "Cross Dissolve", "category": "simple", "position": "end", "alignment": "center", "duration": 20})
B.SetCDL({"NodeIndex": "1", "Slope": "1.2 1.0 0.8", "Offset": "0 0 0", "Power": "1 1 1", "Saturation": "1.4"})
Cc.SetProperties({"DynamicZoomEnabled": True})
comp = D.AddFusionComp()
mi, mo = comp.FindTool("MediaIn1"), comp.FindTool("MediaOut1")
g = comp.AddTool("SoftGlow", -32768, -32768)
g.ConnectInput("Input", mi)
g.SetInput("Gain", 1.5)
mo.ConnectInput("Input", g)
ref = render(r, p, src, "ch09_source")
CHECK = {"plain clip": 1.0, "dissolve": 3.0, "CDL": 4.5, "Dynamic Zoom": 7.0, "Fusion glow": 10.5}


def compare(video, shift=None):
    shift = shift or {}
    return {k: Frame(video, t + shift.get(k, 0), 480, 270).diff(Frame(ref, t, 480, 270)) for k, t in CHECK.items()}


# 9.1 DRT: move the last clip 1 s later and trim it to 2 s, then re-import.
drt = os.path.join(OUT, "ch09_source.drt")
results["Export DRT"] = (src.Export(drt, r.EXPORT_DRT, r.EXPORT_NONE), drt)
work = os.path.join(OUT, "ch09_drt")
shutil.rmtree(work, ignore_errors=True)
with zipfile.ZipFile(drt) as z:
    z.extractall(work)
seq = [os.path.join(work, "SeqContainer", f) for f in os.listdir(os.path.join(work, "SeqContainer"))]
s0 = src.GetStartFrame()
patched = 0
for f in seq:
    x = open(f, encoding="utf-8").read()
    # the 4th clip starts at s0+270 with 90 frames; move to s0+300 and trim to 60
    y = x.replace(f"<Start>{s0 + 270}</Start>\n", f"<Start>{s0 + 300}</Start>\n", 1)
    if y != x:
        i = y.index(f"<Start>{s0 + 300}</Start>")
        y = y[:i] + y[i:].replace("<Duration>90</Duration>", "<Duration>60</Duration>", 1)
        patched += 1
    y = y.replace("<Name>ch09_source</Name>", "<Name>ch09_moved</Name>")
    open(f, "w", encoding="utf-8").write(y)
pj = os.path.join(work, "project.xml")
x = open(pj, encoding="utf-8").read()   # read before opening for write, or the file is truncated first
open(pj, "w", encoding="utf-8").write(x.replace("<ProjectName>ch09_source</ProjectName>",
                                                "<ProjectName>ch09_moved</ProjectName>"))
moved_drt = os.path.join(OUT, "ch09_moved.drt")
if os.path.exists(moved_drt):
    os.remove(moved_drt)
subprocess.run(["zip", "-q", "-r", moved_drt, "."], cwd=work, check=True)
results["DRT: patched one clip"] = (patched == 1, patched)
before = {p.GetTimelineByIndex(i).GetName() for i in range(1, p.GetTimelineCount() + 1)}
t_moved = mp.ImportTimelineFromFile(moved_drt, {"timelineName": "ignored-for-drt"})
if t_moved is None:
    report(results)
    raise SystemExit("DRT import failed (a modal 'import failed' dialog is now blocking Resolve, see docs 1.5)")
results["DRT import: name comes from the file, timelineName ignored"] = (
    t_moved is not None and t_moved.GetName() != "ignored-for-drt", t_moved.GetName() if t_moved else None)
last = [i for i in t_moved.GetItemListInTrack("video", 1) if i.GetType() != "transition"][-1]
results["DRT: last clip moved to 10 s and trimmed to 60 frames"] = (
    last.GetStart() - t_moved.GetStartFrame() == 300 and last.GetDuration() == 60,
    (last.GetStart() - t_moved.GetStartFrame(), last.GetDuration()))
out_m = render(r, p, t_moved, "ch09_moved")
d = compare(out_m, {"Fusion glow": 0.5})   # the glow clip now starts 1 s later; 10.5+0.5 is inside it
results["DRT round trip keeps dissolve, CDL, Dynamic Zoom, Fusion (diff ~0)"] = (
    all(v < 1.0 for k, v in d.items()), d)

# 9.2 FCPXML and OTIO: export and re-import unchanged, see what survives.
fx = os.path.join(OUT, "ch09_source.fcpxml")
shutil.rmtree(fx, ignore_errors=True)
src.Export(fx, r.EXPORT_FCPXML_1_10, r.EXPORT_NONE)
results["FCPXML 1.10 export is a directory (bundle)"] = (os.path.isdir(fx), os.listdir(fx) if os.path.isdir(fx) else None)
inner = os.path.join(fx, "Info.fcpxml") if os.path.isdir(fx) else fx
t_fx = mp.ImportTimelineFromFile(inner, {"timelineName": "ch09_fcpxml", "importSourceClips": False,
                                         "sourceClipsFolders": [mp.GetRootFolder()]})
ot = os.path.join(OUT, "ch09_source.otio")
src.Export(ot, r.EXPORT_OTIO, r.EXPORT_NONE)
t_ot = mp.ImportTimelineFromFile(ot, {"timelineName": "ch09_otio", "importSourceClips": False,
                                      "sourceClipsFolders": [mp.GetRootFolder()]})
for label, t in (("FCPXML", t_fx), ("OTIO", t_ot)):
    if not t:
        results[f"{label} re-import"] = (False, None)
        continue
    o = render(r, p, t, "ch09_" + label.lower())
    results[f"{label} round trip: diff per feature (0 = kept)"] = (True, compare(o))
report(results)
