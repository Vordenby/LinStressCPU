# LinStressCPU

## Overview & Architecture
`LinStressCPU` is a deterministic CPU load generator designed for Linux environments. It provides integrated command-line and Tkinter-based graphical interfaces. The application manages independent worker processes, each executing a closed-loop busy-sleep cycle governed by configurable load coefficients and OS-level nice priorities. 

The workload engine utilizes floating-point mathematical operations (trigonometric, logarithmic, exponential, square-root) to generate sustained computational pressure. Exception handling (`ValueError`, `OverflowError`) is implemented at the worker level with automatic operand reset, ensuring continuous execution without process termination. Designed for stress testing, benchmarking, and system profiling under granular resource control.

## Parameter Logic
| Parameter | Acceptance | Default | Execution Logic |
|-----------|------------|---------|-----------------|
| `-t` / `--threads` | Integer `1–64` or `all` | System CPU count | Instantiates that many independent worker processes. `all` auto-detects available hardware threads. |
| `-l` / `--level` | `Low`, `Medium`, `Busy`, `Maximum` | `Maximum` | Establishes baseline load coefficient for all workers unless overridden by `--levels`. |
| `--levels` | Comma-separated values or floats `[0.0, 1.0]` | Not set | Per-worker load coefficients. Float inputs are clamped to the valid range during initialization. |
| `-d` / `--duration` | Seconds (integer) | `0` | Execution timeout. `0` enables indefinite run until `SIGINT`/`SIGTERM`. |
| `-p` / `--priority` | `Normal`, `High`, `Realtime` | `Normal` | Applies base nice value to all workers via `os.nice()` or `psutil`. Per-worker overrides supported. |
| `--priorities` | Comma-separated names or integers (nice) | Not set | Directly maps to OS scheduler weight. Requires root for values `< -19`. |

**Priority Mapping Reference:**  
`Normal` → `0` \| `High` → `-5` \| `Realtime` → `-20`

## Logging Standard
| Specification Attribute | Definition & Behavior |
|-------------------------|------------------------|
| **Log Directory** | `<application-directory>/logs/` |
| **Naming Convention** | `YYYY-MM-DD_HH-MM-SS.log` (ISO 8601 timestamp) |
| **Auto-Rotation Policy** | Upon session termination, the most recent log file is atomically copied to `latest_log.log`. |
| **Content Scope** | Timestamped run metadata, per-worker load coefficients, applied nice values, process IDs, and termination signals (`SIGINT`, duration expiration). |
| **Retention Management** | Manual cleanup or external log rotation recommended for production environments. |
