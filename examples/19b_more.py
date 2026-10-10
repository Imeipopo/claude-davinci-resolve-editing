"""Chapter 19 (part 2): channel mapping, proxies, folder 'rename', render in place, fit-to-fill, replace, insert edit."""
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, OUT, Frame, append, connect, fresh_timeline, import_media, open_project, render, report

r = connect()
p = open_project(r)
mp = p.GetMediaPool()
root = mp.GetRootFolder()
STEREO, GREY, RAMP = (os.path.join(MEDIA, n) for n in ("stereo_LR.wav", "grey.mp4", "ramp_src.mp4"))
C1, C3 = os.path.join(MEDIA, "clip_1.mp4"), os.path.join(MEDIA, "clip_3.mp4")
pool = import_media(mp, [STEREO, GREY, RAMP, C1, C3])
results = {}
os.makedirs(OUT, exist_ok=True)


def zc_per_channel(video, start, dur):
    """Zero crossings per second for L and R (a 440 Hz sine gives ~880)."""
    import array
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", video, "-vn", "-ac", "2",
                          "-ar", "48000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
    a = array.array("h", raw)
    zc = lambda x: round(sum(1 for i in range(1, len(x)) if (x[i - 1] < 0) != (x[i] < 0)) / dur)
    return zc(a[0::2]), zc(a[1::2])


# --- channel mapping: a stereo file with 440 Hz left / 880 Hz right -----------------------------------
tl = fresh_timeline(p, "ch19b_channels")
append(mp, tl, pool[GREY], 0, 120)
a1 = append(mp, tl, pool[STEREO], 0, 60, media_type=2)
a2 = append(mp, tl, pool[STEREO], 60, 60, media_type=2, src_start=60)
results["timeline item channel mapping read"] = (bool(a2.GetSourceAudioChannelMapping()), a2.GetSourceAudioChannelMapping())
ok = a2.SetSourceAudioChannelMapping('{"track_mapping": {"1": {"channel_idx": [1, 1], "mute": false, "type": "Stereo"}}}')
out = render(r, p, tl, "ch19b_channels")
before, after = zc_per_channel(out, 0.5, 1.0), zc_per_channel(out, 2.5, 1.0)
results["SetSourceAudioChannelMapping [1,1]: right channel now plays the left source"] = (
    ok and abs(before[1] - 1760) < 40 and abs(after[1] - 880) < 40, (ok, before, after))

# --- proxies: make one with ffmpeg and link it --------------------------------------------------------
proxy = os.path.join(OUT, "clip_1_proxy.mov")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", C1, "-vf", "scale=960:-2", "-c:v", "prores_ks", "-profile:v", "0",
                proxy], check=True)
item = pool[C1]
item.UnlinkProxyMedia()
results["LinkProxyMedia with an ffmpeg proxy"] = (item.LinkProxyMedia(proxy),
                                                  (item.GetClipProperty("Proxy"), item.GetClipProperty("Proxy Media Path")))
item.UnlinkProxyMedia()

# --- folder 'rename': new folder + MoveClips + DeleteFolders ------------------------------------------
old = mp.AddSubFolder(root, "ch19b_old_name")
mp.SetCurrentFolder(root)
moved = mp.MoveClips([pool[RAMP]], old)
new = mp.AddSubFolder(root, "ch19b_new_name")
moved2 = mp.MoveClips(old.GetClipList(), new)
gone = mp.DeleteFolders([old])
names = [f.GetName() for f in root.GetSubFolderList()]
results["folder rename emulated (new folder, move clips, delete old)"] = (
    moved and moved2 and gone and "ch19b_new_name" in names and "ch19b_old_name" not in names and len(new.GetClipList()) == 1,
    names)
mp.MoveClips(new.GetClipList(), root)
mp.DeleteFolders([new])

# --- render in place: render one clip's range, import, put it on a track above ------------------------
rip = fresh_timeline(p, "ch19b_render_in_place")
base = append(mp, rip, pool[C1], 0, 60)
comp = base.AddFusionComp()
mi, mo = comp.FindTool("MediaIn1"), comp.FindTool("MediaOut1")
glow = comp.AddTool("ofx.com.blackmagicdesign.resolvefx.Glow", -32768, -32768)
glow.ConnectInput("Source", mi)
mo.ConnectInput("Input", glow)
append(mp, rip, pool[C3], 60, 60)
r.OpenPage("deliver")
p.DeleteAllRenderJobs()
p.SetCurrentRenderFormatAndCodec("mov", "ProRes422HQ") or p.SetCurrentRenderFormatAndCodec("mp4", "H264")
s0 = rip.GetStartFrame()
p.SetRenderSettings({"SelectAllFrames": False, "MarkIn": s0, "MarkOut": s0 + 59, "TargetDir": OUT,
                     "CustomName": "ch19b_baked", "FormatWidth": 1920, "FormatHeight": 1080})
job = p.AddRenderJob()
p.StartRendering([job])
while p.IsRenderingInProgress():
    time.sleep(1)
r.OpenPage("edit")
baked = [os.path.join(OUT, f) for f in os.listdir(OUT) if f.startswith("ch19b_baked")]
results["render just the clip's range (MarkIn/MarkOut)"] = (bool(baked), baked)
if baked:
    bp = import_media(mp, [baked[0]])[baked[0]]
    rip.AddTrack("video")
    top = append(mp, rip, bp, 0, 60, track=2)
    results["baked clip length and position"] = (bp.GetClipProperty("Frames") in ("60", "60.0") and top.GetStart() == s0,
                                                  (bp.GetClipProperty("Frames"), top.GetStart() - s0))
    full = render(r, p, rip, "ch19b_render_in_place")
    results["baked file looks the same as the live Fusion effect"] = (
        Frame(baked[0], 1.0, 480, 270).diff(Frame(full, 1.0, 480, 270)) < 2.0,
        Frame(baked[0], 1.0, 480, 270).diff(Frame(full, 1.0, 480, 270)))

