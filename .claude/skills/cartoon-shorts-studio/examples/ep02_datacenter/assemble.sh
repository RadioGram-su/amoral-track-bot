#!/bin/bash
set -e
cd "$(dirname "$0")"
ffmpeg -loglevel error -y -framerate 15 -i frames/f%04d.png -i mix.wav \
  -filter_complex "[0:v]split[a][b];[a]palettegen=stats_mode=single:max_colors=64[p];[b][p]paletteuse=new=1:dither=bayer:bayer_scale=1,scale=1080:1920:flags=neighbor,drawgrid=w=iw:h=3:t=1:c=black@0.13,fps=30,format=yuv420p[v]" \
  -map "[v]" -map 1:a -c:v libx264 -preset medium -crf 18 -c:a aac -b:a 160k -movflags +faststart -shortest ep02_datacenter_ru.mp4
ffprobe -v error -show_entries format=duration,size -of default=nw=1 ep02_datacenter_ru.mp4
