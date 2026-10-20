"""Chapter 21: Studio-only AI features through the API — Super Scale, Speed Warp, Voice Isolation, Dialogue Leveler.
Every result is measured on the rendered file against a reference made by make_media.sh."""
import array
import math
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import MEDIA, OUT, append, connect, fresh_timeline, import_media, open_project, render, report

r = connect()
p = open_project(r)
mp = p.GetMediaPool()
M = lambda f: os.path.join(MEDIA, f)
SMALL, PHOTO, DISC, GREY, NOISY = M("ss_small.mp4"), M("ss_photo_lo.mp4"), M("moving_disc.mp4"), M("grey.mp4"), M("voice_noisy.wav")
pool = import_media(mp, [SMALL, PHOTO, DISC, GREY, NOISY])
results = {}


def ssim(video, seconds, ref_png, size="1920:1080"):
    out = subprocess.run(["ffmpeg", "-v", "info", "-ss", str(seconds), "-i", video, "-i", ref_png, "-frames:v", "1",
                          "-lavfi", f"[0]scale={size}:flags=area,format=rgb24[a];[1]format=rgb24[b];[a][b]ssim",
                          "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.search(r"All:([\d.]+)", out).group(1))


def psnr(video, ref_video):
    out = subprocess.run(["ffmpeg", "-v", "info", "-i", video, "-i", ref_video,
                          "-lavfi", "[0]format=yuv420p[a];[1]format=yuv420p[b];[a][b]psnr", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.search(r"average:([\d.]+|inf)", out).group(1))


def pcm(path, start=0.0, dur=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", path, "-vn", "-ac", "1", "-ar", "48000", "-f", "s16le", "-"]
    if dur:
        cmd[5:5] = ["-t", str(dur)]
    return array.array("h", subprocess.run(cmd, capture_output=True, check=True).stdout)


def db(x):
    return 20 * math.log10(math.sqrt(sum(v * v for v in x) / max(1, len(x))) / 32768 + 1e-9)


# --- 21.1 Super Scale -------------------------------------------------------------------------------------
# Clips at one third of the reference size, upscaled 3x by the timeline. Super Scale is a MediaPoolItem clip attribute.
# The photo reference is a 1278x720 crop of the original, so its render is scaled back down to 1278x720 to compare.
for name, src, ref, size in [("pattern", SMALL, M("ss_ref.png"), "1920:1080"),
                             ("photo", PHOTO, M("ss_photo_ref.png"), "1278:720")]:
    item = pool[src]
    scores = {}
    # (2, 0.5, 0.5) is '2x Enhanced' (sharpness, noise reduction), the only 4-argument form. Those two values stick to
    # the clip: a later plain 2x renders identically to 2x Enhanced, and 4x renders differently before and after.
    for label, args in [("off", (1,)), ("2x enhanced", (2, 0.5, 0.5)), ("2x after enhanced", (2,)),
                        ("4x after enhanced", (4,))]:
        ok = item.SetClipProperty("Super Scale", *args)
        tl = fresh_timeline(p, f"ch21_superscale_{name}")
        append(mp, tl, item, 0, 60)
        out = render(r, p, tl, f"ch21_superscale_{name}_" + label.replace(" ", "_"))
        scores[label] = (ok, item.GetClipProperty("Super Scale"), ssim(out, 1.0, ref, size))
    item.SetClipProperty("Super Scale", 1)
    results[f"Super Scale ({name}): best of 2x Enhanced / 4x beats off on SSIM vs full-res reference"] = (
        all(v[0] for v in scores.values())
        and max(scores["4x after enhanced"][2], scores["2x enhanced"][2]) > scores["off"][2] + 0.01, scores)
    results[f"Super Scale ({name}): plain 2x keeps the earlier Enhanced sharpness / noise reduction"] = (
        scores["2x after enhanced"][2] == scores["2x enhanced"][2], scores["2x after enhanced"][2])

# --- 21.2 Speed Warp ----------------------------------------------------------------------------------------
# 30 source frames at 25 % fill 120 timeline frames (only with RippleTimeline: without it the clip keeps its
# 30-frame length and shows source frames 0-7). The reference is the same synthetic scene rendered natively
# at 120 fps (the disc moves 4 px per frame), played back at 30 fps: a perfect slow motion.
ref = os.path.join(OUT, "ch21_speed_ref.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=120:d=1", "-f", "lavfi",
                "-i", "color=c=white:s=160x160:r=120:d=1", "-filter_complex",
                "[1]format=yuva420p,geq=lum='255':a='if(lt(hypot(X-80,Y-80),80),255,0)'[d];[0]hue=s=0.3[b];"
                "[b][d]overlay=x='100+4*n':y=460,format=yuv420p,setpts=N/30/TB", "-r", "30", "-c:v", "libx264",
                "-crf", "12", ref], check=True)
methods = {"nearest": (r.RETIME_NEAREST, r.MOTION_EST_USE_PROJECT),
           "frame blend": (r.RETIME_FRAME_BLEND, r.MOTION_EST_USE_PROJECT),
           "optical flow enhanced": (r.RETIME_OPTICAL_FLOW, r.MOTION_EST_ENHANCED_BETTER),
           "speed warp": (r.RETIME_OPTICAL_FLOW, r.MOTION_EST_SPEED_WARP_BETTER)}
scores = {}
for label, (proc, est) in methods.items():
    tl = fresh_timeline(p, "ch21_speedwarp")
    it = append(mp, tl, pool[DISC], 0, 30)
    sp = it.SetSpeed({"Percentage": 25.0, "RippleTimeline": True})
    props = it.SetProperties({"RetimeProcess": proc, "MotionEstimation": est})
    back = (it.GetProperty("RetimeProcess"), it.GetProperty("MotionEstimation"), it.GetDuration())
    scores[label] = round(psnr(render(r, p, tl, "ch21_speed_" + label.replace(" ", "_"), timeout=900), ref), 2)
    results[f"Retime {label}: properties accepted"] = (sp and props and back[2] == 120, back)
results["Speed Warp beats nearest and frame blend (PSNR vs native 120 fps)"] = (
    scores["speed warp"] > max(scores["nearest"], scores["frame blend"]), scores)

# --- 21.3 Voice Isolation and Dialogue Leveler --------------------------------------------------------------
# Speech with 1.5-s pauses over pink noise. Noise floor = level inside the pauses; speech = level elsewhere.
clean = pcm(M("voice_clean.wav"))
win = 4800
quiet = [i for i in range(0, len(clean) - win, win) if db(clean[i:i + win]) < -60]


def floor_and_speech(path):
    a = pcm(path)
    q = set(quiet)
    gap = [v for i in quiet for v in a[i:i + win]]
    loud = [v for i in range(0, len(clean) - win, win) if i not in q and db(clean[i:i + win]) > -30 for v in a[i:i + win]]
    return round(db(gap), 1), round(db(loud), 1)


audio_len = int(len(clean) / 48000 * 30)
for label, props in [("off", {}),
                     ("voice isolation 100", {"AudioVoiceIsolationEnabled": True, "AudioVoiceIsolationAmount": 100}),
                     ("dialogue leveler", {"AudioDialogueLevelerEnabled": True})]:
    tl = fresh_timeline(p, "ch21_voice")
    append(mp, tl, pool[GREY], 0, min(240, audio_len))
    a = append(mp, tl, pool[NOISY], 0, audio_len, media_type=2)
    ok = a.SetProperties(props) if props else True
    state = a.GetVoiceIsolationState()
    nf, sp_db = floor_and_speech(render(r, p, tl, "ch21_voice_" + label.replace(" ", "_")))
    results[f"audio {label}"] = (ok, {"noise floor dB": nf, "speech dB": sp_db, "snr": round(sp_db - nf, 1),
                                      "GetVoiceIsolationState": state})
off_snr = results["audio off"][1]["snr"]
vi_snr = results["audio voice isolation 100"][1]["snr"]
results["Voice Isolation raises speech-to-noise by > 10 dB"] = (vi_snr - off_snr > 10, (off_snr, vi_snr))

report(results)
