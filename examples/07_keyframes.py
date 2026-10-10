"""Chapter 7: animated zoom/position three ways — Dynamic Zoom, FCPXML-imported keyframes, Fusion Transform keyframes."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, OUT, Frame, append, connect, fresh_timeline, import_media, open_project, render, report

r = connect()
p = open_project(r)
mp = p.GetMediaPool()
LAND = os.path.join(MEDIA, "marker_land.mp4")
pool = import_media(mp, [LAND])
results = {}


def side(f):
    b = f.bright_box(128)
    return None if not b else (b[2] - b[0], (b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


# 7.1 Dynamic Zoom
tl = fresh_timeline(p, "ch07_dynamic_zoom")
it = append(mp, tl, pool[LAND], 0, 90)
results["Dynamic Zoom enable + ease"] = (it.SetProperties({"DynamicZoomEnabled": True,
                                                           "DynamicZoomEase": r.DYNAMIC_ZOOM_EASE_OUT}), None)
out = render(r, p, tl, "ch07_dynamic_zoom")
a, b = side(Frame(out, 0.05)), side(Frame(out, 2.95))
results["Dynamic Zoom animates; default direction is zoom OUT (square shrinks)"] = (a and b and a[0] > b[0] * 1.05, (a, b))

# 7.2 FCPXML with keyframes -> ImportTimelineFromFile
fcpxml = os.path.join(OUT, "ch07_keyframes.fcpxml")
os.makedirs(OUT, exist_ok=True)
with open(fcpxml, "w") as f:
    f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.10">
 <resources>
  <format id="r0" name="FFVideoFormat1080p30" width="1920" height="1080" frameDuration="1/30s"/>
  <format id="r1" name="FFVideoFormatRateUndefined" width="1920" height="1080" frameDuration="1/30s"/>
  <asset id="r2" name="marker_land.mp4" start="0/1s" duration="8/1s" hasVideo="1" format="r1">
   <media-rep kind="original-media" src="file://{LAND}"/>
  </asset>
 </resources>
 <library><event name="ch07"><project name="ch07_fcpxml_keyframes">
  <sequence format="r0" tcFormat="NDF" tcStart="3600/1s" duration="6/1s">
   <spine>
    <asset-clip ref="r2" name="scale" offset="3600/1s" start="1/1s" duration="3/1s" format="r1" tcFormat="NDF">
     <adjust-transform>
      <param name="scale"><keyframeAnimation>
       <keyframe time="1/1s" value="1 1"/><keyframe time="4/1s" value="2 2"/>
      </keyframeAnimation></param>
     </adjust-transform>
    </asset-clip>
    <asset-clip ref="r2" name="position" offset="3603/1s" start="1/1s" duration="3/1s" format="r1" tcFormat="NDF">
     <adjust-transform>
      <param name="position"><keyframeAnimation>
       <keyframe time="1/1s" value="0 0"/><keyframe time="4/1s" value="20 10"/>
      </keyframeAnimation></param>
     </adjust-transform>
    </asset-clip>
   </spine>
  </sequence>
 </project></event></library>
</fcpxml>
''')
old = [p.GetTimelineByIndex(i) for i in range(1, p.GetTimelineCount() + 1)
       if p.GetTimelineByIndex(i).GetName() == "ch07_fcpxml_keyframes"]
if old:
    mp.DeleteTimelines(old)
tl2 = mp.ImportTimelineFromFile(fcpxml, {"timelineName": "ch07_fcpxml_keyframes", "importSourceClips": False,
                                         "sourceClipsFolders": [mp.GetRootFolder()]})
results["FCPXML import"] = (tl2 is not None, tl2.GetName() if tl2 else None)
out2 = render(r, p, tl2, "ch07_fcpxml_keyframes")
s0, s1 = side(Frame(out2, 0.05)), side(Frame(out2, 2.95))
results["FCPXML scale keyframes 1 -> 2"] = (s0 and s1 and abs(s1[0] / s0[0] - 2) < 0.12, (s0, s1))
p0, p1 = side(Frame(out2, 3.05)), side(Frame(out2, 5.95))
# sampled 0.05 s after the first key and 0.05 s before the last, so expect a little less than 216/108
results["FCPXML position 20,10 -> ~+216 px right, ~+108 px up (1 unit = 1080/100 px)"] = (
    p0 and p1 and 196 < p1[1] - p0[1] <= 216 and 98 < p0[2] - p1[2] <= 108, (p0, p1))

# 7.3 Fusion Transform keyframes
tl3 = fresh_timeline(p, "ch07_fusion_transform")
it3 = append(mp, tl3, pool[LAND], 0, 60)
comp = it3.AddFusionComp()
mi, mo = comp.FindTool("MediaIn1"), comp.FindTool("MediaOut1")
tr = comp.AddTool("Transform", -32768, -32768)
tr.ConnectInput("Input", mi)
mo.ConnectInput("Input", tr)
tr.AddModifier("Size", "BezierSpline")
tr.SetInput("Size", 1.0, 0)
tr.SetInput("Size", 1.5, 59)
out3 = render(r, p, tl3, "ch07_fusion_transform")
f0, f1 = side(Frame(out3, 0.02)), side(Frame(out3, 1.95))   # 1.97 s is past the last frame (59/30 = 1.967)
results["Fusion Transform Size keyframes 1 -> 1.5"] = (f0 and f1 and abs(f1[0] / f0[0] - 1.5) < 0.08, (f0, f1))
report(results)