# --- fit to fill: 120 source frames into a 60-frame slot ----------------------------------------------
ff = fresh_timeline(p, "ch19b_fit_to_fill")
slot = append(mp, ff, pool[RAMP], 0, 60, src_start=0)
results["fit-to-fill via SetSpeed(src/slot*100)"] = (slot.SetSpeed({"Percentage": 120 / 60 * 100}), slot.GetDuration())
o = render(r, p, ff, "ch19b_fit_to_fill")
def src_frame(video, t):
    f = Frame(video, t, 640, 360)
    xs = [x for x in range(640) if sum(f.px(x, 180)) > 300]
    return None if not xs else round(sum(xs) / len(xs) / 2)
seen = [src_frame(o, t) for t in (0.0, 1.0, 1.95)]
results["fit-to-fill: last frame shows source frame ~118"] = (seen[2] is not None and abs(seen[2] - 118) <= 3, seen)

# --- replace edit: swap the media under a clip --------------------------------------------------------
rp = fresh_timeline(p, "ch19b_replace")
src_copy = os.path.join(OUT, "replace_me.mp4")
shutil.copy(C1, src_copy)
rp_item = import_media(mp, [src_copy])[src_copy]
placed = append(mp, rp, rp_item, 0, 60, src_start=30)
before_img = render(r, p, rp, "ch19b_replace_before")
ok = rp_item.ReplaceClip(C3)
after_img = render(r, p, rp, "ch19b_replace_after")
results["MediaPoolItem.ReplaceClip swaps media, keeps the cut"] = (
    ok and Frame(after_img, 1.0, 480, 270).diff(Frame(before_img, 1.0, 480, 270)) > 5 and placed.GetDuration() == 60,
    (ok, placed.GetDuration()))

# --- insert edit by merging two .drt files ------------------------------------------------------------
def unpack(drt, folder):
    shutil.rmtree(folder, ignore_errors=True)
    with zipfile.ZipFile(drt) as z:
        z.extractall(folder)
    return [os.path.join(folder, "SeqContainer", f) for f in os.listdir(os.path.join(folder, "SeqContainer"))]

target = fresh_timeline(p, "ch19b_insert_src")
append(mp, target, pool[C1], 0, 60)
append(mp, target, pool[GREY], 60, 60)
donor = fresh_timeline(p, "ch19b_insert_donor")
append(mp, donor, pool[C3], 0, 30, src_start=10)
t_drt, d_drt = os.path.join(OUT, "ch19b_target.drt"), os.path.join(OUT, "ch19b_donor.drt")
target.Export(t_drt, r.EXPORT_DRT, r.EXPORT_NONE)
donor.Export(d_drt, r.EXPORT_DRT, r.EXPORT_NONE)
s0, AT, N = target.GetStartFrame(), 60, 30
donor_xml = open(unpack(d_drt, os.path.join(OUT, "ch19b_donor"))[0], encoding="utf-8").read()
clip = re.search(r"\s*<Element>\s*<Sm2TiVideoClip DbId=.*?</Sm2TiVideoClip>\s*</Element>", donor_xml, re.S).group(0)
clip = re.sub(r'DbId="[0-9a-f-]+"', lambda _: f'DbId="{uuid.uuid4()}"', clip)
clip = re.sub(r"<Start>\d+</Start>", f"<Start>{s0 + AT}</Start>", clip, count=1)
tfile = unpack(t_drt, os.path.join(OUT, "ch19b_target"))[0]
x = open(tfile, encoding="utf-8").read()
# ripple: every item that starts at or after the insert point moves N frames later
x = re.sub(r"<Start>(\d+)</Start>", lambda m: f"<Start>{int(m.group(1)) + N}</Start>" if int(m.group(1)) >= s0 + AT else m.group(0), x)
first_video_items = x.index("<Items>", x.index("<Sm2TiTrack")) + len("<Items>")
x = x[:first_video_items] + clip + x[first_video_items:]
x = x.replace("<Name>ch19b_insert_src</Name>", "<Name>ch19b_insert</Name>")
open(tfile, "w", encoding="utf-8").write(x)
pj = os.path.join(OUT, "ch19b_target", "project.xml")
y = open(pj, encoding="utf-8").read()
open(pj, "w", encoding="utf-8").write(y.replace("<ProjectName>ch19b_insert_src</ProjectName>", "<ProjectName>ch19b_insert</ProjectName>"))
old = [p.GetTimelineByIndex(i) for i in range(1, p.GetTimelineCount() + 1) if p.GetTimelineByIndex(i).GetName() == "ch19b_insert"]
if old:
    mp.DeleteTimelines(old)
merged = os.path.join(OUT, "ch19b_insert.drt")
if os.path.exists(merged):
    os.remove(merged)
subprocess.run(["zip", "-q", "-r", merged, "."], cwd=os.path.join(OUT, "ch19b_target"), check=True)
ins = mp.ImportTimelineFromFile(merged)
if ins is None:
    report(results)
    raise SystemExit("insert .drt import failed (error dialog is open in Resolve)")
lay = sorted((i.GetStart() - ins.GetStartFrame(), i.GetDuration(), i.GetName()) for i in ins.GetItemListInTrack("video", 1))
results["insert edit: A 0-60 | X 60-90 | B pushed to 90-150"] = (
    lay == [(0, 60, "clip_1.mp4"), (60, 30, "clip_3.mp4"), (90, 60, "grey.mp4")], lay)

report(results)
