"""Chapter 21: HDR delivery (Rec.2100 PQ) and stereoscopic 3D clips, in their own project so the colour management
change never touches claude-davinci-tutorial."""
import json
import os
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, OUT, append, connect, fresh_timeline, import_media, open_project, report

r = connect()
p = open_project(r, "claude-davinci-hdr")
mp = p.GetMediaPool()
M = lambda f: os.path.join(MEDIA, f)
GREY, LEFT, RIGHT = M("grey.mp4"), M("eye_left.mp4"), M("eye_right.mp4")
# CreateStereoClip replaces its two inputs in the pool, so drop them first to make the script re-runnable, and use
# copies of the eye files as stand-alone references.
mp.DeleteClips([c for c in mp.GetRootFolder().GetClipList() if c.GetClipProperty("File Path") in (LEFT, RIGHT)])
REF_L, REF_R = os.path.join(OUT, "ch21_ref_left.mp4"), os.path.join(OUT, "ch21_ref_right.mp4")
os.makedirs(OUT, exist_ok=True)
for a, b in ((LEFT, REF_L), (RIGHT, REF_R)):
    shutil.copyfile(a, b)
pool = import_media(mp, [GREY, LEFT, RIGHT, REF_L, REF_R])
results = {}


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=codec_name,profile,pix_fmt,color_primaries,color_transfer,color_space,width,height",
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    return json.loads(out)["streams"][0]


def luma(path, seconds=1.0):
    """Mean 10-bit luma code of the centre 200x200, from the raw decoded plane (no colour conversion)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(seconds), "-i", path, "-frames:v", "1", "-vf",
                          "crop=200:200:860:440,format=gray10le", "-f", "rawvideo", "-"], capture_output=True).stdout
    vals = [raw[i] | raw[i + 1] << 8 for i in range(0, len(raw), 2)]
    return round(sum(vals) / len(vals))


def render_mov(tl, name, codec, extra=None):
    os.makedirs(OUT, exist_ok=True)
    p.SetCurrentTimeline(tl)
    r.OpenPage("deliver")
    p.DeleteAllRenderJobs()
    if not p.SetCurrentRenderFormatAndCodec("mov", codec):
        raise RuntimeError(f"mov/{codec} rejected")
    settings = {"SelectAllFrames": True, "TargetDir": OUT, "CustomName": name, "FormatWidth": 1920, "FormatHeight": 1080}
    settings.update(extra or {})
    ok = p.SetRenderSettings(settings)
    job = p.AddRenderJob()
    p.StartRendering([job])
    while p.IsRenderingInProgress():
        time.sleep(1)
    st = p.GetRenderJobStatus(job)
    r.OpenPage("edit")
    if st.get("CompletionPercentage") != 100:
        raise RuntimeError(f"render {name} failed: {st} (settings accepted: {ok})")
    return os.path.join(OUT, name + ".mov")


# --- 21.6 HDR: SDR source -> DaVinci Wide Gamut timeline -> Rec.2100 ST2084 (PQ) output ----------------------
sdr = {"colorScienceMode": "davinciYRGBColorManagedv2", "isAutoColorManage": "0", "separateColorSpaceAndGamma": "0",
       "colorSpaceInput": "Rec.709 Gamma 2.4", "colorSpaceTimeline": "Rec.709 Gamma 2.4",
       "colorSpaceOutput": "Rec.709 Gamma 2.4", "hdrMasteringOn": "0"}
for k, v in sdr.items():
    p.SetSetting(k, v)
tl = fresh_timeline(p, "ch21_hdr")
append(mp, tl, pool[GREY], 0, 60)
sdr_out = render_mov(tl, "ch21_sdr_reference", "H265", {"EncodingProfile": "Main10"})

hdr = {"colorSpaceTimeline": "DaVinci WG/Intermediate", "colorSpaceOutput": "Rec.2100 ST2084",
       "timelineWorkingLuminanceMode": "HDR 1000", "hdrMasteringOn": "1", "hdrMasteringLuminanceMax": "1000"}
applied = {k: (p.SetSetting(k, v), p.GetSetting(k)) for k, v in hdr.items()}
results["HDR project settings accepted"] = (all(a[0] and a[1] == hdr[k] for k, a in applied.items()), applied)
hdr_out = render_mov(tl, "ch21_hdr_pq", "H265", {"EncodingProfile": "Main10", "ColorSpaceTag": "Same as Project",
                                                 "GammaTag": "Same as Project"})
meta = probe(hdr_out)
results["HDR render is 10-bit HEVC tagged BT.2020 / SMPTE ST 2084"] = (
    meta.get("pix_fmt", "").endswith("10le") and meta.get("color_primaries") == "bt2020"
    and meta.get("color_transfer") == "smpte2084", meta)
# Mid-grey (code 128) is ~19 nits in SDR; in PQ that sits near 39 % of the signal range instead of 50 %.
codes = (luma(sdr_out), luma(hdr_out))
results["mid-grey moves from the SDR code to a PQ code"] = (codes[1] < codes[0] - 40, {"sdr 10-bit": codes[0],
                                                                                         "pq 10-bit": codes[1]})
for k, v in sdr.items():
    p.SetSetting(k, v)

# --- 21.7 Stereoscopic 3D -------------------------------------------------------------------------------------
stereo = mp.CreateStereoClip(pool[LEFT], pool[RIGHT])
results["CreateStereoClip returns a stereo MediaPoolItem"] = (stereo is not None,
                                                             stereo and stereo.GetClipProperty("Clip Name"))
tl = fresh_timeline(p, "ch21_stereo")
append(mp, tl, stereo, 0, 60)
out = render_mov(tl, "ch21_stereo_default", "H264")


def psnr_to(path, ref):
    o = subprocess.run(["ffmpeg", "-v", "info", "-ss", "1", "-i", path, "-ss", "1", "-i", ref, "-frames:v", "1",
                        "-lavfi", "[0]format=yuv420p[a];[1]format=yuv420p[b];[a][b]psnr", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(re.search(r"average:([\d.]+|inf)", o).group(1))


# References: each eye file rendered on its own through the same pipeline (so colour handling matches).
eyes = {}
for eye, src in (("left", REF_L), ("right", REF_R)):
    t = fresh_timeline(p, "ch21_eye_" + eye)
    append(mp, t, pool[src], 0, 60)
    eyes[eye] = psnr_to(out, render_mov(t, "ch21_eye_" + eye, "H264"))
results["stereo timeline renders the left eye by default"] = (eyes["left"] > 40 and eyes["right"] < 30, eyes)
results["GetStereoConvergenceValues on the stereo item"] = (True, tl.GetItemListInTrack("video", 1)[0]
                                                           .GetStereoConvergenceValues())
report(results)
