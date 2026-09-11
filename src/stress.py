import math as m
import time
import multiprocessing
from typing import Optional


class StressWorker:

    def __init__(self, activity: float = 1.0, duration: Optional[float] = None):
        self.activity = max(0.0, min(1.0, activity))
        self.duration = duration if duration and duration > 0 else None
        self.cycle = 0.05

    def run(self):
        end_time = time.time() + self.duration if self.duration else None
        x = 1.0

        while True:
            t0 = time.time()
            busy_end = t0 + self.cycle * self.activity

            while time.time() < busy_end:
                try:
                    x = (m.sin(x) * m.cos(x) * m.tan(x) * m.sqrt(abs(x)) * m.log(abs(x) + 1e-10) * m.exp(x)) % 1e6
                except (ValueError, OverflowError):
                    x = 1.0

            sleep_time = self.cycle * (1.0 - self.activity)
            if sleep_time > 0:
                time.sleep(sleep_time)

            if end_time and time.time() >= end_time:
                break

    @staticmethod
    def start_process(activity: float = 1.0, duration: Optional[float] = None) -> multiprocessing.Process:
        worker = StressWorker(activity=activity, duration=duration)
        p = multiprocessing.Process(target=worker.run)
        p.start()
        return p

def STRESS():
    StressWorker(activity=1.0, duration=None).run()