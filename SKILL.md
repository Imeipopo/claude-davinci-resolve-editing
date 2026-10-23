---
name: davinci-resolve-scripting
description: Drive DaVinci Resolve Studio from Python — build timelines, place clips frame-accurately, add transitions/titles/Fusion effects/color, and render. Use when the user wants Claude to edit, assemble, or automate a video in DaVinci Resolve, or asks what the Resolve scripting API can or cannot do.
---

# DaVinci Resolve scripting

Verified on macOS 27.0.1 + DaVinci Resolve Studio 21.1.0.14. Windows/Linux/free edition untested.
The full rule list with evidence is in `AGENTS.md`; chapter docs are in `docs/zh-TW/` and `docs/en/`.

## Workflow

1. Confirm Resolve Studio is running and External scripting = Local:
   `"/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Applications/ResolvePython" -c 'import DaVinciResolveScript as d; print(d.scriptapp("Resolve").GetVersionString())'`
2. Read the authoritative signatures in `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/DaVinciResolveScript.pyi` before calling anything unfamiliar.
3. Write a `.py` script (reuse `examples/common.py`): open project (save the current one first), create a **new** timeline per revision, place clips with absolute `recordFrame`, render.
4. Verify by rendering and extracting frames with ffmpeg. Do not trust API return values alone. Before delivery run `examples/tools/delivery_qa.py` (and `cut_check.py` for beat edits, `caption_qa.py` for .srt).
5. Report what the rendered output shows, including anything that did not work.

## Must-know traps

- `recordFrame` is absolute (timeline starts at frame 108000 at 30 fps); `endFrame` is exclusive.
- Stills always land as 150 frames — convert stills to video clips first (non-16:9: blurred fill, docs 2.6).
- Numeric file names import as an image sequence.
- A modal dialog makes every later API call return None silently; dismiss it with Esc via System Events.
- `ResolvePython` does not add the script directory to `sys.path`.
- None from basic calls can also mean a render is still running — check `IsRenderingInProgress()`. Keep the Mac awake (`caffeinate -dimsu`) for long runs.
- `InsertFusionTitleIntoTimeline` inserts on V1 and ripples the timeline; build titles in a sub-timeline or inside a transparent placeholder's Fusion comp instead.
- Resolve FX inside Fusion take their image on `Source`, not `Input`.
- To move/trim existing clips, export `.drt`, patch, re-import (lossless). FCPXML/OTIO round trips lose effects.
- `SetLUT` only accepts paths relative to the master LUT folder. `ApplyGradeFromDRX`'s return value is unreliable — verify by rendering.
- If you must click Resolve's UI, post real CGEvent mouse events (`examples/tools/click.swift`); AppleScript `click at` often only hovers.
- Jump cuts for talking heads: `examples/22_jumpcut.py` (silencedetect -> keep ranges -> new timeline, .srt remapped). Never re-make a source file under the same name.
- For motion-designed intros, render them outside Resolve (`examples/20_intro_generator`, docs ch 20) at the timeline frame rate, stereo audio; overlays as ProRes 4444 on an added V2.
