
import argparse
import multiprocessing
import time
import logging
import os
from typing import Optional

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

    def __init__(self, threads: int, level: str, duration: Optional[int], priority: str, logfile: Optional[str] = "linstress.log"):
        self.threads = threads
        self.level = level
        self.duration = duration
        self.priority = priority
        self.processes = []

        logging.basicConfig(filename=logfile, level=logging.INFO, format="%(asctime)s %(message)s")

    def start(self):
        activity = self.LEVEL_MAP.get(self.level, 1.0)
        logging.info(f"Starting {self.threads} workers level={self.level} activity={activity} priority={self.priority} duration={self.duration}")

        for _ in range(self.threads):
            p = StressWorker.start_process(activity=activity, duration=self.duration if self.duration and self.duration > 0 else None)
            self._set_priority(p.pid)
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

    def _set_priority(self, pid: int):
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
    parser.add_argument("-d", "--duration", type=int, default=0, help="Duration seconds (0 = infinite)")
    parser.add_argument("-p", "--priority", choices=list(CLIStressRunner.PRIORITY_MAP.keys()), default="Normal", help="Priority")
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

    runner = CLIStressRunner(threads=threads, level=args.level, duration=args.duration, priority=args.priority)
    runner.start()
