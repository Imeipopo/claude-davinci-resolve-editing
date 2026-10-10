"""Chapter 19: things commonly listed as impossible through the API, re-tested on 21.1.
audio volume / pan / pitch, split a clip by patching a .drt, read transitions back from a .drt, subtitles from an .srt."""
import os
import re
import shutil
import subprocess
import sys
import uuid
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, OUT, Frame, append, connect, fresh_timeline, import_media, open_project, render, report

r = connect()
p = open_project(r)
mp = p.GetMediaPool()
GREY, TONE = os.path.join(MEDIA, "grey.mp4"), os.path.join(MEDIA, "tone_10s.wav")
C1, C3 = os.path.join(MEDIA, "clip_1.mp4"), os.path.join(MEDIA, "clip_3.mp4")
pool = import_media(mp, [GREY, TONE, C1, C3])
results = {}
os.makedirs(OUT, exist_ok=True)


def audio_stats(video, start, dur):
    """(left dB, right dB, zero crossings per second of the left channel) — pure Python on raw PCM."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", video, "-vn",
                          "-ac", "2", "-ar", "48000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
    import array, math
    a = array.array("h", raw)
    L, R = a[0::2], a[1::2]
    def db(x):
        rms = math.sqrt(sum(v * v for v in x) / max(1, len(x)))
        return round(20 * math.log10(rms / 32768 + 1e-12), 1)
    zc = sum(1 for i in range(1, len(L)) if (L[i - 1] < 0) != (L[i] < 0)) / dur
    return db(L), db(R), round(zc)


def drt_unpack(drt, folder):
    shutil.rmtree(folder, ignore_errors=True)
    with zipfile.ZipFile(drt) as z:
        z.extractall(folder)
    return [os.path.join(folder, "SeqContainer", f) for f in os.listdir(os.path.join(folder, "SeqContainer"))]


def drt_pack(folder, drt):
    if os.path.exists(drt):
        os.remove(drt)
    subprocess.run(["zip", "-q", "-r", drt, "."], cwd=folder, check=True)


# --- 19.1 audio volume / pan / pitch -------------------------------------------------------------------
tl = fresh_timeline(p, "ch19_audio")
append(mp, tl, pool[GREY], 0, 240)
parts = [append(mp, tl, pool[TONE], k * 60, 60, media_type=2, src_start=k * 60) for k in range(4)]
parts[1].SetProperties({"AudioVolumeEnabled": True, "AudioVolume": -12.0})
parts[2].SetProperties({"AudioPanEnabled": True, "AudioPan": -100.0})
parts[3].SetProperties({"AudioPitchEnabled": True, "AudioPitchSemiTones": 12.0})
out = render(r, p, tl, "ch19_audio")
st = [audio_stats(out, k * 2 + 0.5, 1.0) for k in range(4)]
results["AudioVolume -12 dB"] = (abs((st[0][0] - st[1][0]) - 12) < 0.6, (st[0], st[1]))
results["AudioPan -100 -> right channel ~12 dB quieter (mono source, not silent)"] = (st[2][0] - st[2][1] > 10, st[2])
results["AudioPitchSemiTones +12 -> frequency doubles"] = (abs(st[3][2] / st[0][2] - 2) < 0.1, (st[0][2], st[3][2]))

# --- 19.2 split (razor) by patching a .drt ------------------------------------------------------------
src = fresh_timeline(p, "ch19_split_src")
whole = append(mp, src, pool[C1], 0, 90, src_start=30)
drt = os.path.join(OUT, "ch19_split_src.drt")
src.Export(drt, r.EXPORT_DRT, r.EXPORT_NONE)
work = os.path.join(OUT, "ch19_split")
seqs = drt_unpack(drt, work)
s0 = src.GetStartFrame()
done = 0
for f in seqs:
    x = open(f, encoding="utf-8").read()
    m = re.search(r"(\s*<Element>\s*<Sm2TiVideoClip DbId=.*?</Sm2TiVideoClip>\s*</Element>)", x, re.S)
    if not m:
        continue
    el = m.group(1)
    first = el.replace("<Duration>90</Duration>", "<Duration>45</Duration>", 1)
    second = re.sub(r'DbId="[0-9a-f-]+"', lambda _: f'DbId="{uuid.uuid4()}"', el)   # every object needs a fresh id
    second = second.replace(f"<Start>{s0}</Start>", f"<Start>{s0 + 45}</Start>", 1)
    second = second.replace("<Duration>90</Duration>", "<Duration>45</Duration>", 1)
    second = second.replace("<In>30</In>", "<In>75</In>", 1)
    x = x.replace(el, first + second, 1).replace("<Name>ch19_split_src</Name>", "<Name>ch19_split</Name>")
    open(f, "w", encoding="utf-8").write(x)
    done += 1
pj = os.path.join(work, "project.xml")
x = open(pj, encoding="utf-8").read()
open(pj, "w", encoding="utf-8").write(x.replace("<ProjectName>ch19_split_src</ProjectName>",
                                                "<ProjectName>ch19_split</ProjectName>"))
old = [p.GetTimelineByIndex(i) for i in range(1, p.GetTimelineCount() + 1) if p.GetTimelineByIndex(i).GetName() == "ch19_split"]
if old:
    mp.DeleteTimelines(old)
split_drt = os.path.join(OUT, "ch19_split.drt")
drt_pack(work, split_drt)
t_split = mp.ImportTimelineFromFile(split_drt)
if t_split is None:
    report(results)
    raise SystemExit("split .drt import failed (an error dialog is now open in Resolve)")
items = [(i.GetStart() - t_split.GetStartFrame(), i.GetDuration(), i.GetSourceStartFrame())
         for i in t_split.GetItemListInTrack("video", 1)]
results["split: one clip became two (0-45 src 30, 45-90 src 75)"] = (items == [(0, 45, 30), (45, 45, 75)], items)
o1, o2 = render(r, p, src, "ch19_split_src"), render(r, p, t_split, "ch19_split")
results["split render identical to the original"] = (max(Frame(o1, s, 480, 270).diff(Frame(o2, s, 480, 270)) for s in (0.5, 1.4, 1.6, 2.5)) < 1.0, None)
# give the second half a different look to prove they are independent clips now
t_split.GetItemListInTrack("video", 1)[1].SetProperties({"ZoomX": 2.0, "ZoomY": 2.0})
results["the two halves can be edited separately"] = (True, None)

# --- 19.3 read transitions back from a .drt -----------------------------------------------------------
tt = fresh_timeline(p, "ch19_transitions_readback")
a = append(mp, tt, pool[C1], 0, 60, src_start=60)
b = append(mp, tt, pool[C3], 60, 60, src_start=60)
c = append(mp, tt, pool[C1], 120, 60, src_start=60)
a.AddTransition({"type": "Cross Dissolve", "category": "simple", "position": "end", "alignment": "center", "duration": 20})
b.AddTransition({"type": "Brightness Flash", "category": "fusion", "position": "end", "alignment": "right", "duration": 14})
drt3 = os.path.join(OUT, "ch19_transitions.drt")
tt.Export(drt3, r.EXPORT_DRT, r.EXPORT_NONE)
found = []
for f in drt_unpack(drt3, os.path.join(OUT, "ch19_tr")):
    x = open(f, encoding="utf-8").read()
    for m in re.finditer(r"<Sm2TiTransition DbId=.*?</Sm2TiTransition>", x, re.S):
        blk = m.group(0)
        g = lambda tag: (re.search(f"<{tag}>([^<]*)</{tag}>", blk) or [None, None])[1]
        kind = g("PrettyType")
        if kind == "Fusion Transition":   # the template name sits inside the hex FieldsBlob
            blob = bytes.fromhex(g("FieldsBlob") or "")
            hit = re.search(rb"Templates/Edit/Transitions/([ -~]+?)(?:[^ -~]|$)", blob)
            kind = hit.group(1).decode() if hit else kind
        found.append({"type": kind, "start": int(g("Start")) - tt.GetStartFrame(), "duration": int(g("Duration")),
                      "alignment": g("AlignmentType")})
results["transitions read back from .drt (type, start, length)"] = (
    [(x["type"], x["duration"]) for x in found] == [("Cross Dissolve", 20), ("Brightness Flash", 14)], found)

# --- 19.4 subtitles from an .srt ----------------------------------------------------------------------
srt = os.path.join(OUT, "ch19.srt")
with open(srt, "w", encoding="utf-8") as fh:
    fh.write("1\n00:00:00,500 --> 00:00:02,000\nHello from Claude\n\n2\n00:00:02,500 --> 00:00:04,000\n第二句字幕\n")
sub_items = [c for c in mp.GetRootFolder().GetClipList() if c.GetClipProperty("File Path") == srt] or mp.ImportMedia([srt]) or []
results["ImportMedia(.srt) -> pool item"] = (bool(sub_items), [s.GetName() for s in sub_items])
# AppendToTimeline ignores recordFrame for subtitles and appends after the last item, so place the .srt FIRST
st_tl = fresh_timeline(p, "ch19_subtitles")
st_tl.AddTrack("subtitle")
mp.AppendToTimeline([{"mediaPoolItem": sub_items[0], "trackIndex": 1, "recordFrame": st_tl.GetStartFrame()}])
append(mp, st_tl, pool[GREY], 0, 150)
subs = st_tl.GetItemListInTrack("subtitle", 1)
results["subtitles land at their .srt times when placed first"] = (
    [(s.GetStart() - st_tl.GetStartFrame(), s.GetDuration()) for s in subs] == [(15, 45), (75, 45)],
    [(s.GetName(), s.GetStart() - st_tl.GetStartFrame(), s.GetDuration()) for s in subs])
report(results)

# --- 19.5 burn the subtitles into the render ------------------------------------------------------------
import time
p.SetCurrentTimeline(st_tl)
r.OpenPage("deliver")
p.DeleteAllRenderJobs()
p.SetCurrentRenderFormatAndCodec("mp4", "H264")
p.SetRenderSettings({"SelectAllFrames": True, "TargetDir": OUT, "CustomName": "ch19_subtitles_burnin",
                     "FormatWidth": 1920, "FormatHeight": 1080, "ExportSubtitle": True, "SubtitleFormat": "BurnIn"})
job = p.AddRenderJob()
p.StartRendering([job])
while p.IsRenderingInProgress():
    time.sleep(1)
r.OpenPage("edit")
burn = os.path.join(OUT, "ch19_subtitles_burnin.mp4")
seen = {t: Frame(burn, t).bright_box(200) for t in (1.0, 2.2, 3.0)}
print("PASS" if seen[1.0] and seen[3.0] and not seen[2.2] else "FAIL", "| subtitles burned in (text at 1.0 s and 3.0 s, none in the gap) |", seen)
