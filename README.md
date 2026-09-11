# LinStressCPU

LinStressCPU is a CPU load generator for Linux. It provides a command-line interface (CLI) and a Tkinter graphical interface (GUI). Each worker runs in a separate process and can use an independent load coefficient and process nice value.

## Operation

The application creates one `StressWorker` process per configured worker. Each process repeats a busy interval and, when the load coefficient is below `1.0`, a sleep interval.

| Component | Function |
| --- | --- |
| `src/stress.py` | Implements the worker process and CPU load loop. |
| `src/LinStress.py` | Parses CLI options, starts workers, applies priorities, and controls runtime. |
| `src/LinStressGUI.py` | Provides the Tkinter interface and per-worker configuration. |
| `src/logging_utils.py` | Creates timestamped run logs and updates `latest_log.log`. |

The load loop uses floating-point operations based on trigonometric, logarithmic, exponential, and square-root functions. `ValueError` and `OverflowError` are handled by resetting the working value.

## Requirements

| Requirement | Version or condition |
| --- | --- |
| Operating system | Linux for the automatic installer; Python execution is also supported on other systems with the required dependencies. |
| Python | Python 3 |
| Tkinter | Required for the GUI. |
| psutil | Listed in `requirements.txt`; used for process priority management when available. |
| Permissions | Root privileges are required by `Other/install.sh`. Raising a process priority may also require elevated privileges. |

## Installation

### Automatic installation

The installer supports Debian/Ubuntu, Fedora/RHEL/CentOS, Arch/Manjaro, and openSUSE/SUSE systems. It must be run as root.

```bash
curl -fsSL https://raw.githubusercontent.com/Vordenby/LinStressCPU/master/Other/install.sh -o /tmp/linstresscpu-install.sh
sudo chmod +x /tmp/linstresscpu-install.sh
sudo /tmp/linstresscpu-install.sh
```

The installer performs the following actions:

1. Detects the package manager.
2. Installs Python, pip, a virtual-environment package, and Tkinter.
3. Clones the repository to `/opt/LinStressCPU`.
4. Installs the `linstresscpu` and `linstresscpu-gui` commands in `/usr/local/bin`.
5. Creates CLI and GUI desktop entries in the target user's application directory and Desktop directory.
6. Writes installer logs to `/var/log/linstresscpu/linstresscpu.log`.

### Local execution

From a checkout of this repository:

```bash
python3 -m pip install -r requirements.txt
./run_gui.sh
./run_cli.sh
```

The launchers resolve the repository directory from their own location and can be called from any current working directory. `run_cli.sh` reads arguments from `CLI-Args.txt`.

## CLI

```bash
python3 src/LinStress.py --threads 8 --level Medium --duration 300 --priority High
```

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `-t`, `--threads` | `1`-`64` or `all` | CPU count | Number of worker processes. |
| `-l`, `--level` | `Low`, `Medium`, `Busy`, `Maximum` | `Maximum` | Load level applied to every worker unless per-worker levels are supplied. |
| `--levels` | Comma-separated levels or floats | Not set | Per-worker load values. Floats are clamped to `0.0`-`1.0`. |
| `-d`, `--duration` | Seconds | `0` | Run duration. `0` runs until interrupted. |
| `-p`, `--priority` | `Normal`, `High`, `Realtime` | `Normal` | Nice value applied to every worker unless per-worker priorities are supplied. |
| `--priorities` | Comma-separated names or integers | Not set | Per-worker nice values. |

Priority mappings:

| Name | Nice value |
| --- | ---: |
| `Normal` | `0` |
| `High` | `-5` |
| `Realtime` | `-20` |

Stop an indefinite run with `Ctrl+C`.

## CLI-Args.txt

`run_cli.sh` reads non-empty lines from `CLI-Args.txt`. Lines beginning with `#` are ignored. Whitespace separates arguments, so the following file is equivalent to the CLI command shown above except for the selected values:

```text
-t 2
-l Medium
-d 60
-p Normal
```

## GUI

Run `./run_gui.sh` or `linstresscpu-gui` after installation. The GUI exposes the following controls:

| Control | Description |
| --- | --- |
| Threads | Number of worker rows and processes. |
| Duration | Runtime in seconds; `0` means no time limit. |
| Default Level | Initial load level for worker rows. |
| Default Priority | Initial priority for worker rows. |
| Per-worker Level | Load level for an individual worker. |
| Per-worker Priority | Nice value for an individual worker. |
| Start / Stop | Starts or terminates the configured worker processes. |

## Logging

Logs are stored in `<application-directory>/logs/`. Each run creates a file with the format `YYYY-MM-DD_HH-MM-SS.log`. The most recent run is copied to `latest_log.log` when logging is closed.

## Installed files

| Path | Purpose |
| --- | --- |
| `/opt/LinStressCPU/src` | Application source files. |
| `/usr/local/bin/linstresscpu` | CLI command wrapper. |
| `/usr/local/bin/linstresscpu-gui` | GUI command wrapper. |
| `~/.local/share/applications/LinStressCPU.desktop` | GUI application entry. |
| `~/.local/share/applications/LinStressCPU-CLI.desktop` | CLI application entry. |
| `/var/log/linstresscpu/linstresscpu.log` | Installer log. |

## Uninstallation

```bash
sudo rm -f /usr/local/bin/linstresscpu /usr/local/bin/linstresscpu-gui
sudo rm -rf /opt/LinStressCPU /var/log/linstresscpu
rm -f ~/.local/share/applications/LinStressCPU.desktop
rm -f ~/.local/share/applications/LinStressCPU-CLI.desktop
rm -f ~/Desktop/LinStressCPU.desktop
rm -f ~/Desktop/LinStressCPU-CLI.desktop
```
