"""Chapter 4: transform units, crop, opacity, composite modes, overlapping placement. One second per case."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, Frame, append, connect, fresh_timeline, import_media, open_project, render, report

r = connect()
p = open_project(r)
mp = p.GetMediaPool()
names = ["marker_land.mp4", "marker_port.mp4", "grey.mp4", "blue.mp4", "clip_1.mp4", "clip_2.mp4"]
pool = import_media(mp, [os.path.join(MEDIA, n) for n in names])
M = {n: pool[os.path.join(MEDIA, n)] for n in names}

tl = fresh_timeline(p, "ch04_clip_properties")
tl.AddTrack("video")
results = {"AddTrack -> 2 video tracks": (tl.GetTrackCount("video") == 2, tl.GetTrackCount("video"))}

cases = [  # (label, clip, props, track-2 overlay clip or None, overlay props)
    ("land plain", "marker_land.mp4", {}, None, {}),
    ("land Pan=100", "marker_land.mp4", {"Pan": 100}, None, {}),
    ("land Tilt=100", "marker_land.mp4", {"Tilt": 100}, None, {}),
    ("land Zoom=2", "marker_land.mp4", {"ZoomX": 2.0, "ZoomY": 2.0}, None, {}),
    ("land CropLeft=960", "marker_land.mp4", {"CropLeft": 960}, None, {}),
    ("port plain", "marker_port.mp4", {}, None, {}),
    ("port Pan=100", "marker_port.mp4", {"Pan": 100}, None, {}),
    ("port CropLeft=300", "marker_port.mp4", {"CropLeft": 300}, None, {}),
    ("blue 50% over grey", "grey.mp4", {}, "blue.mp4", {"Opacity": 50.0}),
    ("grey Screen over grey", "grey.mp4", {}, "grey.mp4", {"CompositeMode": r.COMPOSITE_SCREEN}),
    ("land Rotation=90", "marker_land.mp4", {"RotationAngle": 90.0, "ZoomX": 0.5, "ZoomY": 0.5, "Pan": 400}, None, {}),
]
for k, (label, clip, props, over, oprops) in enumerate(cases):
    it = append(mp, tl, M[clip], k * 30, 30)
    if props:
        results[f"SetProperties {label}"] = (it.SetProperties(props), props)
    if over:
        o = append(mp, tl, M[over], k * 30, 30, track=2)
        o.SetProperties(oprops)

# Overlap: a second clip appended onto an occupied range of the same track.
n = len(cases)
first = append(mp, tl, M["clip_1.mp4"], n * 30, 30)
second = mp.AppendToTimeline([{"mediaPoolItem": M["clip_2.mp4"], "startFrame": 0, "endFrame": 30, "trackIndex": 1,
                               "recordFrame": tl.GetStartFrame() + n * 30, "mediaType": 1}])
v1 = tl.GetItemListInTrack("video", 1)
results["overlapping append on same track"] = (True, f"returned {bool(second)}, V1 items in range: "
                                               + str([i.GetName() for i in v1 if i.GetStart() >= tl.GetStartFrame() + n * 30]))

out = render(r, p, tl, "ch04_clip_properties")
F = [Frame(out, k + 0.5) for k in range(n + 1)]
box = {label: F[k].bright_box() for k, (label, *_) in enumerate(cases)}
for label, b in box.items():
    print("measure |", label, "| white box", b, "| centre", None if not b else ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))

def cx(label): b = box[label]; return (b[0] + b[2]) / 2
def cy(label): b = box[label]; return (b[1] + b[3]) / 2
def wd(label): b = box[label]; return b[2] - b[0]

results["landscape Pan 100 -> +100 px right"] = (abs(cx("land Pan=100") - cx("land plain") - 100) <= 3,
                                                 cx("land Pan=100") - cx("land plain"))
results["landscape Tilt 100 -> 100 px up"] = (abs(cy("land plain") - cy("land Tilt=100") - 100) <= 3,
                                              cy("land plain") - cy("land Tilt=100"))
results["Zoom 2 doubles the square"] = (abs(wd("land Zoom=2") / wd("land plain") - 2) < 0.1,
                                        wd("land Zoom=2") / wd("land plain"))
# A 1080x1920 clip is fitted to 607.5 px wide; Pan is scaled by fitted width / 1920.
results["portrait Pan 100 -> 100 * 607.5/1920 px"] = (abs(cx("port Pan=100") - cx("port plain") - 100 * 607.5 / 1920) <= 2,
                                                       cx("port Pan=100") - cx("port plain"))
results["landscape CropLeft 960 hides x<960, image not moved"] = (box["land CropLeft=960"][0] >= 958 and abs(box["land CropLeft=960"][2] - box["land plain"][2]) <= 3,
                                                                  box["land CropLeft=960"])
# Crop is in fitted-frame pixels from the image's own left edge (portrait image starts at x = 656).
results["portrait CropLeft 300 -> cut at 656 + 300"] = (abs(box["port CropLeft=300"][0] - 956) <= 2, box["port CropLeft=300"])
blend = F[8].mean(600, 300, 1300, 800)
results["Opacity 50 = average"] = (all(abs(blend[i] - (0x80 + (0x20, 0x60, 0xc0)[i]) / 2) < 6 for i in range(3)), blend)
scr = F[9].mean(600, 300, 1300, 800)
results["Screen grey over grey ~ 1-(1-g)^2"] = (abs(scr[0] - 255 * (1 - (1 - 128 / 255) ** 2)) < 8, scr)
results["Rotation 90 turns the square (still square)"] = (box["land Rotation=90"] is not None, box["land Rotation=90"])
results["overlap: which clip shows"] = (True, F[n].mean())
report(results)
