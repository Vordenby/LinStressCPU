import argparse
import multiprocessing
import time
import logging
import os
from typing import Optional, List

from logging_utils import close_application_logging, configure_application_logging
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
        self.logger = configure_application_logging(app_name="linstress_cli", base_dir=os.path.dirname(os.path.abspath(__file__)))

    def start(self):
        activities = []
        priorities = []

        if self.levels:
            raw_levels = self.levels
        else:
            raw_levels = [self.level]

        if self.priorities:
            raw_priorities = self.priorities
        else:
            raw_priorities = [self.priority]

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

        msg = f"Starting {self.threads} workers duration={self.duration}"
        print(msg)
        logging.info("CLI start requested: threads=%s duration=%s level=%s priority=%s", self.threads, self.duration, self.level, self.priority)

        for i in range(self.threads):
            activity = activities[i]
            nic = priorities[i]
            info = f"Starting worker {i+1}: activity={activity} nic={nic}"
            print(info)
            logging.info("CLI worker %s/%s configured: activity=%s nic=%s", i + 1, self.threads, activity, nic)
            p = StressWorker.start_process(activity=activity, duration=self.duration if self.duration and self.duration > 0 else None)
            self._set_priority(p.pid, nic)
            self.processes.append(p)
            logging.info("CLI worker %s started with pid=%s", i + 1, p.pid)

        try:
            if self.duration and self.duration > 0:
                end = time.time() + self.duration
                while time.time() < end:
                    time.sleep(0.5)
            else:
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            logging.info("CLI interrupted by user")
        finally:
            self.stop()
            close_application_logging(self.logger)

    def stop(self):
        if not self.processes:
            logging.info("CLI stop requested with no active workers")
            return

        logging.info("Stopping %s workers", len(self.processes))
        for p in self.processes:
            try:
                if p.is_alive():
                    logging.info("CLI terminating worker pid=%s", p.pid)
                    p.terminate()
            except Exception as e:
                logging.warning("CLI error terminating process %s: %s", p.pid, e)

        for p in self.processes:
            try:
                p.join(timeout=1)
            except Exception as e:
                logging.warning("CLI error joining process %s: %s", p.pid, e)

        self.processes = []
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
            logging.info("CLI set worker priority pid=%s nic=%s", pid, nic)
        except Exception as exc:
            logging.warning("CLI failed to set worker priority pid=%s nic=%s: %s", pid, nic, exc)


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
