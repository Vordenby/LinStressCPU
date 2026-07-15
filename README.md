# LinStress v1.1-stable Release Notes: Architecture, Stability and Deployment Guide

The LinStress v1.1-stable release introduces comprehensive architectural refinements designed to ensure process isolation reliability, telemetry integrity, and mathematical stability under high-load conditions. The system architecture has been modularized to separate logging concerns from the primary execution logic, while core worker processes now feature enhanced exception handling to prevent thread crashes due to numerical overflow.

---

## 1. Logging Architecture and Telemetry

The logging subsystem has been refactored into a dedicated utility module (`logging_utils.py`). This separation of concerns ensures that log file management does not interfere with the main application loop.

| Component | Responsibility | Implementation Detail |
|-----------|----------------|----------------------|
| `configure_application_logging()` | Initializes logger instance with directory structure | Generates timestamped filenames using ISO 8601 (`YYYY-MM-DD_HH-MM-SS`) |
| File Handler | Persistent logging output | Writes to `<base_dir>/logs/<timestamp>.log` format |
| Stream Handler | Console output for monitoring | Appends `[LEVEL]` prefix to all messages |
| `latest_log.log` | Active session indicator | Maintained as symlink-like marker pointing to current run |
| `close_application_logging()` | Cleanup and archival | Copies active log to `latest_log.log`, removes handlers, marks archive flag |

### Log Directory Structure

```
<application_dir>/
├── logs/
│   ├── latest_log.log          # Current active session
│   └── YYYY-MM-DD_HH-MM-SS.log  # Archived runs
```

---

## 2. Worker Configuration Parameters

The stress worker accepts multiple input configurations through both CLI and GUI interfaces.

| Parameter | Type | Default | Range/Values | Description |
|-----------|------|---------|---------------|-------------|
| `threads` | int/string | CPU count | 1–64 or "all" | Number of parallel workers to spawn |
| `level` | string/float | Maximum | Low (0.25), Medium (0.5), Busy (0.75), Maximum (1.0) | CPU load percentage per thread |
| `duration` | int | 0 (infinite) | ≥0 seconds | Runtime limit; 0 = continuous execution |
| `priority` | string/int | Normal | Realtime (-20), High (-5), Normal (0) | Process nice level |

### Priority Level Mapping

| Name | Nice Value | Privilege Required | Use Case |
|------|------------|--------------------|----------|
| Realtime | -20 | Root/Administrator | Maximum CPU access, system monitoring |
| High | -5 | Normal user | Background high-priority tasks |
| Normal | 0 | Normal user | Standard application workload |

### Load Level Mapping

| Name | Coefficient | Behavior |
|------|-------------|----------|
| Low | 0.25 | 25% busy, 75% idle |
| Medium | 0.50 | 50% busy, 50% idle |
| Busy | 0.75 | 75% busy, 25% idle |
| Maximum | 1.00 | Continuous busy loop |

---

## 3. Installation and Deployment

### Recommended: Automated Installer Script (`install.sh`)

The `install.sh` script provides a fully automated deployment solution designed for Linux distributions with package managers. This approach minimizes manual intervention and ensures correct system integration.

#### Prerequisites

| Requirement | Verification Command |
|-------------|---------------------|
| Root access | `sudo -l` or `su` to root user |
| Supported OS | Debian/Ubuntu, Fedora/RHEL, CentOS, Arch Linux |
| Bash 4+ | `bash --version` |
| Git (optional) | `git --version` |
| Python 3.6+ | `python3 --version` |

#### Installation Steps

1. **Obtain the script**
   ```bash
   sudo curl -o /tmp/install.sh https://raw.githubusercontent.com/Vordenby/LinStressCPU/master/install.sh
   sudo chmod +x /tmp/install.sh
   ```

2. **Execute installation**
   ```bash
   sudo /tmp/install.sh
   ```

#### Script Capabilities

| Feature | Description |
|---------|-------------|
| Dependency detection | Checks existing packages before installation |
| OS-specific package managers | Supports apt-get (Debian/Ubuntu), yum/dnf (RHEL/CentOS), pacman (Arch) |
| Source extraction | Clones repository to temporary directory with depth 1 |
| System paths creation | `/opt/LinStressCPU/src/` for application binaries |
| CLI wrapper installation | `/usr/local/bin/linstresscpu` symlink to Python script |
| GUI wrapper installation | `/usr/local/bin/linstresscpu-gui` with environment variables |
| Desktop entry generation | Creates `.desktop` file at user's Desktop directory |

#### Script Safety Features

