"""Chapter 22: jump cuts for talking-head footage. Find the pauses with ffmpeg silencedetect, keep the speech
(plus a little padding), and build a NEW timeline from source subclips placed back to back at absolute recordFrame.
Captions in an .srt are shifted by the same cuts. Then render and check the render, not the return values.

    ResolvePython 22_jumpcut.py [source.mp4 [captions.srt]] [--min-silence 0.6] [--pad 0.15] [--noise -35]
                                [--project NAME] [--out DIR]

Without a source it uses media/talk_src.mp4 + talk_src.srt from make_media.sh, whose picture carries its own frame
number, so every kept segment is read back frame-exactly. Analysis needs only ffmpeg, so this runs in ResolvePython.
Pause detection adapted from Hao0321/video-autopilot-kit (MIT); see docs 22.
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import FPS, MEDIA, Frame, connect, import_media, open_project, render, report

ap = argparse.ArgumentParser()
ap.add_argument("source", nargs="?", default=os.path.join(MEDIA, "talk_src.mp4"))
ap.add_argument("srt", nargs="?")
ap.add_argument("--min-silence", type=float, default=0.6, help="pauses at least this long are cut (s)")
ap.add_argument("--pad", type=float, default=0.15, help="silence kept on each side of speech (s)")
ap.add_argument("--noise", type=float, default=-35, help="silencedetect threshold (dB)")
ap.add_argument("--project", default=common.PROJECT)
ap.add_argument("--out", default=common.OUT, help="render folder (default examples/out)")
a = ap.parse_args()
SRC = os.path.abspath(a.source)
SRT = a.srt or (os.path.splitext(SRC)[0] + ".srt" if a.source.endswith("talk_src.mp4") else None)
SELFTEST = SRC.endswith("talk_src.mp4")
common.OUT = a.out


def ff(args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats"] + args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stderr


def probe(path):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=r_frame_rate,nb_frames,duration", "-of", "json", path],
                                  capture_output=True, text=True, check=True).stdout)["streams"][0]
    num, den = j["r_frame_rate"].split("/")
    return float(num) / float(den), int(j["nb_frames"])


def silences(path, noise, min_len):
    e = ff(["-i", path, "-vn", "-af", f"silencedetect=noise={noise}dB:d={min_len}", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", e)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", e)]
    return list(zip(starts, ends + [None] * (len(starts) - len(ends))))   # a pause running to EOF has no end


def keep_ranges(pauses, n, fps, pad):
    """Frames to keep, [(first, end_exclusive), ...]: everything except each pause minus `pad` on its speech sides."""
    cuts = []
    for s, e in pauses:
        a0 = 0 if s <= pad else round((s + pad) * fps)                 # leading silence: cut from frame 0
        b0 = n if e is None or e >= n / fps - pad else round((e - pad) * fps)
        if b0 > a0:
            cuts.append((a0, b0))
    keeps, pos = [], 0
    for a0, b0 in cuts:
        if a0 > pos:
            keeps.append((pos, a0))
        pos = max(pos, b0)
    if pos < n:
        keeps.append((pos, n))
    return keeps


def remap(t, keeps, fps):
    """Source seconds -> edited seconds. A time inside a cut lands on the splice (the end of the previous kept
    segment is the start of the next one in the edit)."""
    f, out = t * fps, 0
    for s, e in keeps:
        if f < s:
            return out / fps
        if f <= e:
            return (out + f - s) / fps
        out += e - s
    return out / fps


def srt_read(path):
    ts = lambda x: int(x[:2]) * 3600 + int(x[3:5]) * 60 + int(x[6:8]) + int(x[9:12]) / 1000
    blocks = re.split(r"\n\s*\n", open(path, encoding="utf-8-sig").read().strip())
    cues = []
    for b in blocks:
        lines = b.splitlines()
        m = re.match(r"(\d\d:\d\d:\d\d[,.]\d\d\d) --> (\d\d:\d\d:\d\d[,.]\d\d\d)", lines[1] if len(lines) > 1 else "")
        if m:
            cues.append((ts(m.group(1)), ts(m.group(2)), "\n".join(lines[2:])))
    return cues


def srt_write(path, cues):
    f = lambda x: "%02d:%02d:%02d,%03d" % (x // 3600, x // 60 % 60, x // 1 % 60, round(x % 1 * 1000) % 1000)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(f"{i}\n{f(s)} --> {f(e)}\n{txt}\n" for i, (s, e, txt) in enumerate(cues, 1)))


def frame_number(video, k, fps):
    """Read the 11-bit frame number drawn by make_media.sh (talk_src.mp4 only). ffmpeg -ss returns the first frame
    at or after the time, so aim 0.1 frame early."""
    fr = Frame(video, max(0.0, (k - 0.1) / fps))
    return sum(1 << b for b in range(11) if sum(fr.px(120 + b * 160, 100)) / 3 > 128)


fps, n = probe(SRC)
if round(fps) != FPS:
    raise SystemExit(f"{SRC} is {fps} fps; the timeline is {FPS} fps (open_project). Conform the source first.")
pauses = silences(SRC, a.noise, a.min_silence)
keeps = keep_ranges(pauses, n, fps, a.pad)
kept = sum(e - s for s, e in keeps)
print(f"{len(pauses)} pauses >= {a.min_silence}s; keep {len(keeps)} segments, {kept} of {n} frames")

r = connect()
p = open_project(r, a.project)
mp = p.GetMediaPool()
item = import_media(mp, [SRC])[SRC]
if int(item.GetClipProperty("Frames") or 0) != n:
    # the file was re-made under the same name: Resolve keeps the old clip info and the render fails partway
    raise SystemExit(f"media pool clip has {item.GetClipProperty('Frames')} frames, the file has {n}: delete the "
                     "clip (and timelines using it) from the pool and run again (docs 20.6)")
names ={p.GetTimelineByIndex(i).GetName() for i in range(1, p.GetTimelineCount() + 1)}
base = "ch22_jumpcut_" + os.path.splitext(os.path.basename(SRC))[0]
name = next(f"{base}_v{v}" for v in range(1, 1000) if f"{base}_v{v}" not in names)   # new timeline per revision
tl = mp.CreateEmptyTimeline(name)
if not tl:
    raise SystemExit(f"CreateEmptyTimeline({name}) failed")
p.SetCurrentTimeline(tl)
start, pos = tl.GetStartFrame(), 0
for s, e in keeps:
    # no mediaType: video and its audio go in together, linked. endFrame is exclusive (docs 2.3).
    if not mp.AppendToTimeline([{"mediaPoolItem": item, "startFrame": s, "endFrame": e, "recordFrame": start + pos}]):
        raise SystemExit(f"AppendToTimeline failed for source frames {s}-{e}")
    pos += e - s
placed = [(i.GetStart() - start, i.GetDuration(), i.GetSourceStartFrame()) for i in tl.GetItemListInTrack("video", 1)]
want, pos = [], 0
for s, e in keeps:
    want.append((pos, e - s, s))
    pos += e - s
results = {"timeline items = keep ranges (start, length, source in)": (placed == want, placed[:4])}
r.GetProjectManager().SaveProject()

if SRT:
    cues = []
    for s, e, txt in srt_read(SRT):
        ns, ne = remap(s, keeps, fps), remap(e, keeps, fps)
        if ne - ns >= 1 / fps:
            cues.append((ns, ne, txt))
    out_srt = os.path.join(a.out, name + ".srt")
    os.makedirs(a.out, exist_ok=True)
    srt_write(out_srt, cues)
    print("captions ->", out_srt)

out = render(r, p, tl, name)
_, got = probe(out)
results["rendered frames = sum of kept ranges (±1)"] = (abs(got - kept) <= 1, f"{got} vs {kept} (source {n})")
left = [(s, e) for s, e in silences(out, a.noise, a.min_silence) if e is not None and s > 0.05]
results[f"no pause >= {a.min_silence}s left inside the render"] = (not left, left)
checks, pos = [], 0
for s, e in keeps:
    for out_f, src_f in ((pos, s), (pos + e - s - 1, e - 1)):   # first and last frame of every kept segment
        if SELFTEST:
            checks.append((out_f, src_f, frame_number(out, out_f, fps)))
        else:
            d = Frame(out, (out_f + 0.4) / fps, 480, 270).diff(Frame(SRC, (src_f + 0.4) / fps, 480, 270))
            checks.append((out_f, src_f, d))
    pos += e - s
if SELFTEST:
    results["each segment's first/last frame is the planned source frame"] = (
        all(src == seen for _, src, seen in checks), [c for c in checks if c[1] != c[2]] or f"{len(checks)} frames")
else:
    results["each segment's first/last frame matches the source (mean diff < 3)"] = (
        all(d < 3 for *_, d in checks), max(d for *_, d in checks))
report(results)
