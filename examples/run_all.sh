#!/bin/bash
# Runs every Resolve example and prints only the PASS/FAIL lines. Resolve Studio must be open.
# Long renders crawl while the screen is locked (docs 1.7); to keep the Mac awake for the run:
#   caffeinate -dimsu ./run_all.sh
set -uo pipefail
cd "$(dirname "$0")"
RP="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Applications/ResolvePython"
[ -d media ] || ./make_media.sh >/dev/null
for f in 02_first_timeline.py 04_clip_properties.py 05_transitions.py 06_titles.py 07_keyframes.py 08_speed.py \
         09_roundtrip.py 10_fusion_effects.py 12_templates.py 13_color.py 17_photo_demo.py 19_beyond.py 19b_more.py; do
  echo "== $f"
  "$RP" "$f" 2>&1 | grep -E "^(PASS|FAIL)|Error|Traceback"
done
