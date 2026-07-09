# LinStressCPU  

LinStressCPU is a Python CPU‑stress testing utility designed as an analogue of **CPUStress** for Linux. It provides both a command‑line interface (`LinStress.py`) and a simple Tkinter GUI (`LinStressGUI.py`).  
The tool lets you create per‑thread load levels and priorities, monitor activity, and optionally run the stressers in background processes.

### Features  

- **CLI** – configure number of threads, duration, default level/priority, and individual per‑thread settings.  
- **Per‑thread load & priority** – each thread can have its own activity (0 → 1) and nice value (`Normal`, `High`, `Realtime`).  
- **Tkinter GUI** – step‑by‑step configuration of threads, duration, default level/priority and live start/stop.  
- **Logging** – detailed log files stored under a `logs/` directory (including “latest_log.log” and archived timestamped logs).  

---

## USAGE (CLI)

```
python LinStress.py -t <threads> \
    --level LEVEL \
    --duration <seconds|0> \
    -p PRIORITY \
    [--levels LEVEL,LEVEL,...] \
    [--priorities PRIO,PRIO,...]
```

| Option | Description |
|--------|-------------|
| `-t`, `--threads` | Number of workers (1‑64 or `all`). Default = CPU count. |
| `-l`, `--level`   | Default activity level: `Low` = 0.25, `Medium` = 0.5, `Busy` = 0.75, `Maximum` = 1.0. |
| `--duration`      | Test length in seconds (0 = infinite). |
| `-p`, `--priority| PRIORITY` | Default process priority: `Normal` (0), `High` (-5), `Realtime` (-20). |
| `--levels`        | Comma‑separated levels or floats for each thread. |
| `--priorities`    | Comma‑separated priorities (names or nice values) for each thread. |

*Examples*  

```bash
# 4 threads, individual levels & priorities, run 60 s:
python LinStress.py -t 4 --levels Low,Medium,0.9,Maximum \
    --priorities Normal,High,-10,Realtime -d 60

# Quick test with two threads:
python LinStress.py -t 2 --levels 0.5,0.2 --priorities 0,0 -d 5
```

---

## GUI USAGE  

```bash
python LinStressGUI.py
```

The GUI shows:

- **Threads** (max = system CPU count) – spinbox with a “+”/“-” button.  
- **Duration** – integer seconds (0 = infinite).  
- **Default Level / Priority** – drop‑downs that feed the same values as CLI.  

For each thread you can also edit its own level and priority before starting.

---

## NOTES & QUESTIONS  

| Topic | Details |
|-------|----------|
| **Dependencies** | Python 3.6+. Optional: `psutil` (only for niceness). The program works without it, using the lower‑level `os.setpriority`. |
| **Platform support** | Linux & macOS – both `psutil` and `os.setpriority` are available. <br>Windows – only `psutil` can set process priority; otherwise the tool falls back to no priority change (default). |
| **Thread limit** | Maximum is `max(1, cpu_count())`. You may request more threads but they will share CPU resources. |
| **Logging** | Files are written to `<project>/logs/YYYY‑MM‑DD_HH‑MM‑SS.log` plus a symbolic link `latest_log.log`. Each run creates a new timestamped file; archived logs stay in the directory. |
| **Process termination** | On Linux/macOS: `p.terminate()` → `os.setpriority(..., -20)` (Realtime) or normal nice value on exit. <br>Windows: priority is handled solely by `psutil`. |
| **PyInstaller** | The CLI script is marked as “suitable for PyInstaller”. To bundle logs, add `--add-data logs/;logs` to the spec file. |

---
