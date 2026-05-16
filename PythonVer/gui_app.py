"""
Advanced GUI application implementing the requested interface elements.
Requires `psutil` for monitoring per-process CPU usage (recommended).
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import multiprocessing
import os
from typing import Optional, List, Dict

from stress import StressWorker

try:
    import psutil
except Exception:
    psutil = None


class AdvancedCPUStressGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LinStressCPU — GUI")
        self.geometry("700x480")

        self.threads_var = tk.StringVar(value=str(multiprocessing.cpu_count()))
        self.level_var = tk.StringVar(value="Maximum")
        self.duration_var = tk.IntVar(value=0)
        self.priority_var = tk.StringVar(value="Normal")

        self.processes: List[multiprocessing.Process] = []
        self.psutil_procs: Dict[int, 'psutil.Process'] = {}
        self.monitor_thread: Optional[threading.Thread] = None
        self.monitor_stop = threading.Event()

        self._build_ui()

    def _build_ui(self):
        main = ttk.Frame(self, padding=8)
        main.pack(fill=tk.BOTH, expand=True)

        controls = ttk.Frame(main)
        controls.pack(fill=tk.X)

        # Threads selection
        ttk.Label(controls, text="Threads:").grid(column=0, row=0, sticky=tk.W)
        self.threads_spin = ttk.Spinbox(controls, from_=1, to=64, textvariable=self.threads_var, width=6)
        self.threads_spin.grid(column=1, row=0, padx=6)
        ttk.Button(controls, text="All", command=self._set_all_threads).grid(column=2, row=0)

        # Level
        ttk.Label(controls, text="Level:").grid(column=0, row=1, sticky=tk.W)
        ttk.Combobox(controls, values=["Low", "Medium", "Busy", "Maximum"], textvariable=self.level_var, state="readonly").grid(column=1, row=1, padx=6)

        # Priority
        ttk.Label(controls, text="Priority:").grid(column=0, row=2, sticky=tk.W)
        ttk.Combobox(controls, values=["Normal", "High", "Realtime"], textvariable=self.priority_var, state="readonly").grid(column=1, row=2, padx=6)

        # Duration
        ttk.Label(controls, text="Duration (s):").grid(column=0, row=3, sticky=tk.W)
        ttk.Entry(controls, textvariable=self.duration_var, width=10).grid(column=1, row=3, padx=6)

        # Start / Stop
        self.start_btn = ttk.Button(controls, text="Start", command=self.start)
        self.start_btn.grid(column=0, row=4, pady=8)
        self.stop_btn = ttk.Button(controls, text="Stop", command=self.stop, state=tk.DISABLED)
        self.stop_btn.grid(column=1, row=4, pady=8)

        # Status and logs
        status_frame = ttk.LabelFrame(main, text="Status")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        # Treeview for threads
        cols = ("pid", "state", "cpu%")
        self.tree = ttk.Treeview(status_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=80)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        # Log panel
        log_frame = ttk.LabelFrame(main, text="Logs / Stats")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.log_text = tk.Text(log_frame, height=6)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Menu
        menubar = tk.Menu(self)
        settings_menu = tk.Menu(menubar, tearoff=0)
        self.autostart_var = tk.BooleanVar(value=False)
        settings_menu.add_checkbutton(label="Auto-start at launch", variable=self.autostart_var)
        settings_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        self.config(menu=menubar)

    def _set_all_threads(self):
        self.threads_var.set(str(multiprocessing.cpu_count()))

    def _show_about(self):
        messagebox.showinfo("About", "LinStressCPU — GUI\nOOP Python stress tester")

    def _log(self, msg: str):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_text.see(tk.END)

    def start(self):
        try:
            th = self.threads_var.get()
            threads = int(th)
            threads = max(1, min(64, threads))
        except Exception:
            threads = multiprocessing.cpu_count()

        level = self.level_var.get() or "Maximum"
        duration = self.duration_var.get()
        priority = self.priority_var.get() or "Normal"

        activity_map = {"Low": 0.25, "Medium": 0.5, "Busy": 0.75, "Maximum": 1.0}
        activity = activity_map.get(level, 1.0)

        self._log(f"Starting {threads} workers level={level} priority={priority} duration={duration}")

        self.processes = []
        self.psutil_procs = {}

        for _ in range(threads):
            p = StressWorker.start_process(activity=activity, duration=duration if duration and duration > 0 else None)
            self.processes.append(p)
            if psutil:
                try:
                    pp = psutil.Process(p.pid)
                    # initialize cpu percent
                    pp.cpu_percent(None)
                    self.psutil_procs[p.pid] = pp
                except Exception:
                    pass

        # set priority best-effort
        self._apply_priority_to_processes(priority)

        # populate tree
        self._refresh_tree()

        # start monitor
        self.monitor_stop.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

    def _apply_priority_to_processes(self, priority: str):
        for p in self.processes:
            try:
                if psutil:
                    proc = psutil.Process(p.pid)
                    if priority == "High":
                        proc.nice(-5)
                    elif priority == "Realtime":
                        proc.nice(-20)
                else:
                    # best-effort unix-like
                    if priority == "High":
                        os.setpriority(os.PRIO_PROCESS, p.pid, -5)
                    elif priority == "Realtime":
                        os.setpriority(os.PRIO_PROCESS, p.pid, -20)
            except Exception as e:
                self._log(f"Failed to set priority for {p.pid}: {e}")

    def _refresh_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for p in self.processes:
            state = "Running" if p.is_alive() else "Stopped"
            self.tree.insert("", tk.END, iid=str(p.pid), values=(p.pid, state, "0%"))

    def _monitor_loop(self):
        while not self.monitor_stop.is_set():
            total = 0.0
            count = 0
            for p in list(self.processes):
                cpu_pct = 0.0
                try:
                    if p.is_alive():
                        if psutil and p.pid in self.psutil_procs:
                            try:
                                cpu_pct = self.psutil_procs[p.pid].cpu_percent(interval=None) / multiprocessing.cpu_count()
                            except Exception:
                                cpu_pct = 0.0
                        else:
                            # approximate based on alive and level
                            cpu_pct = 100.0 if p.is_alive() else 0.0
                    else:
                        cpu_pct = 0.0
                except Exception:
                    cpu_pct = 0.0

                total += cpu_pct
                count += 1
                # update tree
                if str(p.pid) in self.tree.get_children():
                    try:
                        self.tree.set(str(p.pid), column="cpu%", value=f"{cpu_pct:.1f}%")
                        self.tree.set(str(p.pid), column="state", value=("Running" if p.is_alive() else "Stopped"))
                    except Exception:
                        pass

            avg = (total / count) if count else 0.0
            self._log(f"Average CPU (per core-normalized): {avg:.1f}%")

            if all(not p.is_alive() for p in self.processes):
                # all finished
                self.monitor_stop.set()
                self.stop()
                break

            time.sleep(1)

    def stop(self):
        self.monitor_stop.set()
        for p in self.processes:
            try:
                if p.is_alive():
                    p.terminate()
            except Exception:
                pass
        for p in self.processes:
            try:
                p.join()
            except Exception:
                pass

        self.processes = []
        self.psutil_procs = {}
        self._refresh_tree()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self._log("Stopped all workers")


if __name__ == "__main__":
    # Avoid showing GUI dialogs before Tk is fully available; just warn on console if psutil missing.
    if not psutil:
        print("Warning: psutil not installed — monitoring will be limited. Install with: pip install psutil")

    try:
        app = AdvancedCPUStressGUI()
        app.mainloop()
    except tk.TclError as e:
        # Common on macOS when the installed Tcl/Tk is incompatible with the OS/python build.
        print("Failed to start GUI (Tkinter/Tcl error):", e)
        print("On macOS you may need a newer Tcl/Tk. Install Python from python.org or install tcl-tk via Homebrew/ActiveTcl.")
        print("Fallback: run the CLI version:")
        print("  python3 ../cli_exe.py -t 2 -l Medium -d 5")
