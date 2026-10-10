# AGENTS.md — driving DaVinci Resolve Studio from code

Rules for AI agents (Codex, Claude Code, others) that control DaVinci Resolve through its Python scripting API.
Verified on macOS 27.0.1 + DaVinci Resolve Studio 21.1.0.14 unless marked otherwise. Windows/Linux/free edition untested.
Evidence and examples: `docs/zh-TW/` (Chinese, primary) and `docs/en/`. Chapter numbers below refer to those docs.

## Ground rules

1. **Render is truth.** API calls often return success with no visible effect, or None without an error. After every change, render an MP4 and inspect frames with ffmpeg before claiming it worked. (ch 0.4, 18)
2. **Check the local API docs before saying "impossible".** `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/` holds `DaVinciResolveScript.pyi` (authoritative signatures) and `CHANGELOG.md`. 21.1 added `TimelineItem.AddTransition`. (1.9)
3. **Never overwrite the user's work.** Build a new timeline per revision (`v2`, `v3`); `CreateEmptyTimeline` returns None on a duplicate name. Save before switching projects — `LoadProject`/`CreateProject` drop unsaved changes. (2.1, 2.5)
4. **None from basic calls means Resolve is busy or blocked.** While a render is running, or while a modal dialog is open, `GetCurrentPage()`, `LoadProject()`, `SaveProject()`, `SetCurrentRenderFormatAndCodec()` return None silently. Check `IsRenderingInProgress()` first; otherwise list windows via System Events and dismiss the dialog with Esc, never Return. (1.5)
5. **Keep the Mac awake during long runs** (`caffeinate -dimsu ...`): renders containing Fusion titles crawl while the screen is locked. (1.7)

## Environment

- Interpreter (macOS): `/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Applications/ResolvePython` (Python 3.14, `import DaVinciResolveScript` works with no env vars). No pip. It does **not** put the script's directory on `sys.path`. (1.3)
- Resolve must be running and fully loaded; `scriptapp("Resolve")` is None for ~10 s after launch. External scripting must be **Local**. (1.2, 1.4)
- Heavy analysis (numpy, librosa, PIL) runs in a separate venv and hands JSON to the Resolve script. (1.3)

## Timelines and clips (ch 2)

- Timeline start = 01:00:00:00 = frame 108000 at 30 fps. `recordFrame` is absolute: `tl.GetStartFrame() + offset`.
- `AppendToTimeline` `endFrame` is exclusive.
- Stills ignore the requested length and land as 150 frames. Convert each still to a video first (`ffmpeg -i x.jpg -vf "loop=loop=239:size=1:start=0,fps=30,format=yuv420p" -frames:v 240 -c:v libx264 -crf 18 -r 30 x.mp4`).
- Purely numeric file names (`1001.png`, `1002.png`) import as one image-sequence clip. Prefix them.
- `SetSetting("timelineFrameRate")` only works before the project has a timeline; `timelinePlaybackFrameRate` always returns False (render rate follows the timeline rate anyway). Read settings back with `GetSetting`.
- Render: deliver page → `DeleteAllRenderJobs` → `SetCurrentRenderFormatAndCodec("mp4","H264")` → `SetRenderSettings` → `AddRenderJob` → `StartRendering` → poll `IsRenderingInProgress`. Judge success by `CompletionPercentage == 100`; `JobStatus` is a localized string.

## Clip properties (ch 4)

- `Pan`/`Tilt` are output pixels for a frame-filling clip (`Tilt` positive = up), but `Pan` is scaled by (fitted width / 1920): a 1080x1920 clip fitted to 607.5 px moves 32 px for `Pan=100`. Pan is not multiplied by Zoom.
- `CropLeft/Right/Top/Bottom` are pixels of the clip as fitted into the frame (before Zoom), measured from the clip's own edge; cropping does not move the image.
- `CompositeMode` takes `r.COMPOSITE_*` constants, not strings. `Opacity` is 0-100.
- Appending onto an occupied range of the same track returns success but places nothing — the earlier clip stays.
- There are no setters for a timeline item's start/length: rebuild, or export/patch/re-import a .drt (ch 9).

