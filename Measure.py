#!/usr/bin/env python3
"""Measure CPU usage by LinStress worker processes on Linux.

Run from the LinStressCPU directory:
  python3 Measure.py [--repeat 3] [--warmup 3] [--time 20] -- <LinStress command>

Examples:
  python3 Measure.py --repeat 3 -- python3 src/LinStress.py -t 1 -l Low -d 40
  python3 Measure.py --repeat 3 -- taskset -c 0 python3 src/LinStress.py -t 2 -l Maximum --priorities 0,5 -d 40

The script samples worker CPU usage every --step seconds and reports the mean
and standard deviation across runs. Multiprocessing service processes are excluded.
"""

import argparse
import os
import signal
import statistics
import subprocess
import sys
import time

PROC_ROOT = "/proc"


def positive_int(value):
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def non_negative_float(value):
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a non-negative number") from exc
    if not 0 <= parsed < float("inf"):
        raise argparse.ArgumentTypeError("must be a finite, non-negative number")
    return parsed


def positive_float(value):
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive number") from exc
    if not 0 < parsed < float("inf"):
        raise argparse.ArgumentTypeError("must be a finite, positive number")
    return parsed


def read_process_stat(pid):
    """Return a process's command name, CPU ticks, and nice value from /proc."""
    with open(f"{PROC_ROOT}/{pid}/stat", encoding="utf-8") as stat_file:
        stat = stat_file.read()
    command_end = stat.rfind(")")
    if command_end < 0:
        raise ValueError(f"invalid /proc/{pid}/stat contents")
    command = stat[stat.find("(") + 1:command_end]
    fields = stat[command_end + 2:].split()
    if len(fields) < 17:
        raise ValueError(f"incomplete /proc/{pid}/stat contents")
    cpu_ticks = int(fields[11]) + int(fields[12])
    nice = int(fields[16])
    return command, cpu_ticks, nice


def read_children(pid):
    """Return direct child PIDs listed by the Linux proc filesystem."""
    try:
        with open(f"{PROC_ROOT}/{pid}/task/{pid}/children", encoding="ascii") as children_file:
            contents = children_file.read()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return []
    return [int(child_pid) for child_pid in contents.split()]


def discover_workers(root_pid):
    """Find leaf processes beneath root_pid, excluding multiprocessing services."""
    children_by_pid = {}
    pending = [root_pid]
    visited = set()
    while pending:
        pid = pending.pop()
        if pid in visited:
            continue
        visited.add(pid)
        children = read_children(pid)
        children_by_pid[pid] = children
        pending.extend(children)

    workers = []
    for pid, children in children_by_pid.items():
        if children or pid == root_pid:
            continue
        try:
            command, cpu_ticks, nice = read_process_stat(pid)
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
            continue
        if "resource_tracker" not in command:
            workers.append((pid, cpu_ticks, nice))
    return sorted(workers)


def stop_process_tree(proc):
    """Terminate the command and all descendants in its dedicated process group."""
    kill_group = getattr(os, "killpg", None)
    if kill_group is None:
        raise RuntimeError("process-group termination is unavailable on this platform")
    try:
        kill_group(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    try:
        kill_group(proc.pid, getattr(signal, "SIGKILL", signal.SIGTERM))
    except ProcessLookupError:
        pass
    if proc.poll() is None:
        proc.wait()


def one_run(cmd, warmup, duration, step, ticks_per_second):
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        time.sleep(warmup)
        if proc.poll() is not None:
            raise RuntimeError(f"LinStress exited during startup with status {proc.returncode}")

        workers = discover_workers(proc.pid)
        if not workers:
            raise RuntimeError("no worker processes found; check the command")

        last_sample = {pid: (ticks, time.monotonic()) for pid, ticks, _ in workers}
        samples = {pid: [] for pid, _, _ in workers}
        nice_values = {pid: nice for pid, _, nice in workers}
        end = time.monotonic() + duration
        while time.monotonic() < end:
            time.sleep(min(step, max(0, end - time.monotonic())))
            now = time.monotonic()
            for pid in samples:
                try:
                    _, cpu_ticks, nice = read_process_stat(pid)
                except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
                    continue
                previous_ticks, previous_time = last_sample[pid]
                elapsed = now - previous_time
                if elapsed > 0:
                    cpu_percent = max(0, cpu_ticks - previous_ticks) / ticks_per_second / elapsed * 100
                    samples[pid].append(cpu_percent)
                last_sample[pid] = (cpu_ticks, now)
                nice_values[pid] = nice

        return [
            (pid, nice_values[pid], statistics.mean(samples[pid]) if samples[pid] else 0.0)
            for pid in sorted(samples)
        ]
    finally:
        stop_process_tree(proc)


def main():
    parser = argparse.ArgumentParser(description="Measure CPU usage by LinStress worker processes.")
    parser.add_argument("--repeat", type=positive_int, default=1, help="number of runs")
    parser.add_argument("--warmup", type=non_negative_float, default=3.0, help="startup delay in seconds")
    parser.add_argument("--time", type=positive_float, default=20.0, help="measurement duration in seconds")
    parser.add_argument("--step", type=positive_float, default=1.0, help="sampling interval in seconds")
    parser.add_argument("cmd", nargs=argparse.REMAINDER, help="LinStress command, placed after --")
    args = parser.parse_args()
    cmd = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
    if not cmd:
        parser.error("no LinStress command specified; provide it after --")
    if not sys.platform.startswith("linux"):
        parser.error("this script requires Linux and the /proc filesystem")

    sysconf = getattr(os, "sysconf", None)
    if sysconf is None:
        parser.error("the operating system does not expose process clock ticks")
    ticks_per_second = sysconf("SC_CLK_TCK")
    runs = []
    for run_number in range(args.repeat):
        try:
            results = one_run(cmd, args.warmup, args.time, args.step, ticks_per_second)
        except (OSError, RuntimeError) as exc:
            parser.error(f"run {run_number + 1} failed: {exc}")
        runs.append(results)
        line = "  ".join(
            f"[nice {nice}] {mean:5.1f}%" for _, nice, mean in results
        )
        total = sum(mean for _, _, mean in results)
        print(f"run {run_number + 1}: {line}   total {total:6.1f}%", flush=True)
        if run_number + 1 < args.repeat:
            time.sleep(1.0)

    worker_count = len(runs[0])
    print("\nResults across runs (processes in start order):")
    print(f"{'No.':>3} {'nice':>5} {'mean, %':>11} {'run σ':>11} {'share, %':>9}")
    means = []
    for worker_index in range(worker_count):
        values = [run[worker_index][2] for run in runs if len(run) == worker_count]
        means.append(statistics.mean(values))
    total_mean = sum(means)
    for worker_index, mean in enumerate(means):
        values = [run[worker_index][2] for run in runs if len(run) == worker_count]
        standard_deviation = statistics.pstdev(values) if len(values) > 1 else 0.0
        share = 100 * mean / total_mean if total_mean else 0
        print(
            f"{worker_index + 1:>3} {runs[0][worker_index][1]!s:>5} "
            f"{mean:11.1f} {standard_deviation:11.1f} {share:9.1f}"
        )
    print(f"{'total':>9} {total_mean:17.1f}   (logical CPUs: {os.cpu_count()})")


if __name__ == "__main__":
    main()