```bash
set -euo pipefail  # Exit on error, undefined variable, pipe failure
check_root()       # Enforces root execution requirement
trap 'rm -rf "$TMP_DIR"' EXIT  # Cleans temporary directory on exit
```

| Failure Condition | Action Taken |
|-------------------|---------------|
| Non-root execution | Script exits with error message |
| Unsupported OS | Falls back to source code manual installation recommendation |
| Missing dependencies | Installs required packages automatically via system package manager |
| Repository clone failure | Exits immediately with detailed error in log file |

#### Log File Location

All installation events are recorded at `/var/log/linstresscpu/linstresscpu.log` with timestamps and severity levels.

---

### Alternative: Manual Installation (Source Code Deployment)

For environments requiring full source control or custom compilation paths.

| Step | Command | Purpose |
|------|---------|---------|
| 1. Clone repository | `git clone https://github.com/Vordenby/LinStressCPU.git /opt/LinStressCPU` | Download source code |
| 2. Create wrapper script (CLI) | `cat > /usr/local/bin/linstresscpu <<EOF; exec python3 /opt/LinStressCPU/src/LinStress.py "$@"; EOF` | CLI launcher |
| 3. Create wrapper script (GUI) | `cat > /usr/local/bin/linstresscpu-gui <<EOF; exec python3 /opt/LinStressCPU/src/LinStressGUI.py "$@"; EOF` | GUI launcher |
| 4. Set executable permissions | `chmod +x /usr/local/bin/linstresscpu*` | Make wrappers accessible |
| 5. Create desktop entry (optional) | See section below | Desktop menu integration |

---

## 4. System Integration Components

### Installation Directory Structure

```
/opt/LinStressCPU/src/
├── LinStress.py          # CLI application
├── LinStressGUI.py       # GUI application
└── stress.py             # Core worker module

/usr/local/bin/
├── linstresscpu          # CLI wrapper (symlink)
└── linstresscpu-gui      # GUI wrapper (symlink)

/etc/linstresscpu/        # Configuration directory
└── linstresscpu.conf     # Future configuration file

/var/log/linstresscpu/    # Log storage directory
├── linstresscpu.log      # Main log file
└── YYYY-MM-DD_*.log      # Archived logs by timestamp
```

### Desktop Integration

The installer creates a desktop entry for the GUI application. The location depends on execution context:

| Execution Context | Desktop Entry Location |
|-------------------|------------------------|
| Direct root execution | `/root/Desktop/LinStressCPU.desktop` |
| Sudo from other user | `${SUDO_USER}'s_home/`/Desktop/LinStressCPU.desktop` |
| Manual installation (non-root) | User's `~/.local/share/applications/` directory |

### Desktop Entry Configuration

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=LinStress CPU Stress Test
Comment=Vordenby's CPU Stress Test Tool
Exec=/usr/local/bin/linstresscpu-gui %i
Path=/opt/LinStressCPU/src
Terminal=false
Categories=Utility;System;
StartupNotify=true
TryExec=/usr/local/bin/linstresscpu-gui
```

---

## 5. Verification and Post-Installation Checklist

| Check | Command | Expected Result |
|-------|---------|-----------------|
| CLI availability | `which linstresscpu` | `/usr/local/bin/linstresscpu` |
| GUI wrapper available | `which linstresscpu-gui` | `/usr/local/bin/linstresscpu-gui` |
| Source files present | `ls /opt/LinStressCPU/src/` | `LinStress.py`, `LinStressGUI.py`, `stress.py` |
| Logs directory writable | `touch /var/log/linstresscpu/test.log` | Exit code 0 |
| Python3 availability | `python3 --version` | 3.6 or higher |

---

## 6. Uninstallation

| Method | Command | Effect |
|--------|---------|--------|
| Remove wrapper scripts | `sudo rm /usr/local/bin/linstresscpu*` | Removes CLI and GUI wrappers |
| Remove application directory | `sudo rm -rf /opt/LinStressCPU` | Removes source files |
| Clear logs | `sudo rm -rf /var/log/linstresscpu/*` | Removes log files |
| Remove desktop entry | Manual deletion from Desktop folder | Removes menu shortcut |

---

## 7. Deployment Constraints and Recommendations

| Constraint | Status | Recommendation |
|------------|--------|----------------|
| Root privileges required for install | Required | Use `sudo` or run as root |
| Python virtual environment compatibility | Not tested | Use system Python or create venv before install |
| Log file permissions | Owner must be root | Verify write permissions on `/var/log/linstresscpu/` |
| GUI display server (X11/Wayland) | Required for LinStressGUI.py | Ensure `$DISPLAY` is set |

---