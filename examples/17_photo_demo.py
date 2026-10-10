"""Chapter 17 demo on real photos (assets/photos, the author's own portraits, used with permission):
face-centred fill, Burn Away, a title over a photo, a DCTL spotlight and the custom Flash Cut transition.
Run make_media.sh first (it turns assets/photos/*.jpg into 8-second clips in examples/media_photos)."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, Frame, append, connect, fresh_timeline, import_media, open_project, render, report

HERE = os.path.dirname(os.path.abspath(__file__))
PH_DIR = os.path.join(HERE, "media_photos")
TRANSPARENT = os.path.join(HERE, "media", "transparent_10s.mov")


def faces():
    """Normalised face boxes (x, y, w, h; top-left origin). Measured once with macOS Vision and kept here."""
    return {"groom_8625": (0.378, 0.13, 0.225, 0.15), "groom_8628": (0.452, 0.14, 0.134, 0.089),
            "groom_8630": (0.393, 0.13, 0.266, 0.177), "groom_8832": (0.33, 0.159, 0.28, 0.187),
            "groom_8834": (0.267, 0.486, 0.061, 0.041), "groom_8842": (0.407, 0.149, 0.149, 0.125)}


def fill_on_face(item, name, src_w, src_h, face_y=0.40):
    """Zoom a portrait to fill 1920x1080 and move it so the face sits at face_y of the frame height (docs 4.2-4.4)."""
    fit = min(1920 / src_w, 1080 / src_h)
    fit_w, fit_h = src_w * fit, src_h * fit
    zoom = 1920 / fit_w
    fx, fy, fw, fh = faces()[name]
    cx, cy = fx + fw / 2, fy + fh / 2
    dx = -(cx - 0.5) * fit_w * zoom                   # screen px to move right
    dy = (cy - 0.5) * fit_h * zoom - (face_y - 0.5) * 1080   # screen px to move up
    max_dx, max_dy = (fit_w * zoom - 1920) / 2, (fit_h * zoom - 1080) / 2   # never reveal the frame edge
    dx = max(-max_dx, min(max_dx, dx))
    dy = max(-max_dy, min(max_dy, dy))
    item.SetProperties({"ZoomX": zoom, "ZoomY": zoom, "Pan": dx * 1920 / fit_w, "Tilt": dy})


r = connect()
p = open_project(r)
mp = p.GetMediaPool()
names = sorted(faces())
clips = {n: os.path.join(PH_DIR, n + ".mp4") for n in names}
pool = import_media(mp, list(clips.values()) + [TRANSPARENT])
size = {n: (1280, 1530 if n == "groom_8842" else 1920) for n in names}
results = {}

tl = fresh_timeline(p, "ch17_photo_demo")
tl.AddTrack("video")
tl.AddTrack("video")
t = 0
# 1. fit vs face-centred fill (0-2 s, 2-4 s)
append(mp, tl, pool[clips["groom_8625"]], t, 60)
a = append(mp, tl, pool[clips["groom_8625"]], t + 60, 60)
fill_on_face(a, "groom_8625", *size["groom_8625"])
t += 120
# 2. Burn Away 8630 -> 8832 (4-7 s): upper clip burns away over its last second
low = append(mp, tl, pool[clips["groom_8832"]], t, 90)
fill_on_face(low, "groom_8832", *size["groom_8832"])
up = append(mp, tl, pool[clips["groom_8630"]], t, 60, track=2)
fill_on_face(up, "groom_8630", *size["groom_8630"])
comp = up.AddFusionComp()
mi, mo = comp.FindTool("MediaIn1"), comp.FindTool("MediaOut1")
clear = comp.AddTool("Background", -32768, -32768)
for k in ("TopLeftRed", "TopLeftGreen", "TopLeftBlue", "TopLeftAlpha"):
    clear.SetInput(k, 0)
ba = comp.AddTool("ofx.com.blackmagicdesign.resolvefx.BurnAway", -32768, -32768)
ba.ConnectInput("SourceFrom", mi)
ba.ConnectInput("SourceTo", clear)
mo.ConnectInput("Input", ba)
ba.AddModifier("Transition", "BezierSpline")
for fr, v in [(0, 0.0), (30, 0.0), (59, 1.0)]:
    ba.SetInput("Transition", v, fr)
t += 90
# 3. title over a photo (7-10 s) via a transparent placeholder on V3
bg = append(mp, tl, pool[clips["groom_8842"]], t, 90)
fill_on_face(bg, "groom_8842", *size["groom_8842"], face_y=0.34)
ph = append(mp, tl, pool[TRANSPARENT], t + 15, 75, track=3)
c3 = ph.AddFusionComp()
mi3, mo3 = c3.FindTool("MediaIn1"), c3.FindTool("MediaOut1")
tx = c3.AddTool("TextPlus", -32768, -32768)
tx.SetInput("StyledText", "Claude x DaVinci")
tx.SetInput("Size", 0.11)
tx.SetInput("Center", {1: 0.5, 2: 0.18, 3: 0.0})
mg = c3.AddTool("Merge", -32768, -32768)
mg.ConnectInput("Background", mi3)
mg.ConnectInput("Foreground", tx)
mo3.ConnectInput("Input", mg)
t += 90
# 4. DCTL spotlight (10-13 s): plain first half, spotlight second half
s1 = append(mp, tl, pool[clips["groom_8628"]], t, 45)
s2 = append(mp, tl, pool[clips["groom_8628"]], t + 45, 45)
for s in (s1, s2):
    fill_on_face(s, "groom_8628", *size["groom_8628"], face_y=0.34)
p.RefreshLUTList()
results["DCTL spotlight applied"] = (s2.GetNodeGraph(1).SetLUT(1, "claude-tutorial/oval_window.dctl"), None)
t += 90
# 5. custom Flash Cut transition 8630 -> 8834 (13-17 s)
f1 = append(mp, tl, pool[clips["groom_8630"]], t, 60, src_start=30)
fill_on_face(f1, "groom_8630", *size["groom_8630"])
f2 = append(mp, tl, pool[clips["groom_8834"]], t + 60, 60, src_start=30)
fill_on_face(f2, "groom_8834", *size["groom_8834"], face_y=0.30)
tr = f1.AddTransition({"type": "Claude Flash Cut", "category": "fusion", "position": "end",
                       "alignment": "center", "duration": 20})
results["Flash Cut transition"] = (tr is not None, None)
t += 120

out = render(r, p, tl, "ch17_photo_demo")
os.makedirs(os.path.join(OUT, "demo"), exist_ok=True)
for label, sec in {"1_fit": 1.0, "1_face_fill": 3.0, "2_burn_before": 4.5, "2_burn_mid": 5.5, "2_burn_after": 6.5,
                   "3_title": 8.5, "4_plain": 10.7, "4_spotlight": 12.2, "5_flash_mid": 15.0, "5_after": 16.5}.items():
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(sec), "-i", out, "-frames:v", "1", "-vf", "scale=960:-2",
                    os.path.join(OUT, "demo", label + ".jpg")], check=True)
fill = Frame(out, 3.0)
results["face fill: no black bars at the sides"] = (fill.mean(0, 0, 40, 1080)[0] > 10 and fill.mean(1880, 0, 1920, 1080)[0] > 10,
                                                   (fill.mean(0, 0, 40, 1080), fill.mean(1880, 0, 1920, 1080)))
results["burn: mid frame differs from both photos"] = (Frame(out, 5.5, 480, 270).diff(Frame(out, 4.5, 480, 270)) > 5
                                                     and Frame(out, 5.5, 480, 270).diff(Frame(out, 6.5, 480, 270)) > 5, None)
results["title visible"] = (Frame(out, 8.5).bright_box(230) is not None, Frame(out, 8.5).bright_box(230))
results["flash: cut frame much brighter"] = (min(Frame(out, 15.0).mean()) > min(Frame(out, 14.0).mean()) + 40,
                                            (Frame(out, 14.0).mean(), Frame(out, 15.0).mean()))
report(results)
print(out)
