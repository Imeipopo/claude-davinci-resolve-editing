"""Check an .srt before it goes on a timeline or into a burn-in (docs 19.15). Plain python3 (+ ffmpeg for --media):

    python3 examples/tools/caption_qa.py captions.srt [--media out.mp4 | --duration 61.5] [--asr 8] [--json]

Checks: every cue parses; no reversed times, overlaps or out-of-order cues; cues end inside the media; minimum cue
length; reading speed of Chinese cues (characters per second, punctuation not counted).
--asr N (needs --media): transcribe N evenly spaced cues with whisper-cli and check that the caption text is
really spoken there. For SPEECH captions only. Song lyrics: Whisper's word times are 0.8-1 s off (docs 16.7).
Reading-speed and length limits are starter values from Hao0321/video-autopilot-kit, not measured here.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata

CPS_WARN, CPS_FAIL = 5.0, 7.0     # Chinese characters per second (unverified starter values)
MIN_DUR = 0.7                     # s, shorter cue = WARN (unverified)
END_SLACK = 0.04                  # s a cue may run past the end of the media (about one frame)
ASR_MIN = 0.5                     # share of caption characters that must be heard
ASR_PAD = 0.25                    # s of audio added on each side of a cue
WHISPER = "/opt/homebrew/bin/whisper-cli"
MODEL = os.path.expanduser("~/Library/Application Support/superwhisper/ggml-large-v3-turbo.bin")
CJK = re.compile(r"[㐀-䶿一-鿿぀-ヿ가-힯]")


def parse(path):
    """[(index, start, end, text)], [unparsable block numbers]."""
    ts = r"(\d+):(\d\d):(\d\d)[,.](\d{1,3})"
    sec = lambda h, m, s, ms: int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000
    cues, bad = [], []
    blocks = re.split(r"\n\s*\n", open(path, encoding="utf-8-sig").read().replace("\r\n", "\n").strip())
    for n, b in enumerate(blocks, 1):
        lines = b.strip().splitlines()
        k = next((i for i, l in enumerate(lines) if "-->" in l), None)
        m = re.match(ts + r"\s*-->\s*" + ts, lines[k].strip()) if k is not None else None
        if not m:
            bad.append(n)
            continue
        g = m.groups()
        cues.append((n, sec(*g[:4]), sec(*g[4:]), "\n".join(lines[k + 1:]).strip()))
    return cues, bad


def chars(text):
    """Characters a viewer reads: no whitespace, punctuation or symbols; drop <i>-style tags."""
    text = re.sub(r"<[^>]+>|\{[^}]*\}", "", text)
    return [c for c in text if not c.isspace() and not unicodedata.category(c).startswith(("P", "S"))]


def media_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True)
    if out.returncode or not out.stdout.strip():
        raise SystemExit(f"ffprobe cannot read {path}")
    return float(out.stdout)


def heard_share(caption, heard):
    """Share of the caption's characters that appear, in order, in what Whisper heard."""
    a, b = "".join(chars(caption)).lower(), "".join(chars(heard)).lower()
    if not a:
        return 1.0
    return sum(m.size for m in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks()) / len(a)


