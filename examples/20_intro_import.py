"""Chapter 20: put a generated intro into Resolve.
Make the two inputs first (examples/20_intro_generator, see its README):
    node gen.mjs render 7 --fps 30            # template 11 pixel intro, 16:9, 6 s, synthesized SFX
    node gen.mjs render 11 --fps 30 --alpha   # template 6 on a transparent background, ProRes 4444
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, Frame, append, connect, fresh_timeline, import_media, open_project, render, report

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "20_intro_generator", "out", "gen")
INTRO = os.path.join(GEN, "像素風_seed7_16x9_6.00s_30fps.mp4")
OVERLAY = os.path.join(GEN, "字體即結構_seed11_9x16_15.00s_30fps_alpha.mov")
CLIP1, CLIP2 = os.path.join(MEDIA, "clip_1.mp4"), os.path.join(MEDIA, "clip_2.mp4")
GREY = os.path.join(MEDIA, "grey.mp4")


def loudness(video, start, length):
    err = subprocess.run(["ffmpeg", "-nostats", "-ss", str(start), "-t", str(length), "-i", video,
                          "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    summary = err[err.rfind("Summary"):]
    return float(summary.split("I:")[1].split("LUFS")[0])


def video_seconds(video):
    return float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration",
                                 "-of", "csv=p=0", video], capture_output=True, text=True).stdout)


def has_audio(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name",
                          "-of", "csv=p=0", video], capture_output=True, text=True).stdout
    return bool(out.strip())


for f in (INTRO, OVERLAY):
    if not os.path.exists(f):
        raise SystemExit(f"missing {f}: run the gen.mjs commands in this file's docstring first")

r = connect()
p = open_project(r)
mp = p.GetMediaPool()
# A re-rendered intro keeps its file name, but the media pool keeps the old clip and its cached decode
# (the render then fails partway). Drop our timelines and the stale pool clips, then import again.
mp.DeleteTimelines([t for t in (p.GetTimelineByIndex(i) for i in range(1, p.GetTimelineCount() + 1))
                    if t.GetName().startswith("20_intro")])
stale = [c for c in mp.GetRootFolder().GetClipList() if c.GetClipProperty("File Path") in (INTRO, OVERLAY)]
if stale:
    mp.DeleteClips(stale)
pool = import_media(mp, [INTRO, OVERLAY, CLIP1, CLIP2, GREY])
results = {}

intro = pool[INTRO]
results["intro imports as 30 fps, 180 frames"] = (
    float(intro.GetClipProperty("FPS")) == 30 and int(intro.GetClipProperty("Frames")) == 180,
    f"FPS {intro.GetClipProperty('FPS')}, frames {intro.GetClipProperty('Frames')}")

# 1. Intro at the head of V1 (its audio on A1), the programme continues right after it.
tl = fresh_timeline(p, "20_intro_head")
append(mp, tl, intro, 0, 180)
append(mp, tl, intro, 0, 180, media_type=2)
append(mp, tl, pool[GREY], 180, 150)
out = render(r, p, tl, "20_intro_head")
results["head: video is 11 s"] = (abs(video_seconds(out) - 11) < 0.05, f"{video_seconds(out):.3f} s")
d_intro = Frame(out, 3.0).diff(Frame(INTRO, 3.0))
results["head: 3.0 s matches the intro file"] = (d_intro < 3, f"mean abs diff {d_intro}")
d_prog = Frame(out, 8.0).diff(Frame(GREY, 2.0))
results["head: 8.0 s is the programme clip"] = (d_prog < 3, f"mean abs diff {d_prog}")
lufs = loudness(out, 0, 6) if has_audio(out) else None
results["head: intro SFX survive at about -14 LUFS"] = (lufs is not None and abs(lufs + 14) < 1.5, f"{lufs} LUFS")

# 2. Transparent ProRes 4444 on V2 over footage: only the overlay's own pixels may change.
tl2 = fresh_timeline(p, "20_intro_overlay")
tl2.AddTrack("video")
append(mp, tl2, pool[CLIP1], 0, 240)
append(mp, tl2, pool[CLIP2], 240, 210)
ov = append(mp, tl2, pool[OVERLAY], 0, 450, track=2)
with_ov = render(r, p, tl2, "20_intro_overlay")
tl2.SetTrackEnable("video", 2, False)
without = render(r, p, tl2, "20_intro_overlay_off")
tl2.SetTrackEnable("video", 2, True)
a, b = Frame(with_ov, 14.5), Frame(without, 14.5)
# A 1080x1920 clip fits a 1920x1080 timeline as a 607.5 px wide column centred at x = 960.
left = sum(abs(x - y) for x, y in zip(a.mean(0, 0, 640, 1080), b.mean(0, 0, 640, 1080)))
right = sum(abs(x - y) for x, y in zip(a.mean(1280, 0, 1920, 1080), b.mean(1280, 0, 1920, 1080)))
inside = sum(abs(x - y) for x, y in zip(a.mean(660, 300, 1260, 760), b.mean(660, 300, 1260, 760)))
results["overlay: footage outside the overlay column untouched"] = (left < 1 and right < 1, f"left {left:.2f}, right {right:.2f}")
results["overlay: overlay pixels drawn on top"] = (inside > 5, f"mean colour shift inside {inside:.2f}")
report(results)
