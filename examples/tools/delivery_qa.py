"""Whole-file delivery check for a finished render (docs 18.7). Plain python3 + ffmpeg/ffprobe, no Resolve needed:

    python3 examples/tools/delivery_qa.py out.mp4 [--target -14] [--json]

One line per check: PASS / WARN / FAIL. Exit code 1 if anything FAILs, else 0.
Checks: loudness + true peak, video vs audio length, tail fades to silence, dead air (frozen picture AND silence
at the same time), black flashes, dead borders (letterbox / pillarbox).
Ideas adapted from Hao0321/video-autopilot-kit (MIT); thresholds re-measured in docs 18.7.
"""
import argparse
import array
import json
import math
import re
import subprocess
import sys

LU_WARN, LU_FAIL = 1.0, 5.0        # distance from --target, LU
TP_WARN, TP_FAIL = -1.0, 0.0       # dBTP; above 0 the decoded file already clips
AV_WARN, AV_FAIL = 0.1, 0.4        # |video - audio| stream length, s
TAIL_SEC, TAIL_MAX_DB, TAIL_DROP = 0.1, -40.0, 20.0   # last 0.1 s: below -40 dBFS or 20 dB under the body
FREEZE_DB, FREEZE_SEC = -60, 2.0   # freezedetect noise / min length
SIL_DB, SIL_SEC = -35, 2.0         # silencedetect noise / min length
DEAD_AIR_SEC = 1.0                 # one overlap this long = dead air
LONG_SIL_SEC = 5.0                 # silence this long while the picture moves = WARN (intended, or lost audio?)
FLASH_SEC = 0.15                   # black run shorter than this (<= 4 frames at 30 fps) may be a flash
RAMP = 0.6                         # ... unless the frame next to it is already < 60% as bright as 3 frames earlier (a dip)
EDGE_SEC = 0.5                     # black at the very start/end is a fade in/out, not a flash
BORDER_PX = 16                     # both opposite edges darker than this many px = dead border
BORDER_SEC = 1.0                   # border must last this long to FAIL (shorter = WARN)
CROP_FPS = 2                       # cropdetect samples per second


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def probe(path):
    out = run(["ffprobe", "-v", "error",
               "-show_entries", "format=duration:stream=codec_type,duration,width,height,r_frame_rate",
               "-of", "json", path])
    if out.returncode:
        raise SystemExit(f"ffprobe cannot read {path}: {out.stderr.strip()}")
    j = json.loads(out.stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    if v is None:
        raise SystemExit(f"{path} has no video stream")
    dur = float(j["format"]["duration"])
    sdur = lambda s: float(s["duration"]) if s and "duration" in s else None
    num, den = v["r_frame_rate"].split("/")
    return {"duration": dur, "w": v["width"], "h": v["height"], "fps": float(num) / float(den),
            "v_dur": sdur(v), "a_dur": sdur(a), "audio": a is not None}


def pairs(text, key, end):
    """Pair `<key>_start: t` / `<key>_end: t` lines; a run still open at EOF closes at `end`
    (freezedetect prints no freeze_end when the picture stays frozen to the last frame)."""
    out, cur = [], None
    for kind, t in re.findall(key + r"_(start|end): ?([-\d.e+]+)", text):
        if kind == "start":
            cur = float(t)
        elif cur is not None:
            out.append((cur, float(t)))
            cur = None
    if cur is not None and end > cur:
        out.append((cur, end))
    return out


def analyse(path, info):
    """One decode pass: blackdetect + freezedetect on a small copy, cropdetect sampled at full size, silencedetect."""
    g = (f"[0:v]split[a][b];[a]scale=640:-2,blackdetect=d=0.02:pic_th=0.90,"
         f"freezedetect=n={FREEZE_DB}dB:d={FREEZE_SEC}[va];"
         f"[b]fps={CROP_FPS},cropdetect=limit=24:round=2:skip=0:reset=1[vb]")
    maps = ["-map", "[va]"]
    if info["audio"]:
        g += f";[0:a]silencedetect=noise={SIL_DB}dB:d={SIL_SEC}[aa]"
        maps += ["-map", "[aa]"]
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-filter_complex", g] + maps +
              ["-f", "null", "-", "-map", "[vb]", "-f", "null", "-"])
    if out.returncode:
        raise SystemExit("ffmpeg analysis failed: " + out.stderr[-400:])
    e = out.stderr
    blacks = [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.e+-]+) black_end:([\d.e+-]+)", e)]
    crops = [tuple(int(x) for x in m[:4]) + (float(m[4]),)
             for m in re.findall(r"x1:(-?\d+) x2:(-?\d+) y1:(-?\d+) y2:(-?\d+) .*? t:([\d.]+)", e)]
    return {"black": blacks, "freeze": pairs(e, "freeze", info["duration"]),
            "silence": pairs(e, "silence", info["duration"]) if info["audio"] else [], "crops": crops}


