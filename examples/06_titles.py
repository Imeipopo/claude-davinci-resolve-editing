"""Chapter 6: Fusion titles — where they land, how to set text, two ways to put them on any track, template names."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, Frame, append, connect, fresh_timeline, import_media, open_project, render, report, timecode

TEMPLATES = ["Text+", "MultiText", "Text", "Scroll", "Background Reveal", "Background Reveal Lower Third", "Call Out",
             "Center Reveal", "Clean and Simple", "Dark Box Text", "Digital Glitch", "Drop In", "Fade On", "Slide In",
             "Lower 3rd", "Simple Underline", "Draw On 1 Line"]


def set_text(item, text, size=0.2):
    comp = item.GetFusionCompByIndex(1)
    tools = list(comp.GetToolList(False, "TextPlus").values())
    for t in tools:
        t.SetInput("StyledText", text)
        if size:
            t.SetInput("Size", size)
    return [t.GetInput("StyledText") for t in tools]


r = connect()
p = open_project(r)
mp = p.GetMediaPool()
GREY, PH = os.path.join(MEDIA, "grey.mp4"), os.path.join(MEDIA, "transparent_10s.mov")
pool = import_media(mp, [GREY, PH])
results = {}

# 6.1 where InsertFusionTitleIntoTimeline puts the title
tl = fresh_timeline(p, "ch06_insert_behaviour")
append(mp, tl, pool[GREY], 0, 150)
tl.AddTrack("video")
tl.SetCurrentTimecode(timecode(tl, 30))
t = tl.InsertFusionTitleIntoTimeline("Text+")
v1 = [(i.GetName(), i.GetStart() - tl.GetStartFrame(), i.GetDuration()) for i in tl.GetItemListInTrack("video", 1)]
results["insert lands on V1 at the playhead, cutting the clip under it"] = (
    t is not None and t.GetTrackTypeAndIndex() == ["video", 1] and len(tl.GetItemListInTrack("video", 2)) == 0, v1)
results["inserted title default length"] = (True, t.GetDuration() if t else None)
tl.SetTrackLock("video", 1, True)
results["V1 locked -> insert returns None"] = (tl.InsertFusionTitleIntoTimeline("Text+") is None, None)
tl.SetTrackLock("video", 1, False)
tl.SetTrackEnable("video", 1, False)
t2 = tl.InsertFusionTitleIntoTimeline("Text+")
results["V1 disabled -> still lands on V1"] = (t2 is not None and t2.GetTrackTypeAndIndex() == ["video", 1],
                                               t2.GetTrackTypeAndIndex() if t2 else None)
tl.SetTrackEnable("video", 1, True)

# 6.3 nested-timeline route: build the title alone, then place that timeline on V2
sub = fresh_timeline(p, "ch06_title_TAKE_ME")
st = sub.InsertFusionTitleIntoTimeline("Text+")
results["set text through the Fusion comp"] = (set_text(st, "TAKE ME") == ["TAKE ME"], set_text(st, "TAKE ME"))
sub_item = next(c for c in mp.GetRootFolder().GetClipList() if c.GetName() == "ch06_title_TAKE_ME")

main = fresh_timeline(p, "ch06_titles")
append(mp, main, pool[GREY], 0, 120)
main.AddTrack("video")
nested = append(mp, main, sub_item, 30, 30, track=2)   # the sub-timeline is just another pool clip
results["nested timeline placed on V2 at 1 s"] = (nested.GetTrackTypeAndIndex() == ["video", 2], nested.GetStart() - main.GetStartFrame())

# 6.4 transparent placeholder hosting a Fusion Text+ on V2 at 2.5-3.5 s
ph = append(mp, main, pool[PH], 75, 30, track=2)
comp = ph.AddFusionComp()
mi, mo = comp.FindTool("MediaIn1"), comp.FindTool("MediaOut1")
tx = comp.AddTool("TextPlus", -32768, -32768)
tx.SetInput("StyledText", "LOVE")
tx.SetInput("Size", 0.2)
mg = comp.AddTool("Merge", -32768, -32768)
mg.ConnectInput("Background", mi)
mg.ConnectInput("Foreground", tx)
mo.ConnectInput("Input", mg)

out = render(r, p, main, "ch06_titles")
grey_only, take, gap, love = (Frame(out, s) for s in (0.5, 1.5, 2.2, 3.0))
results["nested title visible at 1.5 s"] = (take.bright_box(200) is not None, take.bright_box(200))
results["placeholder title visible at 3.0 s"] = (love.bright_box(200) is not None, love.bright_box(200))
results["no text where V2 is empty / transparent"] = (grey_only.bright_box(200) is None and gap.bright_box(200) is None, None)
results["grey still shows around the text"] = (abs(take.mean(0, 0, 300, 200)[0] - 128) < 6, take.mean(0, 0, 300, 200))

# 6.5 template catalogue: each on its own 150-frame slot of an empty timeline
cat = fresh_timeline(p, "ch06_title_templates")
ok = {}
for k, name in enumerate(TEMPLATES):
    cat.SetCurrentTimecode(timecode(cat, k * 150))
    item = cat.InsertFusionTitleIntoTimeline(name)
    ok[name] = item is not None
    if item:
        set_text(item, "SAMPLE", size=None)   # "Slide In" ships with an empty text
out2 = render(r, p, cat, "ch06_title_templates")
visible = {}
for k, name in enumerate(TEMPLATES):
    if ok[name]:
        visible[name] = any(Frame(out2, k * 5 + s, 480, 270).bright_box(40) for s in (1.0, 2.5, 4.0))
results["templates inserted"] = (True, [n for n in TEMPLATES if ok[n]])
results["templates rejected"] = (True, [n for n in TEMPLATES if not ok[n]])
results["inserted templates show text in the render"] = (all(visible.values()), {n: v for n, v in visible.items() if not v})
report(results)
