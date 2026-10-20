#!/bin/bash
# Generates every test asset the examples use (no personal media needed). Requires ffmpeg.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p media
M=media

# Four distinct 3:2 stills (3240x2160) and the same stills as 8-second H.264 clips.
i=0
for hue in 0 90 180 270; do
  i=$((i + 1))
  ffmpeg -v error -y -f lavfi -i "testsrc2=s=3240x2160:r=1" -frames:v 1 -vf "hue=h=${hue}" "$M/still_$i.png"
  # scale once, then loop the single frame: much faster than -loop 1 on large stills
  ffmpeg -v error -y -i "$M/still_$i.png" -vf "loop=loop=239:size=1:start=0,fps=30,format=yuv420p" \
    -frames:v 240 -c:v libx264 -crf 18 -r 30 "$M/clip_$i.mp4"
done

# Measurement targets: a white 120-px square centred on black, landscape and portrait, as 8-second clips.
ffmpeg -v error -y -f lavfi -i "color=c=black:s=1920x1080:r=30:d=8" \
  -vf "drawbox=x=900:y=480:w=120:h=120:color=white:t=fill,format=yuv420p" -c:v libx264 -crf 12 "$M/marker_land.mp4"
ffmpeg -v error -y -f lavfi -i "color=c=black:s=1080x1920:r=30:d=8" \
  -vf "drawbox=x=480:y=900:w=120:h=120:color=white:t=fill,format=yuv420p" -c:v libx264 -crf 12 "$M/marker_port.mp4"
# Flat mid-grey and flat colour clips for blend/opacity maths.
ffmpeg -v error -y -f lavfi -i "color=c=0x808080:s=1920x1080:r=30:d=8" -pix_fmt yuv420p -c:v libx264 -crf 12 "$M/grey.mp4"
ffmpeg -v error -y -f lavfi -i "color=c=0x2060c0:s=1920x1080:r=30:d=8" -pix_fmt yuv420p -c:v libx264 -crf 12 "$M/blue.mp4"

# Purely numeric file names: Resolve groups these into an image sequence on import.
cp "$M/still_1.png" "$M/1001.png"
cp "$M/still_2.png" "$M/1002.png"

# Frame-identifiable clip for retime tests: a 2-px white bar at x = 2*N on frame N (300 frames).
ffmpeg -v error -y -f lavfi -i "color=c=black:s=640x360:r=30:d=10" \
  -vf "format=gray,geq=lum='if(between(X,N*2,N*2+1),255,0)',format=yuv420p" -c:v libx264 -crf 10 "$M/ramp_src.mp4"

# Fully transparent 10-second ProRes 4444 placeholder (used to host Fusion titles on any track).
ffmpeg -v error -y -f lavfi -i "color=c=black@0.0:s=1920x1080:r=30:d=10,format=yuva444p10le" \
  -c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le "$M/transparent_10s.mov"

# 10-second 440 Hz tone as a stand-in music track.
ffmpeg -v error -y -f lavfi -i "sine=frequency=440:duration=10" -ar 48000 "$M/tone_10s.wav"

# Chapter 21 (Studio AI). Super Scale: sharp references and the same frames at one third size.
ffmpeg -v error -y -f lavfi -i "testsrc2=s=1920x1080:r=1" -frames:v 1 "$M/ss_ref.png"
ffmpeg -v error -y -i "$M/ss_ref.png" -vf "scale=640:360:flags=area" "$M/ss_small.png"
ffmpeg -v error -y -loop 1 -i "$M/ss_small.png" -t 4 -r 30 -pix_fmt yuv420p -c:v libx264 -crf 10 "$M/ss_small.mp4"
if [ -f ../assets/photos/groom_8625.jpg ]; then
  ffmpeg -v error -y -i ../assets/photos/groom_8625.jpg -vf "crop=1278:720:0:500" "$M/ss_photo_ref.png"
  ffmpeg -v error -y -i "$M/ss_photo_ref.png" -vf "scale=426:240:flags=area" "$M/ss_photo_lo.png"
  ffmpeg -v error -y -loop 1 -i "$M/ss_photo_lo.png" -t 4 -r 30 -pix_fmt yuv420p -c:v libx264 -crf 10 "$M/ss_photo_lo.mp4"
fi
# Retime / tracking target: a disc moving 16 px per frame over a textured background.
ffmpeg -v error -y -f lavfi -i "testsrc2=s=1920x1080:r=30:d=4" -f lavfi -i "color=c=white:s=160x160:r=30:d=4" \
  -filter_complex "[1]format=yuva420p,geq=lum='255':a='if(lt(hypot(X-80,Y-80),80),255,0)'[d];[0]hue=s=0.3[b];[b][d]overlay=x='100+16*n':y=460,format=yuv420p" \
  -c:v libx264 -crf 12 "$M/moving_disc.mp4"
# Power Window tracking target: a textured disc moving 8 px right and 3 px down per frame on flat grey.
ffmpeg -v error -y -f lavfi -i "color=c=0x303030:s=1920x1080:r=30:d=3" -f lavfi -i "testsrc2=s=240x240:r=30:d=3" \
  -filter_complex "[1]format=yuva420p,geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':a='if(lt(hypot(X-120,Y-120),120),255,0)'[d];[0][d]overlay=x='840+8*n':y='420+3*n',format=yuv420p" \
  -c:v libx264 -crf 12 "$M/track_disc.mp4"
# Voice isolation: Taiwanese Mandarin speech (macOS say) with 1.5-s pauses, over loud pink noise.
say -v Meijia -o "$M/voice_raw.aiff" "大家好，歡迎來參加我們的婚禮。[[slnc 1500]] 謝謝爸爸媽媽一路的照顧。[[slnc 1500]] 希望大家今天吃得開心。"
ffmpeg -v error -y -i "$M/voice_raw.aiff" -ar 48000 -ac 1 "$M/voice_clean.wav"
ffmpeg -v error -y -i "$M/voice_clean.wav" -f lavfi -i "anoisesrc=color=pink:amplitude=0.12:sample_rate=48000:seed=7" \
  -filter_complex "[0][1]amix=inputs=2:duration=first:normalize=0" -ac 2 -ar 48000 "$M/voice_noisy.wav"
# Stereo 3D: left and right eye views 24 px apart.
ffmpeg -v error -y -f lavfi -i "testsrc2=s=1944x1080:r=30:d=4" -vf "crop=1920:1080:0:0,format=yuv420p" -c:v libx264 -crf 14 "$M/eye_left.mp4"
ffmpeg -v error -y -f lavfi -i "testsrc2=s=1944x1080:r=30:d=4" -vf "crop=1920:1080:24:0,format=yuv420p" -c:v libx264 -crf 14 "$M/eye_right.mp4"

# Optional real photos in ../assets/photos -> 8-second clips for 17_photo_demo.py
if ls ../assets/photos/*.jpg >/dev/null 2>&1; then
  mkdir -p media_photos
  for f in ../assets/photos/*.jpg; do
    b=$(basename "${f%.jpg}")
    ffmpeg -v error -y -i "$f" -vf "loop=loop=239:size=1:start=0,fps=30,format=yuv420p" \
      -frames:v 240 -c:v libx264 -crf 16 -r 30 "media_photos/$b.mp4"
  done
fi

ls -la "$M"
