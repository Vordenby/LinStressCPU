import tkinter as tk
from tkinter import messagebox, ttk
import multiprocessing
import os
from typing import List

from logging_utils import close_application_logging, configure_application_logging
from stress import StressWorker

try:
    import psutil
except Exception:
    psutil = None


LEVEL_MAP = {"Low": 0.25, "Medium": 0.5, "Busy": 0.75, "Maximum": 1.0}
PRIORITY_MAP = {"Normal (0)": 0, "High (-5)": -5, "Realtime (-20)": -20}


class LinStressGUI:
    def __init__(self):
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
        self.threads_spin.bind("<Return>", self._on_thread_count_edit)
        self.threads_spin.bind("<FocusOut>", self._on_thread_count_edit)
        self.threads_spin.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(controls, text="Duration (s, 0=infinite):").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.duration_var = tk.IntVar(value=0)
        ttk.Entry(controls, textvariable=self.duration_var, width=10).grid(row=0, column=3, sticky=tk.W)

        ttk.Label(controls, text="Default Level:").grid(row=1, column=0, sticky=tk.W)
        self.default_level = tk.StringVar(value="Maximum")
        ttk.OptionMenu(controls, self.default_level, self.default_level.get(), *LEVEL_MAP.keys()).grid(row=1, column=1, sticky=tk.W)

        ttk.Label(controls, text="Default Priority:").grid(row=1, column=2, sticky=tk.W, padx=(10, 0))
        self.default_prio = tk.StringVar(value="Normal (0)")
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
        try:
            n = max(1, min(self.max_cpus, int(self.threads_var.get())))
        except (tk.TclError, ValueError):
            self.logger.warning("Ignoring invalid thread count while rebuilding worker rows")
            return

        previous_levels = [variable.get() for variable in self.level_vars]
        previous_priorities = [variable.get() for variable in self.prio_vars]
        if self.threads_var.get() != n:
            self.threads_var.set(n)
        self.logger.info("GUI rebuilding worker rows for %s threads", n)
        for child in self.rows_frame.winfo_children():
            child.destroy()

        self.level_vars = []
        self.prio_vars = []

        header = ttk.Frame(self.rows_frame)
        header.pack(fill=tk.X)
        ttk.Label(header, text="#", width=4).grid(row=0, column=0)
        ttk.Label(header, text="Level", width=20).grid(row=0, column=1)
        ttk.Label(header, text="Priority", width=20).grid(row=0, column=2)

        for i in range(n):
            f = ttk.Frame(self.rows_frame)
            f.pack(fill=tk.X, pady=2)
            ttk.Label(f, text=str(i + 1), width=4).grid(row=0, column=0)

            level = previous_levels[i] if i < len(previous_levels) else self.default_level.get()
            lv = tk.StringVar(value=level)
            self.level_vars.append(lv)
            ttk.OptionMenu(f, lv, lv.get(), *LEVEL_MAP.keys()).grid(row=0, column=1, sticky=tk.W)

            priority = previous_priorities[i] if i < len(previous_priorities) else self.default_prio.get()
            pv = tk.StringVar(value=priority)
            self.prio_vars.append(pv)
            ttk.OptionMenu(f, pv, pv.get(), *PRIORITY_MAP.keys()).grid(row=0, column=2, sticky=tk.W)

    def _on_thread_count_edit(self, event: tk.Event):
        self.logger.debug("Thread count edit completed via %s", event.type)
        self.rebuild_rows()

    def _set_priority(self, pid: int, nic: int):
        try:
            if psutil:
                p = psutil.Process(pid)
                p.nice(nic)
            else:
                setpriority = getattr(os, "setpriority", None)
                process_priority = getattr(os, "PRIO_PROCESS", None)
                if setpriority is None or process_priority is None:
                    raise NotImplementedError("Process priority changes are unavailable on this platform")
                setpriority(process_priority, pid, nic)
            self.logger.info("GUI set worker priority pid=%s nic=%s", pid, nic)
        except Exception as exc:
            self.logger.warning("GUI failed to set worker priority pid=%s nic=%s: %s", pid, nic, exc)

    def start(self):
        self.stop()
        try:
            n = max(1, min(self.max_cpus, int(self.threads_var.get())))
        except (tk.TclError, ValueError):
            messagebox.showerror("Invalid thread count", "Enter a whole number of threads.")
            return
        if len(self.level_vars) != n:
            self.rebuild_rows()
        try:
            duration = abs(int(self.duration_var.get()))
        except (tk.TclError, ValueError):
            messagebox.showerror("Invalid duration", "Enter a non-negative whole number of seconds.")
            return

        self.logger.info("GUI start requested: threads=%s duration=%s", n, duration)

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

        self.logger.info("GUI starting %s workers duration=%s", n, duration)

        try:
            for i in range(n):
                act = activities[i]
                nic = nic_vals[i]
                self.logger.info("GUI worker %s configured: activity=%s nic=%s", i + 1, act, nic)
                p = StressWorker.start_process(activity=act, duration=duration if duration > 0 else None)
                self.processes.append(p)
                if p.pid is not None:
                    self._set_priority(p.pid, nic)
                else:
                    self.logger.warning("GUI worker %s started without a process ID", i + 1)
                self.logger.info("GUI worker %s started with pid=%s", i + 1, p.pid)
        except Exception as exc:
            self.logger.exception("GUI failed to start workers")
            self.stop()
            messagebox.showerror("Worker startup failed", "Could not start all workers: %s" % exc)

    def stop(self):
        if not self.processes:
            return
        self.logger.info("GUI stopping %s workers", len(self.processes))
        for p in self.processes:
            try:
                if p.is_alive():
                    self.logger.info("GUI terminating worker pid=%s", p.pid)
                    p.terminate()
            except Exception as exc:
                self.logger.warning("GUI failed to terminate worker pid=%s: %s", p.pid, exc)

        remaining = []
        for p in self.processes:
            try:
                p.join(timeout=1)
                if p.is_alive():
                    self.logger.warning("GUI worker pid=%s did not stop after terminate; killing it", p.pid)
                    p.kill()
                    p.join(timeout=1)
                if p.is_alive():
                    self.logger.error("GUI worker pid=%s is still running after kill", p.pid)
                    remaining.append(p)
            except Exception as exc:
                self.logger.warning("GUI failed to join worker pid=%s: %s", p.pid, exc)
                remaining.append(p)

        self.processes = remaining
        if not remaining:
            self.logger.info("GUI workers stopped")

    def on_close(self):
        self.logger.info("GUI window closed")
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
