"""Chapter 2: connect, import, place clips, render, verify. Prints one PASS/FAIL line per claim."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # ResolvePython does not add the script dir
from common import MEDIA, append, connect, duration, fresh_timeline, import_media, open_project, render

r = connect()
p = open_project(r)
mp = p.GetMediaPool()
pool = import_media(mp, [os.path.join(MEDIA, f) for f in
                         ["clip_1.mp4", "clip_2.mp4", "still_3.png", "tone_10s.wav"]])

results = {}

# Numeric file names collapse into one image-sequence clip.
mp.ImportMedia([os.path.join(MEDIA, "1001.png"), os.path.join(MEDIA, "1002.png")])
seq = [c.GetName() for c in mp.GetRootFolder().GetClipList() if c.GetName().startswith("[1001")]
single = [c.GetName() for c in mp.GetRootFolder().GetClipList() if c.GetName() in ("1001.png", "1002.png")]
results["numeric names -> one sequence clip"] = (len(seq) == 1 and not single, seq + single)

tl = fresh_timeline(p, "ch02_first_timeline")
results["timeline starts at 01:00:00:00 = frame 108000"] = (tl.GetStartFrame() == 108000, tl.GetStartFrame())
results["CreateEmptyTimeline with an existing name returns None"] = (mp.CreateEmptyTimeline("ch02_first_timeline") is None, None)

a = append(mp, tl, pool[os.path.join(MEDIA, "clip_1.mp4")], 0, 90)
b = append(mp, tl, pool[os.path.join(MEDIA, "clip_2.mp4")], 90, 45, src_start=30)
results["video clip: endFrame exclusive -> duration == length"] = (a.GetDuration() == 90 and b.GetDuration() == 45,
                                                                  (a.GetDuration(), b.GetDuration()))
results["recordFrame is absolute (start + offset)"] = (b.GetStart() == tl.GetStartFrame() + 90, b.GetStart())
results["src_start honoured"] = (b.GetSourceStartFrame() == 30, b.GetSourceStartFrame())

s = append(mp, tl, pool[os.path.join(MEDIA, "still_3.png")], 135, 30)
results["still image ignores requested length (30)"] = (s.GetDuration() != 30, s.GetDuration())

aud = append(mp, tl, pool[os.path.join(MEDIA, "tone_10s.wav")], 0, 135, media_type=2)
results["audio via mediaType 2"] = (aud.GetDuration() == 135 and tl.GetItemListInTrack("audio", 1) != [],
                                    aud.GetDuration())

out = render(r, p, tl, "ch02_first_timeline")
expected = (135 + s.GetDuration()) / 30
results["render duration matches timeline"] = (abs(duration(out) - expected) < 0.1, (duration(out), expected))

for k, (ok, detail) in results.items():
    print("PASS" if ok else "FAIL", "|", k, "|", detail)
