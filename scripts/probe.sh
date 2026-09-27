#!/usr/bin/env bash
# probe.sh — 摸清一个视频：时长 / 流 / 有没有字幕轨
# 用法: bash probe.sh <video>
set -e
V="${1:?用法: probe.sh <video>}"
echo "== 文件 =="; ls -la "$V"
echo; echo "== 容器 =="
ffprobe -v error -show_entries format=duration,size,bit_rate,format_name -of default=noprint_wrappers=1 "$V"
echo; echo "== 流 =="
ffprobe -v error -show_entries stream=index,codec_type,codec_name,width,height,r_frame_rate,channels,sample_rate -of default=noprint_wrappers=1 "$V"
echo; echo "== 字幕轨 =="
SUB=$(ffprobe -v error -select_streams s -show_entries stream=index,codec_name -of csv=p=0 "$V" || true)
if [ -n "$SUB" ]; then
  echo "有软字幕轨: $SUB"
  echo "直接抽: ffmpeg -i \"$V\" -map 0:s:0 out.srt"
else
  echo "没有软字幕轨 → 走硬字幕 OCR（subtitle-frames.sh）或语音识别"
fi
