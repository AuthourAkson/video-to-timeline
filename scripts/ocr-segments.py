#!/usr/bin/env python
"""ocr-segments.py — 两套 OCR 结果 → 字幕段（起止时间 + 文本）

用法:
    python ocr-segments.py <workdir> [--fps 2] [--sim 0.55]

<workdir> 里应有 ocrA.raw / ocrB.raw（ocr-batch.ps1 的输出，每行 "f_0001.png<TAB>文本"）。
输出 <workdir>/segments.json，每项 {s, end, t} = 起始秒 / 结束秒 / 文本。
"""
import io, os, re, sys, json, difflib

try:                      # 控制台可能是 GBK：中文/特殊字符打印时会炸，这里兜底
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def load(path):
    out = {}
    if not os.path.isfile(path): return out
    for line in io.open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'f_(\d+)\.png\t(.*)', line.strip())
        if m: out[int(m.group(1))] = m.group(2).strip()
    return out

def sim(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

def main():
    pos = [a for a in sys.argv[1:] if not a.startswith('--')]
    wd = pos[0] if pos else '.'
    fps = float(sys.argv[sys.argv.index('--fps') + 1]) if '--fps' in sys.argv else 2.0
    thr = float(sys.argv[sys.argv.index('--sim') + 1]) if '--sim' in sys.argv else 0.55

    A, B = load(os.path.join(wd, 'ocrA.raw')), load(os.path.join(wd, 'ocrB.raw'))
    best = dict(A)
    for n, t in B.items():
        if n not in best or len(t) > len(best[n]): best[n] = t
    if not best:
        print('!! 没读到 OCR 结果，检查 ocrA.raw / ocrB.raw')
        return 1

    segs = []
    for n in sorted(best):
        t = (n - 1) / fps
        txt = best[n]
        if segs and sim(segs[-1]['t'], txt) > thr and t - segs[-1]['end'] <= 0.7:
            segs[-1]['end'] = t
            if len(txt) > len(segs[-1]['t']): segs[-1]['t'] = txt
        else:
            segs.append({'s': t, 'end': t, 't': txt})
    out = os.path.join(wd, 'segments.json')
    json.dump(segs, io.open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('有字幕的帧 %d 个 → 合并成 %d 段 → %s' % (len(best), len(segs), out))
    for s in segs[:8]:
        print('  %7.2f → %6.2f  %s' % (s['s'], s['end'], s['t'][:52]))
    print('（提示：请用一句已知歌词校准时间基准）')
    return 0

if __name__ == '__main__':
    sys.exit(main())
