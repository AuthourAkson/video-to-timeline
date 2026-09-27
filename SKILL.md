---
name: video-to-timeline
description: 从一个视频里提取制作音乐动画所需的全部时间线材料 —— 歌词 LRC、字幕时间轴、音符起音表（卡点）、MIDI 文件。Use this skill whenever the user hands over a video (MV / 现场 / 演奏 / 游戏过场) and asks for 歌词时间轴 / LRC / 字幕 / 提取歌词 / MIDI / 卡点 / onset / 音符表, or whenever you are about to build a music-driven animation and need the timing data first. Also use it when a video has burned-in subtitles that must be read out, when the audio must be turned into note events without internet access, or when a downloaded LRC needs to be cross-checked against the actual video.
---

# video-to-timeline：视频 → 歌词时间线 + 卡点 + MIDI

## 这个 skill 解决什么问题

做一部"跟着音乐走"的动画（每句歌词一块画板、每个重音一次脉冲），
开工前必须先拿到三样东西：

| 要的东西 | 用途 | 本 skill 怎么拿 |
|---|---|---|
| **歌词 + 时间戳（LRC）** | 每句歌词的落点 | 优先从歌词站抓（毫秒级），再用视频字幕 OCR **交叉验证** |
| **笔记号起音表**（time_ms, strength） | 卡点：脉冲、闪白、扩散环 | 分频段谱通量起音检测（不依赖 librosa） |
| **MIDI 文件** | 音高条 / 音符可视化 / 兜底 | 起音 + FFT 谱峰音高估计 → mido 写 .mid |

**核心原则：时间轴要"两条腿走路"** —— 网上的 LRC 只信一半，一定要用视频自己的字幕（或音频起音）对一遍。两边对不上就说明版本不同（TV size / 完整版 / 现场版），必须查清楚再动工。

## 工作流程

### 第 0 步：先摸清视频（永远先做这一步）

```bash
bash scripts/probe.sh <video>
```

要回答四个问题：**时长**、**有没有字幕轨**（软字幕最好，直接抽）、**几条音轨**、**帧率**。
有字幕轨就用 `ffmpeg -map 0:s:0 out.srt`，跳过后面 OCR 那一大套。

### 第 1 步：抽音频（后面所有分析的基础）

```bash
bash scripts/extract-audio.sh <video> work/audio.wav
```

统一成 **单声道 44.1kHz PCM**：起音检测、音高估计、波形比对都用它。

### 第 2 步：歌词时间线 —— 三条路线，按优先级

1. **软字幕** → `ffmpeg -map 0:s:0` 抽出 → 转 LRC。最准。
2. **硬字幕（烧在画面里）** → 抽条带帧 + OCR：
   ```bash
   bash scripts/subtitle-frames.sh <video> work/subs work/subsB   # 2fps，两套预处理
   powershell -File scripts/ocr-batch.ps1 -Dir <绝对路径>\work\subs  -Lang en-US > work/ocrA.raw
   powershell -File scripts/ocr-batch.ps1 -Dir <绝对路径>\work\subsB -Lang en-US > work/ocrB.raw
   python scripts/ocr-segments.py work    # 合并 → segments.json（字幕段：起止时间 + 文本）
   ```
3. **完全没有字幕** → 语音识别（faster-whisper 已装的话直接上；唱歌的识别率会打折，重复段落尤甚）。

**并行做**：去歌词站抓现成 LRC（`lrc6.com`、`wagequ.com`、`lrc.64h.cn` 等搜索 "<歌名> lrc"），
然后 **必须**跑一次对齐验证：

```bash
python scripts/align-lrc.py work/internet.lrc work/segments.json
```

它会逐行告诉你：哪些行在视频里找到了对应字幕（附时间差），哪些行视频里没有（可能是版本差异或漏识别）。

### 第 3 步：卡点表 + MIDI

```bash
python scripts/onsets-midi.py work/audio.wav work/out --bpm 124
```

输出：
- `out-onsets.csv`：`time_ms, strength, midi_note`
- `out.mid`：可直接拖进 DAW / 网页 MIDI 库的单轨 MIDI
- stdout 给出：起音总数、每秒密度、音高分布（用来判断参数是否合理）

**参数是否合理的判据**（实战值）：
- 起音密度 **3–12 个/秒**（摇滚/电子偏高，抒情偏低）。低于 2 说明漏检（降阈值），高于 20 说明把噪声当音符了（升阈值）。
- 音高 p5/p50/p95 应落在 MIDI 30–90 之间。

