"""Shared helpers for the examples. Run every example with Resolve's bundled interpreter:

    "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Applications/ResolvePython" examples/<script>.py

Resolve Studio must be running with Preferences > System > General > External scripting = Local.
"""
import os
import subprocess
import time

import DaVinciResolveScript as dvr

HERE = os.path.dirname(os.path.abspath(__file__))
MEDIA = os.path.join(HERE, "media")
OUT = os.path.join(HERE, "out")
PROJECT = "claude-davinci-tutorial"
FPS = 30


def connect():
    r = dvr.scriptapp("Resolve")
    if r is None:
        raise RuntimeError("Resolve not reachable: is Resolve Studio running with External scripting = Local?")
    return r


def open_project(r, name=PROJECT):
    pm = r.GetProjectManager()
    cur = pm.GetCurrentProject()
    if cur and cur.GetName() not in (name, "Untitled Project"):
        # Switching projects discards unsaved changes in the current one. Never save the untitled startup
        # project: that opens a "Save current project" name dialog which blocks every later call (docs 2.1).
        pm.SaveProject()
    p = pm.LoadProject(name) or pm.CreateProject(name)
    if not p or p.GetName() != name:
        raise RuntimeError(f"could not open project {name}")
    # timelineFrameRate only sticks before the project has a timeline; timelinePlaybackFrameRate never does.
    for k, v in {"timelineResolutionWidth": "1920", "timelineResolutionHeight": "1080",
                 "timelineFrameRate": str(FPS)}.items():
        p.SetSetting(k, v)
    if float(p.GetSetting("timelineFrameRate")) != FPS:
        raise RuntimeError(f"project {name} is not {FPS} fps; create a fresh project")
    return p


def import_media(mp, paths):
    pool = {c.GetClipProperty("File Path"): c for c in mp.GetRootFolder().GetClipList()}
    missing = [x for x in paths if x not in pool]
    for c in (mp.ImportMedia(missing) or []) if missing else []:
        pool[c.GetClipProperty("File Path")] = c
    absent = [x for x in paths if x not in pool]
    if absent:
        raise RuntimeError(f"import failed: {absent}")
    return pool


def fresh_timeline(p, name):
    """CreateEmptyTimeline returns None when the name exists, so delete the old one first."""
    mp = p.GetMediaPool()
    old = [p.GetTimelineByIndex(i) for i in range(1, p.GetTimelineCount() + 1)
           if p.GetTimelineByIndex(i).GetName() == name]
    if old:
        mp.DeleteTimelines(old)
    tl = mp.CreateEmptyTimeline(name)
    if not tl:
        raise RuntimeError(f"CreateEmptyTimeline({name}) failed")
    p.SetCurrentTimeline(tl)
    return tl


def append(mp, tl, item, offset, length, track=1, src_start=0, media_type=1):
    """Place `length` frames of `item` at `offset` frames from the timeline start. endFrame is exclusive."""
    s = tl.GetStartFrame()
    res = mp.AppendToTimeline([{"mediaPoolItem": item, "startFrame": src_start, "endFrame": src_start + length,
                                "trackIndex": track, "recordFrame": s + offset, "mediaType": media_type}])
    if not res:
        raise RuntimeError("AppendToTimeline failed")
    return res[0]


def timecode(tl, offset):
    f = tl.GetStartFrame() + offset
    return "%02d:%02d:%02d:%02d" % (f // FPS // 3600, f // FPS // 60 % 60, f // FPS % 60, f % FPS)


def render(r, p, tl, name, timeout=300):
    """Render the whole timeline to examples/out/<name>.mp4 and return the path."""
    os.makedirs(OUT, exist_ok=True)
    p.SetCurrentTimeline(tl)
    r.OpenPage("deliver")
    p.DeleteAllRenderJobs()
    if not p.SetCurrentRenderFormatAndCodec("mp4", "H264"):
        raise RuntimeError("SetCurrentRenderFormatAndCodec failed (a modal dialog may be blocking Resolve)")
    p.SetRenderSettings({"SelectAllFrames": True, "TargetDir": OUT, "CustomName": name,
                         "FormatWidth": 1920, "FormatHeight": 1080})
    job = p.AddRenderJob()
    p.StartRendering([job])
    t0 = time.time()
    while p.IsRenderingInProgress():
        if time.time() - t0 > timeout:
            # StopRendering() does not unstick a hung Fusion frame (docs 11.6); stop here and report.
            raise RuntimeError(f"render of {name} still running after {timeout}s")
        time.sleep(1)
    status = p.GetRenderJobStatus(job)
    r.OpenPage("edit")
    if status.get("CompletionPercentage") != 100:
        raise RuntimeError(f"render failed: {status}")
    return os.path.join(OUT, name + ".mp4")


def grab(video, seconds, png):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(seconds), "-i", video, "-frames:v", "1", png], check=True)
    return png


def duration(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


class Frame:
    """One decoded RGB frame (no numpy needed: ResolvePython has no pip)."""

    def __init__(self, video, seconds, w=1920, h=1080):
        self.w, self.h = w, h
        self.buf = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(seconds), "-i", video, "-frames:v", "1",
                                   "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                  capture_output=True, check=True).stdout

    def px(self, x, y):
        i = (y * self.w + x) * 3
        return tuple(self.buf[i:i + 3])

    def mean(self, x0=0, y0=0, x1=None, y1=None, step=4):
        x1, y1 = x1 or self.w, y1 or self.h
        acc, n = [0, 0, 0], 0
        for y in range(y0, y1, step):
            for x in range(x0, x1, step):
                p = self.px(x, y)
                acc[0] += p[0]; acc[1] += p[1]; acc[2] += p[2]; n += 1
        return tuple(round(a / n, 1) for a in acc)

    def bright_box(self, thresh=128, step=2):
        """Bounding box (x0, y0, x1, y1) of pixels brighter than thresh, or None."""
        xs, ys = [], []
        for y in range(0, self.h, step):
            for x in range(0, self.w, step):
                if sum(self.px(x, y)) / 3 > thresh:
                    xs.append(x); ys.append(y)
        return (min(xs), min(ys), max(xs), max(ys)) if xs else None

    def diff(self, other, step=4):
        d, n = 0, 0
        for y in range(0, self.h, step):
            for x in range(0, self.w, step):
                a, b = self.px(x, y), other.px(x, y)
                d += abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]); n += 3
        return round(d / n, 2)


def report(results):
    for k, (ok, detail) in results.items():
        print("PASS" if ok else "FAIL", "|", k, "|", detail)
