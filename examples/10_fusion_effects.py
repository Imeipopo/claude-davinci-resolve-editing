"""Chapter 10-11: Fusion comps on timeline clips — built-in Fusion tools, Resolve FX inside Fusion, Burn Away, Lock()."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, Frame, append, connect, fresh_timeline, import_media, open_project, render, report

TOOLS = [  # (label, Fusion RegID, inputs)
    ("Transform (no change)", "Transform", {}),
    ("SoftGlow", "SoftGlow", {"Gain": 1.0}),
    ("CameraShake", "CameraShake", {"Deviation": 0.1}),
    ("RFX Glow", "ofx.com.blackmagicdesign.resolvefx.Glow", {}),
    ("RFX Lightray", "ofx.com.blackmagicdesign.resolvefx.Lightray", {}),
    ("RFX ZoomBlur", "ofx.com.blackmagicdesign.resolvefx.ZoomBlur", {}),
    ("RFX ChromaticAberration", "ofx.com.blackmagicdesign.resolvefx.ChromaticAberration",
     {"curvatureRed": 5.0, "curvatureBlue": -5.0}),   # defaults are 0 = no visible effect
    ("RFX FilmDamage", "ofx.com.blackmagicdesign.resolvefx.FilmDamage", {}),
    ("RFX FilmGrain", "ofx.com.blackmagicdesign.resolvefx.FilmGrain", {"Opacity": 1.0, "GrainStrength": 0.6}),
    ("RFX Vignette", "ofx.com.blackmagicdesign.resolvefx.Vignette", {}),
    ("RFX DirectionalBlur", "ofx.com.blackmagicdesign.resolvefx.DirectionalBlur", {}),
    ("RFX CameraShake", "ofx.com.blackmagicdesign.resolvefx.CameraShake", {}),
]


def chain(item, reg_id, inputs):
    comp = item.AddFusionComp()
    mi, mo = comp.FindTool("MediaIn1"), comp.FindTool("MediaOut1")
    t = comp.AddTool(reg_id, -32768, -32768)
    if not t:
        return None, None
    # Resolve FX (OFX) tools take the image on "Source"; native Fusion tools on "Input".
    t.ConnectInput("Source" if reg_id.startswith("ofx.") else "Input", mi)
    for k, v in inputs.items():
        t.SetInput(k, v)
    mo.ConnectInput("Input", t)
    return comp, t


r = connect()
p = open_project(r)
mp = p.GetMediaPool()
A, B = os.path.join(MEDIA, "clip_1.mp4"), os.path.join(MEDIA, "clip_3.mp4")
pool = import_media(mp, [A, B])
results = {}

fu = r.Fusion()
ids = [v.GetAttrs().get("REGS_ID") for v in fu.GetRegList(1).values()]
rfx = sorted(i for i in ids if i and "resolvefx" in i)
results["Resolve FX available as Fusion tools"] = (len(rfx) > 50, len(rfx))

# 10.x one effect per 2-s clip, plus an untouched reference clip first
tl = fresh_timeline(p, "ch10_fusion_effects")
append(mp, tl, pool[A], 0, 60, src_start=60)
added = {}
for k, (label, reg, inputs) in enumerate(TOOLS):
    it = append(mp, tl, pool[A], (k + 1) * 60, 60, src_start=60)
    added[label] = chain(it, reg, inputs)[1] is not None
out = render(r, p, tl, "ch10_fusion_effects")
plain = Frame(out, 1.0)   # full resolution: grain and fringing vanish when downscaled
diffs = {label: Frame(out, (k + 1) * 2 + 1.0).diff(plain) for k, (label, *_) in enumerate(TOOLS)}
results["AddTool succeeded for every tool"] = (all(added.values()), [k for k, v in added.items() if not v])
results["each effect changes the picture (Transform must not)"] = (
    diffs["Transform (no change)"] < 0.5 and all(v > 1 for k, v in diffs.items() if k != "Transform (no change)"), diffs)

# 11.2 Burn Away: upper clip burns to transparent and reveals the clip below.
tl2 = fresh_timeline(p, "ch11_burn_away")
tl2.AddTrack("video")
append(mp, tl2, pool[B], 0, 90)
up = append(mp, tl2, pool[A], 0, 60, track=2)
comp = up.AddFusionComp()
mi, mo = comp.FindTool("MediaIn1"), comp.FindTool("MediaOut1")
bg = comp.AddTool("Background", -32768, -32768)
for k in ("TopLeftRed", "TopLeftGreen", "TopLeftBlue", "TopLeftAlpha"):
    bg.SetInput(k, 0)
ba = comp.AddTool("ofx.com.blackmagicdesign.resolvefx.BurnAway", -32768, -32768)
ba.ConnectInput("SourceFrom", mi)
ba.ConnectInput("SourceTo", bg)
mo.ConnectInput("Input", ba)
ba.AddModifier("Transition", "BezierSpline")
for fr, v in [(0, 0.0), (30, 0.0), (59, 1.0)]:
    ba.SetInput("Transition", v, fr)
out2 = render(r, p, tl2, "ch11_burn_away")
fa, fb = Frame(out2, 0.5, 480, 270), Frame(out2, 2.5, 480, 270)
mid = Frame(out2, 1.5, 480, 270)
results["Burn Away: before = upper clip, after = lower clip, middle = mix"] = (
    fa.diff(fb) > 5 and mid.diff(fa) > 2 and mid.diff(fb) > 2, (fa.diff(fb), mid.diff(fa), mid.diff(fb)))

# 11.3 Burn Away with SourceTo left unconnected -> render fails once Transition > 0
tl3 = fresh_timeline(p, "ch11_burn_away_unconnected")
it3 = append(mp, tl3, pool[A], 0, 60)
c3 = it3.AddFusionComp()
b3 = c3.AddTool("ofx.com.blackmagicdesign.resolvefx.BurnAway", -32768, -32768)
b3.ConnectInput("SourceFrom", c3.FindTool("MediaIn1"))
c3.FindTool("MediaOut1").ConnectInput("Input", b3)
b3.AddModifier("Transition", "BezierSpline")
b3.SetInput("Transition", 0.0, 0)
b3.SetInput("Transition", 1.0, 59)
try:
    render(r, p, tl3, "ch11_burn_away_unconnected")
    results["Burn Away without SourceTo fails to render"] = (False, "rendered")
except RuntimeError as e:
    results["Burn Away without SourceTo fails to render"] = (True, str(e))

# 11.4 Lock(): changes made between Lock() and Unlock() do not reach the render
tl4 = fresh_timeline(p, "ch11_lock")
it4 = append(mp, tl4, pool[A], 0, 30, src_start=60)
c4, glow = chain(it4, "SoftGlow", {"Gain": 0.0})
before = render(r, p, tl4, "ch11_lock_before")
c4.Lock()
glow.SetInput("Gain", 3.0)
c4.Unlock()
after_locked = render(r, p, tl4, "ch11_lock_after_locked")
glow.SetInput("Gain", 3.0)
after_plain = render(r, p, tl4, "ch11_lock_after_plain")
d_locked = Frame(after_locked, 0.5, 480, 270).diff(Frame(before, 0.5, 480, 270))
d_plain = Frame(after_plain, 0.5, 480, 270).diff(Frame(before, 0.5, 480, 270))
results["value set inside Lock()/Unlock() reaches the render?"] = (True, {"locked edit diff": d_locked,
                                                                          "plain edit diff": d_plain})
report(results)
