"""Compare the cuts in a rendered file with the planned cut list (docs 16.10). Plain python3 + ffmpeg/ffprobe:

    python3 examples/tools/cut_check.py out.mp4 plan.json [--key kick] [--frames] [--offset 0] [--json]

plan.json may be
  - a list of seconds            [3.0, 3.5, 4.0]          (--frames: the numbers are frame offsets instead)
  - cuts.json from 16_beats.py   {"kick": [...], ...}     (pick the list with --key)
  - a segment plan (16.9)        [{"start": 90, "dur": 15}, ...]   (start = frame offset from the timeline start)
Planned times are rounded to frames with round(t * fps) (docs 16.5); --offset adds seconds (the song starts later).
Hard cuts only: ffmpeg's scene score barely moves during a dissolve, so a dissolve shows up as a missed cut.
Exit code 1 when a planned cut is missed or more than --tol frames off; extra cuts are a WARN.
"""
import argparse
import json
import re
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def fps_and_duration(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=r_frame_rate:format=duration", "-of", "json", path])
    if out.returncode:
        raise SystemExit(f"ffprobe cannot read {path}: {out.stderr.strip()}")
    j = json.loads(out.stdout)
    num, den = j["streams"][0]["r_frame_rate"].split("/")
    return float(num) / float(den), float(j["format"]["duration"])


def detect(path, fps, threshold):
    """Frame numbers where the scene score jumps above threshold (the first frame of each new shot)."""
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-an", "-vf",
               f"scale=480:-2,select='gt(scene,{threshold})',showinfo", "-f", "null", "-"])
    if out.returncode:
        raise SystemExit("ffmpeg scene detection failed: " + out.stderr[-400:])
    return sorted({round(float(t) * fps) for t in re.findall(r"Parsed_showinfo.*?pts_time:([\d.]+)", out.stderr)})


def load_plan(path, key, frames, fps, offset):
    j = json.load(open(path, encoding="utf-8"))
    if isinstance(j, dict):
        if key is None:
            raise SystemExit(f"{path} is a dict; choose a list with --key ({', '.join(k for k, v in j.items() if isinstance(v, list))})")
        j = j[key]
    if j and isinstance(j[0], dict):
        return sorted({int(x["start"]) + round(offset * fps) for x in j})
    return sorted({(round(x) if frames else round(x * fps)) + round(offset * fps) for x in j})


def match(planned, found, tol, window):
    """Pair planned and detected cuts. Pass 1 takes every pair within `tol`, pass 2 pairs the leftovers within
    `window` frames; otherwise one wrong planned cut steals its neighbour's detection and every later cut looks late."""
    free, rows = list(found), {}
    for limit in (tol, window):
        for p in planned:
            if p in rows:
                continue
            near = min(free, key=lambda f: abs(f - p), default=None)
            if near is not None and abs(near - p) <= limit:
                free.remove(near)
                d = near - p
                rows[p] = {"planned": p, "found": near, "delta": d,
                           "status": "ok" if abs(d) <= tol else "late" if d > 0 else "early"}
    for p in planned:
        rows.setdefault(p, {"planned": p, "found": None, "delta": None, "status": "missed"})
    return [rows[p] for p in planned], free


def pacing(found, total, rule):
    """Shots longer than the cap for the section they sit in. rule: '0-30:7,30-180:15,180-:30' (seconds)."""
    caps = []
    for part in rule.split(","):
        span, cap = part.split(":")
        a, b = span.split("-")
        caps.append((float(a), float(b) if b else None, float(cap)))
    edges = [0.0] + found + [total]
    long_shots = []
    for a, b in zip(edges, edges[1:]):
        mid = (a + b) / 2
        cap = next((c for lo, hi, c in caps if mid >= lo and (hi is None or mid < hi)), caps[-1][2])
        if b - a > cap:
            long_shots.append({"start": round(a, 2), "end": round(b, 2), "length": round(b - a, 2), "cap": cap})
    return long_shots


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("plan")
    ap.add_argument("--key", help="which list to use when plan.json is a dict (cuts.json: kick, high)")
    ap.add_argument("--frames", action="store_true", help="plan numbers are frame offsets, not seconds")
    ap.add_argument("--offset", type=float, default=0.0, help="seconds added to every planned time")
    ap.add_argument("--tol", type=int, default=1, help="allowed error, frames (default 1)")
    ap.add_argument("--window", type=float, default=0.5, help="search radius for a planned cut, seconds (default 0.5)")
    ap.add_argument("--threshold", type=float, default=0.3, help="ffmpeg scene score for a cut (default 0.3)")
    ap.add_argument("--max-shot", metavar="RULE",
                    help="UNVERIFIED pacing caps, e.g. '0-30:7,30-180:15,180-:30' = longest shot (s) per section; "
                         "Hao0321/video-autopilot-kit starter values, not measured here")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    fps, total = fps_and_duration(a.video)
    last = round(total * fps)
    planned = [p for p in load_plan(a.plan, a.key, a.frames, fps, a.offset) if 0 < p < last]
    found = [f for f in detect(a.video, fps, a.threshold) if f > 0]
    rows, extra = match(planned, found, a.tol, round(a.window * fps))
    bad = [r for r in rows if r["status"] != "ok"]
    rep = {"file": a.video, "fps": fps, "planned": len(planned), "detected": len(found),
           "ok": len(rows) - len(bad), "missed": [r["planned"] for r in rows if r["status"] == "missed"],
           "off": [r for r in rows if r["status"] in ("late", "early")], "extra": extra, "rows": rows}
    if a.max_shot:
        rep["long_shots_unverified"] = pacing([f / fps for f in found], total, a.max_shot)
    result = "FAIL" if bad else "WARN" if extra or rep.get("long_shots_unverified") else "PASS"
    rep["result"] = result

    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        sec = lambda f: f"{f / fps:.3f}s(f{f})"
        print(f"{a.video}  {fps:g} fps  planned {len(planned)}  detected {len(found)}  within ±{a.tol} frame: {rep['ok']}")
        print("PASS" if not rep["missed"] else "FAIL", "| missed |", ", ".join(sec(f) for f in rep["missed"]) or "none")
        print("PASS" if not rep["off"] else "FAIL", "| late/early |",
              ", ".join(f"{sec(r['planned'])} found {r['delta']:+d} frames ({r['status']})" for r in rep["off"]) or "none")
        print("PASS" if not extra else "WARN", "| extra (cut not in the plan) |", ", ".join(sec(f) for f in extra) or "none")
        if a.max_shot:
            ls = rep["long_shots_unverified"]
            print("PASS" if not ls else "WARN", "| shot length caps (UNVERIFIED starter values) |",
                  ", ".join(f"{s['start']}-{s['end']}s = {s['length']}s > {s['cap']:g}s" for s in ls) or "none")
        print("RESULT", result)
    sys.exit(1 if result == "FAIL" else 0)


if __name__ == "__main__":
    main()
