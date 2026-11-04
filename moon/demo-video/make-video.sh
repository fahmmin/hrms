#!/usr/bin/env bash
# Re-record the captioned walkthrough video from a running demo.
#   Requirements: the demo running at $BASE (default http://localhost:8080) with fresh demo data,
#                 Node.js 18+, ffmpeg.
#   Usage:        ./make-video.sh            -> ../docs/media/moon-exchange-hrms-demo.mp4
# Note: the recording clocks Kavya out in the mobile app and drags one CRM deal to "Customer",
# so record on a freshly seeded demo (../start.sh reset && ../start.sh).
set -euo pipefail
cd "$(dirname "$0")"
[ -d node_modules/playwright ] || { npm init -y >/dev/null; npm i playwright@1.49.1 >/dev/null; npx playwright install chromium; }
rm -rf raw
node record.js
D1=$(ls raw/d1/*.webm); M=$(ls raw/m/*.webm); D2=$(ls raw/d2/*.webm)
OUTFILE=../docs/media/moon-exchange-hrms-demo.mp4
ffmpeg -v error -y -i "$D1" -i "$M" -i "$D2" -filter_complex "\
[0:v]fps=25,scale=1280:800,setsar=1,format=yuv420p[a];\
[1:v]fps=25,scale=-2:760,pad=1280:800:(ow-iw)/2:(oh-ih)/2:color=0x0f172a,setsar=1,format=yuv420p[b];\
[2:v]fps=25,scale=1280:800,setsar=1,format=yuv420p[c];\
[a][b][c]concat=n=3:v=1:a=0[v]" -map "[v]" -c:v libx264 -preset medium -crf 24 -movflags +faststart "$OUTFILE"
echo "Wrote $OUTFILE"