## Transitions (ch 5)

- `item.AddTransition({"type", "category": "simple"|"fusion", "position": "start"|"end", "alignment": "center", "duration": frames})`. 30 simple + 28 Fusion names verified (list in docs ch 5). Names are case-sensitive (`Dip To Color Dissolve`, not `Dip to ...`). OFX/Resolve FX transitions (Burn Away) cannot be added this way.
- Centred transitions need handles: start each clip a few frames into its source.
- A created transition's parameters cannot be read back (`GetProperty()` is `{}`).

## Titles (ch 6)

- `InsertFusionTitleIntoTimeline(name)` always inserts on V1 at the playhead as an **insert edit**: it splits the V1 clip and ripples everything after it. Locking V1 makes it return None; disabling V1 does not redirect it. Never call it on a finished timeline.
- To place a title anywhere: (A) insert it into its own small timeline and append that timeline's pool item to the target track; or (B) put a transparent ProRes 4444 clip on the target track and build TextPlus + Merge inside its Fusion comp.
- Change text via `item.GetFusionCompByIndex(1).GetToolList(False, "TextPlus")` → `SetInput("StyledText", ...)`. `Slide In` ships with empty text.

## Keyframes and speed (ch 7-8)

- No API for Edit-page inspector keyframes. Options: Dynamic Zoom (`DynamicZoomEnabled`, `DynamicZoomEase`; default direction is zoom OUT, direction not settable); import an FCPXML whose `<adjust-transform>` carries `<keyframeAnimation>` for scale/position/rotation (position unit = 1% of frame height, y up; keyframe `time` in source time); or Fusion `Transform` with `AddModifier("Size","BezierSpline")` and `SetInput("Size", v, frame)` (comp frame 0 = clip's first frame).
- `item.SetSpeed({"Percentage": 200.0})` sets constant speed; the clip keeps its timeline length.
- Speed ramps: Fusion `TimeStretcher`, keyframe `SourceTime` (output frame -> source frame).

## Editing an existing timeline (ch 9)

- Export `.drt` (`tl.Export(path, r.EXPORT_DRT, r.EXPORT_NONE)`), unzip, patch `<Start>` (absolute, from 108000) / `<Duration>` / `<In>` in `SeqContainer/*.xml`, re-zip with the three entries at the zip root, `ImportTimelineFromFile`. Lossless: transitions, CDL, Dynamic Zoom, Fusion all survive. `.drt` import ignores `timelineName`; rename inside the file. Read a file fully before reopening it for writing.
- FCPXML 1.10 (exported as a folder) and OTIO round trips drop transitions, CDL and Fusion (OTIO keeps Dynamic Zoom). Use them only to generate new timelines.

## Fusion (ch 10-12)

- `comp = item.AddFusionComp()`; connect tools between `MediaIn1` and `MediaOut1`; unconnected tools have no effect. Effects added this way DO render.
- Resolve FX run inside Fusion as `ofx.com.blackmagicdesign.resolvefx.<Name>` (100 on 21.1; list via `r.Fusion().GetRegList(1)`). Their image input is **`Source`**, not `Input`; a wrong/missing image input makes the render fail.
- Some Resolve FX defaults do nothing (ChromaticAberration curvature = 0); set parameters by `INPS_ID`.
- Burn Away: put the outgoing clip on the upper track, Fusion `BurnAway` with `SourceFrom`=MediaIn, `SourceTo`=transparent Background (must be connected), keyframe `Transition` 0->1.
- Avoid `comp.AddTool("Loader")`: it opens a file dialog that blocks the API. `comp.Lock()` suppresses the dialog.
- Hung render: `StopRendering()` does not help; set a timeout, and restart Resolve if needed. If a crash-report dialog appears, click "Ignore", never "Send" without the user's consent.
- Custom transitions/titles: `.setting` files in `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/<Transitions|Titles|Effects|Generators>/`; new files need a Resolve restart, edits do not. Call by file name with category `fusion`. In a `LUTLookup`, `Curve` must be `Custom` for a connected `LUTBezier` to be used.

## Color (ch 13-15)

- `SetCDL` takes strings (`"Slope": "1.2 1.0 0.8"`); write-only.
- `GetNodeGraph(1).SetLUT(1, "sub/x.cube")` accepts only paths relative to the master LUT folder (`/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT` on macOS); call `p.RefreshLUTList()` after adding files. `.dctl` files apply the same way (no sliders).
- Save/reuse a grade: color page → playhead on the clip → `tl.GrabStill()` → `album.ExportStills([still], dir, prefix, "drx")` → `target.GetNodeGraph(1).ApplyGradeFromDRX(path, 0)`. Its return value is unreliable (None or True); check the render. A Power Window drawn once in the GUI travels inside the .drx. GrabStill takes the topmost clip at the playhead.
- No API for nodes, primaries, Power Windows or qualifiers. Use DCTL for programmatic masks/keys (`r.ValidateDCTL(src)` returns None when valid), or a GUI-made .drx.

## Beyond the documented limits (ch 19)

- Audio: `AudioVolumeEnabled`/`AudioVolume` (dB), `AudioPanEnabled`/`AudioPan`, `AudioPitchEnabled`/`AudioPitchSemiTones` work via SetProperties on 21.1 (verified: -12 dB exact, +12 semitones = 2x frequency).
- Split a clip: export .drt, duplicate the clip's `<Element>`, give every `DbId` in the copy a new UUID, adjust `<Start>`/`<Duration>`/`<In>`, re-import.
- Read transitions back from a .drt: `<Sm2TiTransition>` has `<PrettyType>`, `<Start>`, `<Duration>`, `<AlignmentType>`; Fusion transitions hide the template name in the hex `<FieldsBlob>` as `Templates/Edit/Transitions/<Name>`.
- Subtitles: `ImportMedia([".srt"])`, `AddTrack("subtitle")`, append it — subtitle appends ignore `recordFrame` and land after the last item, so place the .srt on an empty timeline first. Burn-in: `SetRenderSettings({"ExportSubtitle": True, "SubtitleFormat": "BurnIn"})`.

## Beat sync (ch 16)

- Analyse in a normal venv (librosa), not ResolvePython. Use onsets, not beat_track grids (many intros have no drums). Separate stems first (Demucs htdemucs_ft). Judge loudness inside the frequency band. backtrack=True lands ~25 ms early; convert with round(t*fps). BPM is often halved/doubled. For lyric timing, use vocal-stem RMS valleys, not Whisper word times; let the human confirm key hits.

## Generated intros (ch 20)

- Motion-designed intros are rendered outside Resolve (`examples/20_intro_generator`, Remotion), then placed on the timeline. Templates and the shared rules for writing new ones: `prompts/intro-templates.zh-TW.md`.
- Render at the timeline frame rate (`node gen.mjs render <seed> --fps 30`); the animation is a pure function of seconds, so only the sampling changes.
- Mix intro audio to stereo. A mono track comes out of a stereo Resolve render ~3 LU louder (-14.1 became -11.1 LUFS).
- Overlays: `--alpha` writes ProRes 4444 with alpha; `AddTrack("video")` before appending to V2 (without it the append reports no failure but the overlay never shows).
- After re-rendering a file under the same name, delete the old media-pool clip (and timelines using it) and re-import; otherwise the render can fail partway (`JobStatus: Failed`). Or change the file name.
- `prompts/third-party/` belongs to the original prompt authors, not this repo's MIT license.

## Status of later chapters

All chapters are written; English chapter translations are in progress. Treat anything not listed here or marked verified in the chapters as unverified.
