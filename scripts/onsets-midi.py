#!/usr/bin/env python
"""onsets-midi.py — 音频 → 起音表（卡点）+ 音高估计 → MIDI

用法:
    python onsets-midi.py <audio.wav> <out前缀> [--bpm 124] [--thr 1.1]

输出:
    <out>-onsets.csv   time_ms,strength,midi_note
    <out>.mid          单轨 MIDI —— 时间轴准(±30ms)，音高是估计值(成品混音无法分轨)
说明:
    只用 numpy + scipy + mido，不依赖 librosa（避开 numba/numpy 版本地狱）。
    起音密度应落在 3–12 个/秒；过低→降 --thr，过高→升 --thr。
"""
import io, os, sys
import numpy as np
import scipy.io.wavfile as wav
import scipy.signal as sig
import mido

try:                      # 控制台可能是 GBK：中文/特殊字符打印时会炸，这里兜底
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def detect_onsets(y, sr, thr=1.1):
    n_fft, hop = 2048, 512
    f, tt, Z = sig.stft(y, fs=sr, nperseg=n_fft, noverlap=n_fft - hop)
    mag = np.abs(Z)
    def band(lo, hi):
        sel = (f >= lo) & (f < hi)
        return np.concatenate([[0], np.maximum(0, np.diff(mag[sel], axis=1)).sum(axis=0)])
    def pick(flux, th, dist_s):
        w = int(0.35 * sr / hop) | 1
        b = sig.medfilt(flux, kernel_size=w)
        z = (flux - b) / (np.abs(b) + 1e-6)
        pk, _ = sig.find_peaks(z, height=th, distance=max(1, int(dist_s * sr / hop)))
        return tt[pk], z[pk]
    o1, s1 = pick(band(0, 200), thr, 0.06)          # 底鼓 / 贝斯
    o2, s2 = pick(band(200, 2500), thr, 0.06)       # 人声 / 吉他 / 键盘
    o3, s3 = pick(band(2500, 14000), thr + 0.2, 0.05)  # 镲 / 齿音
    at = np.concatenate([o1, o2, o3]); a_s = np.concatenate([s1, s2, s3])
    order = np.argsort(at); at, a_s = at[order], a_s[order]
    keep = []
    for t, s in zip(at, a_s):
        if keep and t - keep[-1][0] < 0.055:
            if s > keep[-1][1]: keep[-1] = [float(t), float(s)]
        else:
            keep.append([float(t), float(s)])
    return keep

def pitch_at(y, sr, t0):
    i0 = int(t0 * sr); seg = y[i0:i0 + int(0.085 * sr)]
    if len(seg) < 1024: return 0
    w = seg * np.hanning(len(seg))
    sp = np.abs(np.fft.rfft(w, 8192)); fr = np.fft.rfftfreq(8192, 1.0 / sr)
    sel = (fr > 75) & (fr < 1100); sp, fr = sp[sel], fr[sel]
    if not len(sp): return 0
    return int(round(69 + 12 * np.log2(float(fr[int(np.argmax(sp))]) / 440.0)))

def main():
    pos = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(pos) < 2:
        print(__doc__); return 2
    wav_path, out = pos[0], pos[1]
    bpm = float(sys.argv[sys.argv.index('--bpm') + 1]) if '--bpm' in sys.argv else 120.0
    thr = float(sys.argv[sys.argv.index('--thr') + 1]) if '--thr' in sys.argv else 1.1

    sr, y = wav.read(wav_path)
    y = y.astype(np.float32) / 32768.0
    if y.ndim > 1: y = y.mean(axis=1)
    dur = len(y) / sr
    ev = detect_onsets(y, sr, thr)
    for e in ev: e.append(pitch_at(y, sr, e[0]))
    notes = [e for e in ev if 24 <= e[2] <= 96]
    print('音频 %.1fs · 起音 %d 个 (%.1f/秒) · 有效音高 %d 个' % (dur, len(ev), len(ev) / dur, len(notes)))
    if notes:
        p = np.percentile([e[2] for e in notes], [5, 50, 95])
        print('音高 p5/p50/p95 = %d / %d / %d (MIDI 号)' % tuple(int(x) for x in p))

    lines = ['time_ms,strength,midi_note'] + ['%d,%.2f,%d' % (round(t * 1000), s, n) for t, s, n in notes]
    io.open(out + '-onsets.csv', 'w', encoding='utf-8').write('\n'.join(lines))

    TPB, s2t = 480, 480 * bpm / 60.0
    mid = mido.MidiFile(ticks_per_beat=TPB); tr = mido.MidiTrack(); mid.tracks.append(tr)
    tr.append(mido.MetaMessage('track_name', name=os.path.basename(out)))
    tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm), time=0))
    cur = 0
    for i, (t, s, n) in enumerate(notes):
        nxt = notes[i + 1][0] if i + 1 < len(notes) else t + 0.3
        start = max(cur, int(t * s2t)); ln = max(24, int(min(0.22, nxt - t) * s2t))
        vel = int(np.clip(38 + s * 16, 28, 127))
        tr.append(mido.Message('note_on', note=int(n), velocity=vel, time=start - cur))
        tr.append(mido.Message('note_off', note=int(n), velocity=0, time=ln))
        cur = start + ln
    mid.save(out + '.mid')
    print('已写出: %s.mid (%d 音符) · %s-onsets.csv' % (out, len(notes), out))
    print('提醒: 音高为估计值，做视觉可用，当乐谱不可用。')
    return 0

if __name__ == '__main__':
    sys.exit(main())
