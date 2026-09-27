#!/usr/bin/env bash
# extract-audio.sh — 抽成单声道 44.1kHz PCM（后续所有分析的统一输入）
# 用法: bash extract-audio.sh <video> <out.wav>
set -e
V="${1:?用法: extract-audio.sh <video> <out.wav>}"; O="${2:?用法: extract-audio.sh <video> <out.wav>}"
mkdir -p "$(dirname "$O")"
ffmpeg -v error -i "$V" -vn -acodec pcm_s16le -ar 44100 -ac 1 -y "$O"
echo "已抽音频: $O"
python -c "import scipy.io.wavfile as w, sys; sr,y=w.read(sys.argv[1]); print('时长 %.2f s · %d Hz · %d 采样' % (len(y)/sr, sr, len(y)))" "$(cygpath -w "$O")"
