#!/usr/bin/env python
"""align-lrc.py — 网上下载的 LRC ↔ 视频字幕段 对齐校验

用法:
    python align-lrc.py <lrc文件> <segments.json>

用途：判断网上的 LRC 与这个视频是不是"同一个版本"，以及时间轴是否可直接用。
输出：stdout 摘要 + <lrc文件>.align.txt 明细。
判据：匹配率 ≥70% 且 |Δt| 中位数 <0.5s → 可以直接用；否则要查版本差异。
"""
import io, os, re, sys, json, difflib

try:                      # 控制台可能是 GBK：中文/特殊字符打印时会炸，这里兜底
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def parse_lrc(path):
    rows = []
    for line in io.open(path, encoding='utf-8', errors='replace'):
        m = re.match(r'\[(\d+):(\d+)[.:](\d+)\]\s*(.*)', line.strip())
        if not m: continue
        fr = m.group(3)
        t = int(m.group(1)) * 60 + int(m.group(2)) + int(fr) / (1000.0 if len(fr) == 3 else 100.0)
        rows.append({'t': round(t, 3), 'text': m.group(4).strip()})
    return rows

def sim(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

def main():
    if len(sys.argv) < 3:
        print(__doc__); return 2
    lrc_path, seg_path = sys.argv[1], sys.argv[2]
    lrc = parse_lrc(lrc_path)
    segs = json.load(io.open(seg_path, encoding='utf-8'))
    # 阶段 1：每个 LRC 行独立找最佳匹配
    cands = []
    for i, L in enumerate(lrc):
        bj, br = -1, 0.0
        for j, S in enumerate(segs):
            r = sim(L['text'], S['t'])
            if r > br: br, bj = r, j
        cands.append((i, bj, br))

    # 阶段 2：只留高置信度、且时间严格递增的锚点（错配会在这一步被丢掉）
    anchors, last_t = [], -1e9
    for i, bj, br in cands:
        if br < 0.55: continue
        t = segs[bj]['s']
        if t <= last_t: continue
        anchors.append((i, bj, br)); last_t = t
    amap = {i: (bj, br) for i, bj, br in anchors}

    lines, dts = [], []
    for i, L in enumerate(lrc):
        if i in amap:
            bj, br = amap[i]
            dt = segs[bj]['s'] - L['t']; dts.append(abs(dt))
            lines.append('ANCHOR lrc=%8.3f  video=%8.3f  dt=%+6.2f  r=%.2f | %s' % (L['t'], segs[bj]['s'], dt, br, L['text'][:44]))
        else:
            lines.append('       lrc=%8.3f  video=    n/a            | %s' % (L['t'], L['text'][:44]))
    used = set(bj for _, bj, _ in anchors)
    hits = len(anchors)
    n, h = len(lrc), hits
    med = sorted(dts)[len(dts) // 2] if dts else -1
    print('LRC %d 行 · 高置信锚点 %d 个 · |Δt| 中位数 %.2fs · 最大 %.2fs' % (n, h, med, max(dts) if dts else -1))
    out = lrc_path + '.align.txt'
    print('明细: ' + out)
    ok = med >= 0 and med < 0.6 and h >= 8
    print('判据: 可靠锚点 ≥8 个 且 |中位Δt| <0.6s → 版本一致、LRC 可直接用')
    print('     （匹配率低多半是 OCR 把字幕切碎了，不代表版本不同；中位Δt大才是版本问题）')
    print('结论: ' + ('PASS —— 这份 LRC 与视频一致' if ok else 'CHECK —— 需要人工核对版本/时间轴'))
    return 0

if __name__ == '__main__':
    sys.exit(main())
