
import argparse
import multiprocessing
import time
import logging
import os
from typing import Optional, List

from stress import StressWorker

try:
    import psutil
except Exception:
    psutil = None


class CLIStressRunner:
    LEVEL_MAP = {"Low": 0.25, "Medium": 0.5, "Busy": 0.75, "Maximum": 1.0}
    PRIORITY_MAP = {
        "Normal": 0,
        "High": -5,
        "Realtime": -20,
    }

    def __init__(self, threads: int, level: str, duration: Optional[int], priority: str,
                 levels: Optional[List[str]] = None, priorities: Optional[List[str]] = None,
                 logfile: Optional[str] = "linstress.log"):
        self.threads = threads
        self.level = level
        self.duration = duration
        self.priority = priority
        self.levels = levels
        self.priorities = priorities
        self.processes = []

        logging.basicConfig(filename=logfile, level=logging.INFO, format="%(asctime)s %(message)s")

    def start(self):
        # Build per-thread activity and priority lists
        activities = []
        priorities = []

        # Normalize levels
        if self.levels:
            raw_levels = self.levels
        else:
            raw_levels = [self.level]

        # Normalize priorities
        if self.priorities:
            raw_priorities = self.priorities
        else:
            raw_priorities = [self.priority]

        # Helper to expand/truncate lists to thread count
        def normalize_list(lst, default, count):
            if not lst:
                return [default] * count
            if len(lst) == 1:
                return [lst[0]] * count
            if len(lst) < count:
                return lst + [lst[-1]] * (count - len(lst))
            return lst[:count]

        raw_levels = normalize_list(raw_levels, self.level, self.threads)
        raw_priorities = normalize_list(raw_priorities, self.priority, self.threads)

        # Convert levels to activity floats
        for lv in raw_levels:
            lv = lv.strip()
            if lv in self.LEVEL_MAP:
                activities.append(self.LEVEL_MAP[lv])
            else:
                try:
                    f = float(lv)
                    activities.append(max(0.0, min(1.0, f)))
                except Exception:
                    activities.append(self.LEVEL_MAP.get(self.level, 1.0))

        # Convert priorities to nic ints
        for pr in raw_priorities:
            pr = pr.strip()
            if pr in self.PRIORITY_MAP:
                priorities.append(self.PRIORITY_MAP[pr])
            else:
                try:
                    nic = int(pr)
                    priorities.append(nic)
                except Exception:
                    priorities.append(self.PRIORITY_MAP.get(self.priority, 0))

        logging.info(f"Starting {self.threads} workers duration={self.duration}")

        for i in range(self.threads):
            activity = activities[i]
            nic = priorities[i]
            logging.info(f"Starting worker {i+1}: activity={activity} nic={nic}")
            p = StressWorker.start_process(activity=activity, duration=self.duration if self.duration and self.duration > 0 else None)
            self._set_priority(p.pid, nic)
            self.processes.append(p)

        try:
            if self.duration and self.duration > 0:
                end = time.time() + self.duration
                while time.time() < end:
                    time.sleep(0.5)
            else:
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Interrupted by user")
        finally:
            self.stop()

    def stop(self):
        logging.info("Stopping workers")
        for p in self.processes:
            try:
                if p.is_alive():
                    p.terminate()
            except Exception as e:
                logging.info(f"Error terminating process {p.pid}: {e}")

        for p in self.processes:
            try:
                p.join()
            except Exception:
                pass

        logging.info("All workers stopped")

    def _set_priority(self, pid: int, nic: Optional[int] = None):
        if nic is None:
            nic = self.PRIORITY_MAP.get(self.priority, 0)
        try:
            if psutil:
                p = psutil.Process(pid)
                p.nice(nic)
            else:
                os.setpriority(os.PRIO_PROCESS, pid, nic)
        except Exception:
            pass


def parse_args():
    parser = argparse.ArgumentParser(description="CLI-only CPU stress runner (suitable for PyInstaller)")
    parser.add_argument("-t", "--threads", type=str, default=str(multiprocessing.cpu_count()), help="Number of workers: 1..64 or 'all' (default: cpu count)")
    parser.add_argument("-l", "--level", choices=list(CLIStressRunner.LEVEL_MAP.keys()), default="Maximum", help="Load level")
    parser.add_argument("--levels", type=str, default=None, help="Per-thread comma-separated levels or floats (e.g. 'Low,Medium,1.0')")
    parser.add_argument("-d", "--duration", type=int, default=0, help="Duration seconds (0 = infinite)")
    parser.add_argument("-p", "--priority", choices=list(CLIStressRunner.PRIORITY_MAP.keys()), default="Normal", help="Priority")
    parser.add_argument("--priorities", type=str, default=None, help="Per-thread comma-separated priorities or nice values (e.g. 'Normal,High,-10')")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.threads.lower() == "all":
        threads = multiprocessing.cpu_count()
    else:
        try:
            threads = int(args.threads)
            threads = max(1, min(64, threads))
        except Exception:
            threads = multiprocessing.cpu_count()
    levels = None
    priorities = None
    if args.levels:
        levels = [s.strip() for s in args.levels.split(',') if s.strip()]
    if args.priorities:
        priorities = [s.strip() for s in args.priorities.split(',') if s.strip()]

    runner = CLIStressRunner(threads=threads, level=args.level, duration=args.duration, priority=args.priority,
                             levels=levels, priorities=priorities)
    runner.start()
