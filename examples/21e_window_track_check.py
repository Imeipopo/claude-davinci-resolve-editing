"""Chapter 21.8: a tracked Power Window. Drawing the window and pressing "track" have no API, so they are done on the
colour page by hand or with CGEvent (docs 1.11); the grade inside the window is set from the script with SetCDL.
Setup: 21e_window_track_check.py --setup builds ch21_track (track_disc.mp4: a disc moving 8 px right, 3 px down per
frame on flat grey). Then: Window panel > Circle, size 23 (fits the disc), Tracker panel > track forward.
This script then tints node 1 red with SetCDL and checks the tint sits on the disc at the start, middle and end."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, Frame, append, connect, fresh_timeline, import_media, open_project, render, report, timecode

r = connect()
p = open_project(r)
mp = p.GetMediaPool()
SRC = os.path.join(MEDIA, "track_disc.mp4")
pool = import_media(mp, [SRC])

if "--setup" in sys.argv:
    tl = fresh_timeline(p, "ch21_track")
    append(mp, tl, pool[SRC], 0, 90)
    tl.SetCurrentTimecode(timecode(tl, 0))
    r.OpenPage("color")
    sys.exit(0)

tl = next(p.GetTimelineByIndex(i) for i in range(1, p.GetTimelineCount() + 1)
          if p.GetTimelineByIndex(i).GetName() == "ch21_track")
p.SetCurrentTimeline(tl)
item = tl.GetItemListInTrack("video", 1)[0]
ok = item.SetCDL({"NodeIndex": "1", "Slope": "1.8 0.6 0.6", "Offset": "0 0 0", "Power": "1 1 1", "Saturation": "1"})
out = render(r, p, tl, "ch21_window_track")


def disc_centre(n):
    return 960 + 8 * n, 540 + 3 * n


def redness(f, x, y, half=60):
    """Mean R - mean G in a square around (x, y)."""
    m = f.mean(x - half, y - half, x + half, y + half, step=3)
    return round(m[0] - m[1], 1)


results = {"SetCDL on the windowed node": (ok, ok)}
for n in (0, 45, 88):
    t = n / 30 + 0.005
    graded, source = Frame(out, t), Frame(SRC, t)
    x, y = disc_centre(n)
    inside = (redness(source, x, y), redness(graded, x, y))
    # Where the disc was at frame 0 is flat grey later on: it must stay neutral (window moved away).
    left_behind = redness(graded, 960, 540) if n == 88 else None
    results[f"frame {n}: disc is tinted"] = (inside[1] > inside[0] + 25, {"source R-G": inside[0],
                                                                        "graded R-G": inside[1]})
    if left_behind is not None:
        results["frame 88: the start position is neutral grey again"] = (abs(left_behind) < 4, left_behind)
report(results)