def transcribe(media, s, e, lang, prompt, tmp):
    wav = os.path.join(tmp, "cue.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, s - ASR_PAD):.3f}", "-t",
                    f"{e - s + 2 * ASR_PAD:.3f}", "-i", media, "-vn", "-ar", "16000", "-ac", "1", wav], check=True)
    cmd = [WHISPER, "-m", MODEL, "-l", lang, "-nt", "-np", "-f", wav] + (["--prompt", prompt] if prompt else [])
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if out.returncode:
        raise SystemExit("whisper-cli failed: " + out.stderr[-300:])
    return out.stdout.strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("srt")
    ap.add_argument("--media", help="video/audio the captions belong to (length check, --asr)")
    ap.add_argument("--duration", type=float, help="media length in seconds, instead of --media")
    ap.add_argument("--asr", type=int, default=0, metavar="N", help="spot-check N cues with whisper-cli")
    ap.add_argument("--lang", default="zh", help="whisper language (default zh)")
    ap.add_argument("--prompt", default="以下是繁體中文。",
                    help="whisper initial prompt; without it zh comes back in simplified characters")
    ap.add_argument("--cps-warn", type=float, default=CPS_WARN)
    ap.add_argument("--cps-fail", type=float, default=CPS_FAIL)
    ap.add_argument("--min-dur", type=float, default=MIN_DUR)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    cues, bad = parse(a.srt)
    res = []
    add = lambda name, status, detail, **data: res.append({"check": name, "status": status, "detail": detail, **data})
    label = lambda c: f"#{c[0]} {c[1]:.2f}s"
    add("parse", "FAIL" if bad or not cues else "PASS",
        f"{len(cues)} cues" + (f"; unreadable blocks {bad}" if bad else ""), unreadable=bad)

    rev = [c for c in cues if c[2] <= c[1]]
    over = [(p, c) for p, c in zip(cues, cues[1:]) if c[1] < p[2] - 0.0005]
    order = [(p, c) for p, c in zip(cues, cues[1:]) if c[1] < p[1]]
    probs = [f"{label(c)} ends before it starts" for c in rev] + \
            [f"{label(c)} starts before {label(p)} ends ({p[2]:.3f})" for p, c in over if (p, c) not in order] + \
            [f"{label(c)} is earlier than the cue before it" for p, c in order]
    add("timing order", "FAIL" if probs else "PASS", "; ".join(probs[:6]) or "no reversed, overlapping or "
                                                                            "out-of-order cues", problems=probs)

    short = [c for c in cues if 0 < c[2] - c[1] < a.min_dur]
    add("min length (unverified limit)", "WARN" if short else "PASS",
        ", ".join(f"{label(c)} {c[2] - c[1]:.2f}s" for c in short[:6]) or f"all cues ≥ {a.min_dur:g} s")

    speeds = []
    for c in cues:
        ch = chars(c[3])
        if ch and c[2] > c[1] and sum(bool(CJK.match(x)) for x in ch) * 2 >= len(ch):   # mostly Chinese/Japanese/Korean
            speeds.append((c, len(ch), len(ch) / (c[2] - c[1])))
    fast = [s for s in speeds if s[2] > a.cps_warn]
    worst = max((s[2] for s in speeds), default=0)
    st = "FAIL" if any(s[2] > a.cps_fail for s in fast) else "WARN" if fast else "PASS"
    add("reading speed (unverified limits)", st,
        (", ".join(f"{label(c)} {n} chars {v:.1f}/s" for c, n, v in sorted(fast, key=lambda s: -s[2])[:6]) or
         f"{len(speeds)} Chinese cues, fastest {worst:.1f} chars/s") + f" (WARN > {a.cps_warn:g}, FAIL > {a.cps_fail:g})",
        fastest=round(worst, 2), median=round(sorted(s[2] for s in speeds)[len(speeds) // 2], 2) if speeds else None)

    dur = media_duration(a.media) if a.media else a.duration
    if dur is not None:
        out = [c for c in cues if c[2] > dur + END_SLACK]
        add("inside media", "FAIL" if out else "PASS",
            ", ".join(f"{label(c)} ends {c[2]:.2f}s" for c in out[:6]) + f" > media {dur:.2f}s" if out
            else f"last cue ends {max((c[2] for c in cues), default=0):.2f}s, media {dur:.2f}s")

    if a.asr:
        if not a.media:
            raise SystemExit("--asr needs --media")
        pick = sorted({round(i * (len(cues) - 1) / max(1, a.asr - 1)) for i in range(min(a.asr, len(cues)))})
        rows = []
        with tempfile.TemporaryDirectory() as tmp:
            for i in pick:
                n, s, e, txt = cues[i]
                heard = transcribe(a.media, s, e, a.lang, a.prompt, tmp)
                rows.append({"cue": n, "start": s, "caption": txt, "heard": heard, "share": round(heard_share(txt, heard), 2)})
        miss = [r for r in rows if r["share"] < ASR_MIN]
        add("ASR spot-check", "FAIL" if miss else "PASS",
            f"{len(rows)} cues, lowest share heard {min(r['share'] for r in rows):.2f} (needs ≥ {ASR_MIN:g})" +
            "".join(f"; #{r['cue']} {r['start']:.2f}s caption 「{r['caption']}」 heard 「{r['heard']}」" for r in miss[:4]),
            samples=rows)

    worst = "FAIL" if any(r["status"] == "FAIL" for r in res) else "WARN" if any(r["status"] == "WARN" for r in res) else "PASS"
    if a.json:
        print(json.dumps({"file": a.srt, "cues": len(cues), "result": worst, "checks": res}, ensure_ascii=False, indent=1))
    else:
        for r in res:
            print(r["status"], "|", r["check"], "|", r["detail"])
        print("RESULT", worst)
    sys.exit(1 if worst == "FAIL" else 0)


if __name__ == "__main__":
    main()
