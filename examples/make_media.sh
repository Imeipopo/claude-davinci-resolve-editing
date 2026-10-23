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

# Chapter 22 (jump cuts): a "talking head" stand-in. Five Mandarin sentences (macOS say) separated by pauses of
# 0.2 / 1.5 / 2.5 / 0.9 s (say adds ~0.2 s of its own), 1 s of silence before and 1.2 s after. The picture carries
# its own frame number as 11 white/black blocks along the top (block k = bit k), so a render can be read back
# frame by frame. talk_src.srt holds the exact sentence times.
TALK=("大家好，今天示範自動剪掉停頓。" "第一段話講完會停一下。" "這裡停了比較久，應該被剪掉。" "短的換氣要留著，聽起來才自然。" "最後一句，謝謝收看。")
GAPS=(1.0 0.2 1.5 2.5 0.9 1.2)
parts=() srt="" t=0 n=0
for k in "${!TALK[@]}"; do
  say -v Meijia -o "$M/_talk_$k.aiff" "${TALK[$k]}"
  ffmpeg -v error -y -f lavfi -i "anullsrc=r=48000:cl=mono" -t "${GAPS[$k]}" "$M/_gap_$k.wav"
  ffmpeg -v error -y -i "$M/_talk_$k.aiff" -ar 48000 -ac 1 "$M/_talk_$k.wav"
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$M/_talk_$k.wav")
  t=$(python3 -c "print(round($t + ${GAPS[$k]}, 6))"); e=$(python3 -c "print(round($t + $d, 6))")
  n=$((n + 1)); srt+="$n
$(python3 -c "f=lambda x:'%02d:%02d:%02d,%03d'%(x//3600,x//60%60,x//1%60,round(x%1*1000)); print(f($t),'-->',f($e))")
${TALK[$k]}

"
  t=$e; parts+=("$M/_gap_$k.wav" "$M/_talk_$k.wav")
done
ffmpeg -v error -y -f lavfi -i "anullsrc=r=48000:cl=mono" -t "${GAPS[5]}" "$M/_gap_5.wav"
parts+=("$M/_gap_5.wav")
printf "file '%s'\n" "${parts[@]}" > "$M/_talk.txt"
ffmpeg -v error -y -f concat -safe 0 -i "$M/_talk.txt" -c:a pcm_s16le "$M/talk_src.wav"
printf "%s" "$srt" > "$M/talk_src.srt"
bits=""
for k in $(seq 0 10); do bits+=",drawbox=x=$((60 + k * 160)):y=40:w=120:h=120:c=white:t=fill:enable='bitand(n\,$((1 << k)))'"; done
len=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$M/talk_src.wav")
ffmpeg -v error -y -f lavfi -i "testsrc2=s=1920x1080:r=30" -i "$M/talk_src.wav" -t "$len" \
  -vf "drawbox=x=40:y=20:w=1780:h=160:c=black:t=fill$bits,format=yuv420p" \
  -c:v libx264 -crf 16 -g 30 -c:a aac -b:a 192k -ac 2 "$M/talk_src.mp4"
rm -f "$M"/_talk* "$M"/_gap_*

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
