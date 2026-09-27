#!/usr/bin/env bash
# subtitle-frames.sh — 抽字幕条带帧（两套：原图 + 增强图，OCR 互相补救）
# 用法: bash subtitle-frames.sh <video> <outA> <outB> [fps] [crop滤镜]
#   crop 默认 "1920:140:0:940"（底部 140px 条带）—— 按视频实际字幕位置改
#   时间基准：第 n 帧 ≈ (n-1)/fps 秒，务必用一句已知歌词校准
set -e
V="${1:?}"; A="${2:?}"; B="${3:?}"; FPS="${4:-2}"; CROP="${5:-1920:140:0:940}"
mkdir -p "$A" "$B"
ffmpeg -v error -i "$V" -vf "fps=$FPS,crop=$CROP" -y "$A/f_%04d.png"
ffmpeg -v error -i "$A/f_%04d.png" -vf "format=gray,eq=contrast=2.4:brightness=0.12,scale=iw*2:ih*2:flags=lanczos" -y "$B/f_%04d.png"
echo "原图帧 $(ls "$A" | wc -l) 张 → $A"
echo "增强帧 $(ls "$B" | wc -l) 张 → $B"
