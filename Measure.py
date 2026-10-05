#!/usr/bin/env python3

import argparse, subprocess, time, statistics, sys
import psutil

ap = argparse.ArgumentParser()
ap.add_argument("--repeat", type=int, default=1)
ap.add_argument("--warmup", type=float, default=3.0)
ap.add_argument("--time", type=float, default=20.0)
ap.add_argument("--step", type=float, default=1.0)
ap.add_argument("cmd", nargs=argparse.REMAINDER)
a = ap.parse_args()
cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
if not cmd:
    sys.exit("No LinStress command specified (after --)")

SERVICE = ("forkserver", "resource_tracker")

def is_worker(p):
    try:
        line = " ".join(p.cmdline())
    except psutil.Error:
        return False
    return not any(s in line for s in SERVICE)

def one_run():
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(a.warmup)
    root = psutil.Process(proc.pid)
    workers = [p for p in root.children(recursive=True) if is_worker(p)]
    if not workers:
        proc.terminate()
        sys.exit("No worker processes found: check the command")
    for w in workers:
        w.cpu_percent(None)
    samples = {w.pid: [] for w in workers}
    end = time.time() + a.time
    while time.time() < end:
        time.sleep(a.step)
        for w in workers:
            try:
                samples[w.pid].append(w.cpu_percent(None))
            except psutil.Error:
                pass
    res = []
    for w in workers:
        s = samples[w.pid]
        try: ni = w.nice()
        except psutil.Error: ni = None
        res.append((w.pid, ni, statistics.mean(s) if s else 0.0))
    res.sort()
    proc.terminate()
    try: proc.wait(5)
    except Exception: proc.kill()
    return res

runs = []
for r in range(a.repeat):
    res = one_run()
    runs.append(res)
    line = "  ".join(f"[nice {ni}] {m:5.1f}%" for _, ni, m in res)
    print(f"run {r+1}: {line}   total {sum(m for _,_,m in res):6.1f}%", flush=True)
    time.sleep(1.0)

n = len(runs[0])
print("\nResults across runs (processes in start order):")
print(f"{'No.':>3} {'nice':>5} {'mean, %':>11} {'run σ':>11} {'share, %':>9}")
means = []
for i in range(n):
    vals = [run[i][2] for run in runs if len(run) == n]
    means.append(statistics.mean(vals))
tot = sum(means)
for i in range(n):
    vals = [run[i][2] for run in runs if len(run) == n]
    sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    print(f"{i+1:>3} {runs[0][i][1]!s:>5} {means[i]:11.1f} {sd:11.1f} {100*means[i]/tot if tot else 0:9.1f}")
print(f"{'total':>9} {tot:17.1f}   (logical CPUs: {psutil.cpu_count()})")