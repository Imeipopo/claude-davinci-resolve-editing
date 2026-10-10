#!/bin/bash
# Downloads the SIL OFL fonts the templates use from the google/fonts repository into public/fonts.
set -euo pipefail
cd "$(dirname "$0")/public/fonts"
B=https://raw.githubusercontent.com/google/fonts/main/ofl
get() { [ -s "$2" ] || curl -sfL "$B/$1" -o "$2"; echo "ok $2"; }
get "notosanstc/NotoSansTC%5Bwght%5D.ttf" NotoSansTC.ttf
get "notoseriftc/NotoSerifTC%5Bwght%5D.ttf" NotoSerifTC.ttf
get ibmplexmono/IBMPlexMono-Medium.ttf IBMPlexMono-Medium.ttf
get pressstart2p/PressStart2P-Regular.ttf PressStart2P.ttf
get lxgwwenkaitc/LXGWWenKaiTC-Regular.ttf LXGWWenKaiTC-Regular.ttf
get lxgwwenkaitc/LXGWWenKaiTC-Bold.ttf LXGWWenKaiTC-Bold.ttf
get cactusclassicalserif/CactusClassicalSerif-Regular.ttf CactusClassicalSerif-Regular.ttf