## 踩过的坑（都是真金白银换来的）

1. **抽帧的时间基准要先校准。** `ffmpeg -vf fps=2` 抽出的第 n 帧，时间大致是 `(n-1)/2` 秒，
   但最好拿一个已知时间点（比如 LRC 的第一句）对一遍再往下算。差半帧就会让整条时间轴偏 0.25s。

2. **OCR 认不出"红色/细体"字幕。** 白色字幕用「灰度 + 拉对比度 + 放大 2 倍」几乎全对；
   红色或渐隐字幕会碎成 `Buc!l p op e Vet` 这种。**解决：抽两套图（原图 + 增强图）各 OCR 一遍再合并**，
   同一句歌词有多帧冗余，模糊匹配（`difflib.SequenceMatcher > 0.55`）就能拼回完整段落。

3. **字幕快速切换时会产生大量"碎片段"**（如 `A regre | bidde | It'lllt`）。
   它们不是新歌词，是同一句在动画中被切碎。合并时按"时间相邻 + 文本相似"归并，
   剩下的孤立碎片一律丢弃（宁可漏，不可乱）。

4. **成品混音不可能还原成谱面。** 鼓、贝斯、人声、吉他叠在一起，自动转谱一定糊。
   所以本 skill 的定位是：**时间轴准（±30ms 级别）、音高是估计值**。
   音高拿来做视觉（音高条、粒子高度）没问题，**当乐谱用会出事**。要真谱只能分轨或买谱。

5. **别忘了 librosa 可能被 numba/numpy 版本卡死**（`Numba needs NumPy 2.0 or less`）。
   本 skill 的脚本**只用 numpy + scipy**，不碰 librosa，就是为了不踩这个雷。

6. **MIDI 站的下载通常在登录墙后面**（midishow 之类），而且站点可能整个不可达。
   先试着抓页面，抓不到就果断走"音频提取"路线 —— 别在下载上耗超过十分钟。

7. **Windows OCR 的调用**：`ocr-batch.ps1` 用系统自带引擎，跑 450 帧只要 10~15 秒，
   但**只能吃 .png**（`-Filter *.png`），JPEG 要先转。

8. **写文件路径时注意**：Git Bash 的 `/tmp` 与 Windows Python 的路径不互通，
   跨工具传路径一律用 `cygpath -w` 转换，否则 Python 会说"文件不存在"。

## 脚本清单

```
scripts/probe.sh            摸清视频（时长/流/字幕轨）
scripts/extract-audio.sh    抽单声道 44.1k WAV
scripts/subtitle-frames.sh  抽字幕条带帧（原图 + 增强两套）
scripts/ocr-batch.ps1       Windows OCR 批量识别一个目录的 png
scripts/ocr-segments.py     合并两套 OCR 结果 → 字幕段（起止时间 + 文本）
scripts/align-lrc.py        网上下载的 LRC ↔ 视频字幕段 对齐校验
scripts/onsets-midi.py      分频段起音检测 + 音高估计 → MIDI + 卡点表
references/pitfalls.md      上面这些坑的展开版（含参数与判据）
```

## 交付前检查清单

- [ ] `probe.sh` 的输出里，**时长**和用户说的一致
- [ ] LRC 行数 ≥ 歌词实际句数；首句/末句的时间戳**落在视频长度内**
- [ ] `align-lrc.py` 报告里，匹配率 ≥ 70%（低于这个数说明版本不对，要查）
- [ ] 起音密度在 3–12 个/秒之间
- [ ] 生成的 `.mid` 能被读回：`python -c "import mido; m=mido.MidiFile('x.mid'); print(m.length)"`
- [ ] 交付物和三样东西（LRC / 卡点表 / MIDI）齐全，中间产物（帧目录等）清理掉

## 用于"做动画"时的对接方式

- LRC → 逐句时间线（每句一个 cue，可再用 `_tools/build-timeline.js` 那种生成器变成代码常量）
- 卡点表 → `[时间ms, 强度]` → 脉冲/闪白/扩散环的触发源
- MIDI/音高 → 音高条、粒子高度、图形变形幅度
- 别忘了：**动画的时间基准永远是 `audio.currentTime + syncOffset`**，这份时间轴只是"台词表"。
