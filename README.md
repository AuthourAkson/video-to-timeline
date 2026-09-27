# video-to-timeline

**从一个视频里，提取做一部音乐动画所需要的全部时间线材料。**

给它一个 MV / 现场 / 演奏视频，拿回三样东西：

| 交付物 | 用途 | 怎么来的 |
|---|---|---|
| **歌词时间线（LRC）** | 每一句歌词的落点 | 优先抓歌词站（毫秒级），再用视频硬字幕 OCR **交叉验证** |
| **音符起音表（卡点 CSV）** | 脉冲 / 闪白 / 扩散环的触发源 | 分频段谱通量起音检测 |
| **MIDI 文件** | 音高条 / 音符可视化 | 起音 + FFT 谱峰音高估计 → mido |

核心原则：**时间轴要两条腿走路** —— 网上的 LRC 只信一半，一定用视频自己的字幕（或音频起音）对一遍。

## 依赖

- **ffmpeg / ffprobe**（抽音频、抽帧、抽字幕）
- **Python 3** + `numpy` `scipy` `mido`
  （刻意**不依赖 librosa** —— 它的 numba 依赖经常和 numpy 2.x 打架）
- **Windows**（硬字幕 OCR 走系统自带引擎 `Windows.Media.Ocr`；其他平台请换 tesseract）

## 用法

```bash
# 0) 摸清视频（时长 / 流 / 有没有字幕轨）
bash scripts/probe.sh input.mp4

# 1) 抽音频（后续分析的统一输入）
bash scripts/extract-audio.sh input.mp4 work/audio.wav

# 2a) 有软字幕：直接抽
ffmpeg -i input.mp4 -map 0:s:0 work/out.srt

# 2b) 硬字幕：抽条带帧（原图 + 增强两套）→ 两遍 OCR → 合并成字幕段
bash scripts/subtitle-frames.sh input.mp4 work/subs work/subsB 2
powershell -File scripts/ocr-batch.ps1 -Dir "<绝对路径>\work\subs"  -Lang en-US > work/ocrA.raw
powershell -File scripts/ocr-batch.ps1 -Dir "<绝对路径>\work\subsB" -Lang en-US > work/ocrB.raw
python scripts/ocr-segments.py work            # → work/segments.json

# 2c) 校验网上下载的 LRC 与视频是否同一版本
python scripts/align-lrc.py internet.lrc work/segments.json

# 3) 起音 + MIDI + 卡点表
python scripts/onsets-midi.py work/audio.wav work/out --bpm 124
```

完整方法论、参数基准、8 条实战坑见 **[SKILL.md](SKILL.md)** 与 **[references/pitfalls.md](references/pitfalls.md)**。

## 实测（Mili - In Hell We Live, Lament）

```
视频 3:45.4 · HEVC 1080p30 · 无字幕轨 → 硬字幕 OCR 451 帧（10~15 秒跑完）
网上 LRC 69 行（毫秒级）→ 锚点校验 |Δt| 中位 0.28 s → PASS
音频 225.4 s → 起音 1612 个（7.2/秒）→ MIDI 1612 音符
```

## 已知边界

- **音高是估计值**：成品混音里鼓/贝斯/人声叠在一起，无法完美分离。做视觉可以，当乐谱不行。
- 想更准只能先**分轨**（Demucs 之类）再转谱，或找官方谱。

## 许可

工具脚本可自由使用；文档中引用的歌曲、歌词、视频版权归原作者所有。
