# -*- coding: utf-8 -*-
"""分析 wsl-localhost-probe 直方图日志（只读，不产生 churn）。
用法: python3 analyze_histogram.py <logfile>
"""
import io, sys, re, statistics
from collections import Counter

PAT = re.compile(r"^round\s+(\d+):\s+port\s+(\d+)\s+(first-success=\s*(\d+)ms|STALL > (\d+)s)(.*win=(ok:(\d+)ms|UNREACHABLE|n/a))?")

def parse(path):
    rounds = []
    with io.open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = PAT.match(line)
            if not m:
                continue
            n, port = int(m.group(1)), int(m.group(2))
            if m.group(3).startswith("first"):
                lat = int(m.group(4)); stall = False
            else:
                lat = None; stall = True
            win_ms = int(m.group(8)) if m.group(8) else None
            rounds.append({"n": n, "port": port, "stall": stall, "lat": lat, "win_ms": win_ms})
    return rounds

def main(path):
    rs = parse(path)
    total = len(rs)
    if total == 0:
        print("no rounds parsed")
        return
    stalls = [r for r in rs if r["stall"]]
    oks = [r for r in rs if not r["stall"]]
    print("=== 总览 ===")
    print("轮数=%d  STALL=%d (%.1f%%)  OK=%d (%.1f%%)" % (total, len(stalls), 100.0*len(stalls)/total, len(oks), 100.0*len(oks)/total))

    lats = sorted(r["lat"] for r in oks if r["lat"] is not None)
    if lats:
        print("OK 时延: min=%dms avg=%.1fms max=%dms p50=%dms p90=%dms p95=%dms" % (
            lats[0], statistics.mean(lats), lats[-1],
            lats[len(lats)//2], lats[int(len(lats)*0.9)-1], lats[int(len(lats)*0.95)-1]))
    wms = sorted(r["win_ms"] for r in oks if r["win_ms"] is not None)
    if wms:
        print("win=ok 时延: min=%dms avg=%.1fms max=%dms n=%d" % (wms[0], statistics.mean(wms), wms[-1], len(wms)))

    print("\n=== STALL 串长分布 ===")
    runs = []
    cur = 0
    for r in rs:
        if r["stall"]:
            cur += 1
        else:
            if cur: runs.append(cur); cur = 0
    if cur: runs.append(cur)
    c = Counter(runs)
    for k in sorted(c):
        print("连续 %d 轮: %d 次" % (k, c[k]))
    if runs:
        print("最长串=%d  平均串长=%.1f" % (max(runs), sum(runs)/len(runs)))

    print("\n=== 时段分段（每 1/4 轮次） ===")
    q = max(1, total // 4)
    for i in range(0, total, q):
        seg = rs[i:i+q]
        s = sum(1 for r in seg if r["stall"])
        print("轮 %3d-%3d: STALL %d/%d (%.0f%%)" % (seg[0]["n"], seg[-1]["n"], s, len(seg), 100.0*s/len(seg)))

    print("\n=== 端口号特征（STALL vs OK） ===")
    def port_stat(rsx, label):
        if not rsx:
            print("%s: 无" % label); return
        lo = min(r["port"] for r in rsx); hi = max(r["port"] for r in rsx)
        evens = sum(1 for r in rsx if r["port"] % 2 == 0)
        high = sum(1 for r in rsx if r["port"] >= 40000)
        print("%s: n=%d 范围=%d-%d 偶数=%.0f%%  >=40000=%.0f%%" % (label, len(rsx), lo, hi, 100.0*evens/len(rsx), 100.0*high/len(rsx)))
    port_stat(stalls, "STALL 轮")
    port_stat(oks, "OK 轮")

if __name__ == "__main__":
    main(sys.argv[1])