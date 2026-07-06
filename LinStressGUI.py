import tkinter as tk
from tkinter import ttk
import multiprocessing
import logging
import os
import time
from typing import List, Optional

from logging_utils import close_application_logging, configure_application_logging
from stress import StressWorker

try:
    import psutil
except Exception:
    psutil = None


def validate_tkinter() -> None:
    try:
        import tkinter
    except Exception as exc:
        raise RuntimeError("Tkinter is not available or cannot be initialized: %s" % exc)


LEVEL_MAP = {"Low": 0.25, "Medium": 0.5, "Busy": 0.75, "Maximum": 1.0}
PRIORITY_MAP = {"Normal (0)": 0, "High (-5)": -5, "Realtime (-20)": -20}


class LinStressGUI:
    def __init__(self):
        validate_tkinter()
        self.logger = configure_application_logging(app_name="linstress_gui", base_dir=os.path.dirname(os.path.abspath(__file__)))

        self.root = tk.Tk()
        self.root.title("LinStress GUI")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.max_cpus = multiprocessing.cpu_count()

        controls = ttk.Frame(self.root)
        controls.pack(fill=tk.X, padx=8, pady=8)

        ttk.Label(controls, text="Threads:").grid(row=0, column=0, sticky=tk.W)
        self.threads_var = tk.IntVar(value=self.max_cpus)
        self.threads_spin = ttk.Spinbox(controls, from_=1, to=self.max_cpus, textvariable=self.threads_var, width=6, command=self.rebuild_rows)
        self.threads_spin.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(controls, text="Duration (s, 0=infinite):").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.duration_var = tk.IntVar(value=0)
        ttk.Entry(controls, textvariable=self.duration_var, width=10).grid(row=0, column=3, sticky=tk.W)

        ttk.Label(controls, text="Default Level:").grid(row=1, column=0, sticky=tk.W)
        self.default_level = tk.StringVar(value="Maximum")
        ttk.OptionMenu(controls, self.default_level, self.default_level.get(), *LEVEL_MAP.keys()).grid(row=1, column=1, sticky=tk.W)

        ttk.Label(controls, text="Default Priority:").grid(row=1, column=2, sticky=tk.W, padx=(10, 0))
        self.default_prio = tk.StringVar(value="Normal")
        ttk.OptionMenu(controls, self.default_prio, self.default_prio.get(), *PRIORITY_MAP.keys()).grid(row=1, column=3, sticky=tk.W)

        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        ttk.Button(btn_frame, text="Start", command=self.start).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Stop", command=self.stop).pack(side=tk.LEFT, padx=(6, 0))

        self.rows_frame = ttk.Frame(self.root)
        self.rows_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.level_vars: List[tk.StringVar] = []
        self.prio_vars: List[tk.StringVar] = []

        self.processes: List[multiprocessing.Process] = []

        self.rebuild_rows()

    def rebuild_rows(self):
        logging.info("GUI rebuilding worker rows for %s threads", self.threads_var.get())
        for child in self.rows_frame.winfo_children():
            child.destroy()

        self.level_vars = []
        self.prio_vars = []

        n = max(1, min(self.max_cpus, int(self.threads_var.get())))

        header = ttk.Frame(self.rows_frame)
        header.pack(fill=tk.X)
        ttk.Label(header, text="#", width=4).grid(row=0, column=0)
        ttk.Label(header, text="Level", width=20).grid(row=0, column=1)
        ttk.Label(header, text="Priority", width=20).grid(row=0, column=2)

        for i in range(n):
            f = ttk.Frame(self.rows_frame)
            f.pack(fill=tk.X, pady=2)
            ttk.Label(f, text=str(i + 1), width=4).grid(row=0, column=0)

            lv = tk.StringVar(value=self.default_level.get())
            self.level_vars.append(lv)
            ttk.OptionMenu(f, lv, lv.get(), *LEVEL_MAP.keys()).grid(row=0, column=1, sticky=tk.W)

            pv = tk.StringVar(value=self.default_prio.get())
            self.prio_vars.append(pv)
            ttk.OptionMenu(f, pv, pv.get(), *PRIORITY_MAP.keys()).grid(row=0, column=2, sticky=tk.W)

    def _set_priority(self, pid: int, nic: int):
        try:
            if psutil:
                p = psutil.Process(pid)
                p.nice(nic)
            else:
                os.setpriority(os.PRIO_PROCESS, pid, nic)
        except Exception:
            pass

    def start(self):
        self.stop()
        n = max(1, min(self.max_cpus, int(self.threads_var.get())))
        duration = int(self.duration_var.get())
        logging.info("GUI start requested: threads=%s duration=%s", n, duration)

        activities: List[float] = []
        nic_vals: List[int] = []

        for i in range(n):
            lv = self.level_vars[i].get()
            if lv in LEVEL_MAP:
                activities.append(LEVEL_MAP[lv])
            else:
                try:
                    activities.append(max(0.0, min(1.0, float(lv))))
                except Exception:
                    activities.append(1.0)

            pv = self.prio_vars[i].get()
            if pv in PRIORITY_MAP:
                nic_vals.append(PRIORITY_MAP[pv])
            else:
                try:
                    nic_vals.append(int(pv))
                except Exception:
                    nic_vals.append(0)

        logging.info("GUI starting %s workers duration=%s", n, duration)

        for i in range(n):
            act = activities[i]
            nic = nic_vals[i]
            logging.info("GUI worker %s configured: activity=%s nic=%s", i + 1, act, nic)
            p = StressWorker.start_process(activity=act, duration=duration if duration and duration > 0 else None)
            self._set_priority(p.pid, nic)
            self.processes.append(p)
            logging.info("GUI worker %s started with pid=%s", i + 1, p.pid)

    def stop(self):
        if not self.processes:
            return
        logging.info("GUI stopping %s workers", len(self.processes))
        for p in self.processes:
            try:
                if p.is_alive():
                    logging.info("GUI terminating worker pid=%s", p.pid)
                    p.terminate()
            except Exception as exc:
                logging.warning("GUI failed to terminate worker pid=%s: %s", p.pid, exc)

        for p in self.processes:
            try:
                p.join(timeout=1)
            except Exception as exc:
                logging.warning("GUI failed to join worker pid=%s: %s", p.pid, exc)

        self.processes = []
        logging.info("GUI workers stopped")

    def on_close(self):
        logging.info("GUI window closed")
        self.stop()
        close_application_logging(self.logger)
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        self.stop()
        close_application_logging(self.logger)


if __name__ == "__main__":
    gui = LinStressGUI()
    gui.run()