def loudness(path):
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-af", "loudnorm=print_format=json",
               "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", out.stderr)
    if not m:
        return None, None
    j = json.loads(m.group(0))
    return float(j["input_i"]), float(j["input_tp"])


def is_dip(path, a, b, fps):
    """True when the picture darkens into (or brightens out of) a short black run, like Dip To Color or a 3D flip.
    A gap in the timeline or a stray black frame cuts from full brightness straight to black and back."""
    pad = 5 / fps
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-copyts", "-ss", f"{max(0.0, a - pad):.3f}", "-t",
               f"{b - a + 2 * pad:.3f}", "-i", path, "-an", "-vf",
               "scale=320:-2,signalstats,metadata=mode=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"])
    ys = [(float(t), float(y)) for t, y in re.findall(r"pts_time:([\d.]+)[^\n]*\n[^\n]*YAVG=([\d.]+)", out.stderr)]
    before = [y for t, y in ys if t < a - 1e-3]
    after = [y for t, y in ys if t >= b - 1e-3]
    ramps = lambda seq: len(seq) >= 4 and seq[0] < RAMP * max(seq[1:4])   # seq[0] is the frame touching the black run
    return ramps(before[::-1]) or ramps(after)


def rms_db(path, start, dur):
    """Loudest channel's RMS between start and start+dur, dBFS (None when there is no audio there)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, start):.3f}", "-t", f"{dur:.3f}", "-i", path,
                          "-vn", "-ac", "2", "-ar", "48000", "-f", "s16le", "-"], capture_output=True).stdout
    a = array.array("h", raw)
    if not a:
        return None
    rms = [math.sqrt(sum(v * v for v in ch) / max(1, len(ch))) for ch in (a[0::2], a[1::2])]
    return round(20 * math.log10(max(rms) / 32768 + 1e-9), 1)


def overlap(xs, ys):
    return sorted((max(a, c), min(b, d)) for a, b in xs for c, d in ys if min(b, d) > max(a, c))


def border_runs(crops, blacks, w, h):
    """Time ranges where cropdetect finds dark bars on BOTH opposite edges (one dark side alone is just a dark scene)."""
    step, runs = 1.0 / CROP_FPS, []
    for x1, x2, y1, y2, t in crops:
        if x2 <= x1 or y2 <= y1 or any(a - 0.05 <= t <= b + 0.05 for a, b in blacks):
            continue   # all-black frame: cropdetect finds nothing to keep
        lr = min(x1, w - 1 - x2)
        tb = min(y1, h - 1 - y2)
        if lr > BORDER_PX or tb > BORDER_PX:
            px = f"{x1}/{w - 1 - x2} px left/right" if lr > BORDER_PX else f"{y1}/{h - 1 - y2} px top/bottom"
            if runs and t - runs[-1][1] <= step + 1e-6:
                runs[-1][1] = t
            else:
                runs.append([t, t, px])
    return [(a, b + step, px) for a, b, px in runs]


def fmt(ranges, n=6):
    s = ", ".join(f"{a:.2f}-{b:.2f}" for a, b, *_ in ranges[:n])
    return s + (f" (+{len(ranges) - n} more)" if len(ranges) > n else "")


def check(path, target):
    info = probe(path)
    res = []
    add = lambda name, status, detail, **data: res.append({"check": name, "status": status, "detail": detail, **data})
    d = info["duration"]
    an = analyse(path, info)

    if not info["audio"]:
        add("audio", "WARN", "no audio stream: loudness / tail / dead-air checks skipped")
    else:
        i, tp = loudness(path)
        if i is None:
            add("loudness", "FAIL", "loudnorm printed no measurement")
        elif i == float("-inf"):
            add("loudness", "WARN", "audio track is digital silence (-inf LUFS): fine for a test render, "
                                    "not for a delivery", lufs=None)
        else:
            off = abs(i - target)
            st = "FAIL" if off > LU_FAIL else "WARN" if off > LU_WARN else "PASS"
            add("loudness", st, f"{i:.1f} LUFS (target {target} ±{LU_WARN:g}, FAIL beyond ±{LU_FAIL:g})", lufs=i)
            st = "FAIL" if tp > TP_FAIL else "WARN" if tp > TP_WARN else "PASS"
            add("true peak", st, f"{tp:.1f} dBTP (WARN > {TP_WARN:g}, FAIL > {TP_FAIL:g} = clipping)", dbtp=tp)

        diff = abs((info["v_dur"] or d) - (info["a_dur"] or d))
        st = "FAIL" if diff > AV_FAIL else "WARN" if diff > AV_WARN else "PASS"
        add("A/V length", st, f"video {info['v_dur']} s, audio {info['a_dur']} s, diff {diff:.3f} s "
                              f"(WARN > {AV_WARN:g}, FAIL > {AV_FAIL:g})", diff=round(diff, 3))

        end = info["a_dur"] or d
        t, body = rms_db(path, end - TAIL_SEC, TAIL_SEC), rms_db(path, end - 4.0, 3.0)
        faded = t is None or t < TAIL_MAX_DB or (body is not None and t <= body - TAIL_DROP)
        add("tail fade", "PASS" if faded else "FAIL",
            f"last {TAIL_SEC:g} s of audio {t} dBFS vs {body} dBFS in the 3 s before the last second "
            f"(needs < {TAIL_MAX_DB:g} or {TAIL_DROP:g} dB quieter: faded out, not cut)", tail_db=t, body_db=body)

        dead = [r for r in overlap(an["freeze"], an["silence"]) if r[1] - r[0] >= DEAD_AIR_SEC]
        frozen = sum(b - a for a, b in an["freeze"])
        add("dead air", "FAIL" if dead else "PASS",
            (f"frozen + silent at {fmt(dead)} s" if dead else "no frozen-and-silent stretch") +
            f" (freeze alone is fine: {len(an['freeze'])} static runs, {frozen:.1f} s; "
            f"{len(an['silence'])} silent runs ≥ {SIL_SEC:g} s)",
            dead_air=[[round(a, 2), round(b, 2)] for a, b in dead])

        long_sil = [(a, b) for a, b in an["silence"] if b - a >= LONG_SIL_SEC]
        add("long silence", "WARN" if long_sil else "PASS",
            (f"silent at {fmt(long_sil)} s: intended, or audio lost in the render?" if long_sil
             else f"no silence ≥ {LONG_SIL_SEC:g} s"), silence=[[round(a, 2), round(b, 2)] for a, b in long_sil])

    flashes = [(a, b) for a, b in an["black"] if b - a < FLASH_SEC and a > EDGE_SEC and b < d - EDGE_SEC
               and not is_dip(path, a, b, info["fps"])]
    fades = [(a, b) for a, b in an["black"] if (a, b) not in flashes]
    add("black flash", "FAIL" if flashes else "PASS",
        (f"{len(flashes)} black flash(es) at {fmt(flashes)} s" if flashes else "no black flash") +
        (f"; {len(fades)} black run(s) treated as fades / dips: {fmt(fades)} s" if fades else ""),
        flashes=[[round(a, 3), round(b, 3)] for a, b in flashes], black=[[round(a, 3), round(b, 3)] for a, b in an["black"]])

    runs = border_runs(an["crops"], an["black"], info["w"], info["h"])
    long_runs = [r for r in runs if r[1] - r[0] >= BORDER_SEC]
    st = "FAIL" if long_runs else "WARN" if runs else "PASS"
    add("dead border", st, (f"dark bars at {fmt(runs)} s, e.g. {runs[0][2]}" if runs else "picture fills the frame") +
        f" (sampled {CROP_FPS}/s; FAIL when ≥ {BORDER_SEC:g} s)", borders=[[round(a, 2), round(b, 2), px] for a, b, px in runs])
    return info, res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--target", type=float, default=-14.0, help="integrated loudness target, LUFS (default -14)")
    ap.add_argument("--json", action="store_true", help="print one JSON object instead of text lines")
    a = ap.parse_args()
    info, res = check(a.video, a.target)
    worst = "FAIL" if any(r["status"] == "FAIL" for r in res) else "WARN" if any(r["status"] == "WARN" for r in res) else "PASS"
    if a.json:
        print(json.dumps({"file": a.video, "duration": info["duration"], "size": [info["w"], info["h"]],
                          "result": worst, "checks": res}, ensure_ascii=False, indent=1))
    else:
        print(f"{a.video}  {info['w']}x{info['h']}  {info['duration']:.2f} s")
        for r in res:
            print(r["status"], "|", r["check"], "|", r["detail"])
        print("RESULT", worst)
    sys.exit(1 if worst == "FAIL" else 0)


if __name__ == "__main__":
    main()
