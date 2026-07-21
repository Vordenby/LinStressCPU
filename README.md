# LinStress v1.1‑stable  
## LinStress? 
LinStress is a command‑line and graphical tool that generates configurable CPU stress tests for system monitoring or benchmarking. It creates multiple worker processes with adjustable activity levels, nice priorities, and optional runtimes. The application logs all activities to files in `<app_dir>/logs/` while keeping the main loop clean.

## How It works?
1. **Execution** – The core `StressWorker` runs a mathematically stable loop (`sin·cos·tan·sqrt|x|·log(x+ε)·eˣ % 1e6`). If a numeric exception occurs it resets the value to 1.0, ensuring stability under high load.
2. **Worker Configuration** – Parameters: threads, load level (Low 0.25 – Maximum 1.0), duration, and nice priority (Realtime ‑20 – Normal). Each thread receives its own activity coefficient and nice value, allowing fine‑grained load control without crashes from overflow.
3. **Logging** – All messages are written by a dedicated `logging_utils.py` module to a timestamped file (`YYYY‑MM‑DD_HH‑MM‑SS.log`). The file `latest_log.log` always points to the active run and is copied when a new session starts. 

## Installation (&Uninstall)
### Automatic Installer (`install.sh`) – Recommended
#### WORKS ON Debian/Ubuntu-like, Fedora/RHEL/CentOS (& Red Hat‑distro's), Arch  
```bash
sudo curl -o /tmp/install.sh https://raw.githubusercontent.com/Vordenby/LinStressCPU/master/install.sh
sudo chmod +x /tmp/install.sh
sudo /tmp/install.sh
```
The script:  
* detects OS and package manager,  
* clones the repo to `/opt/LinStressCPU` (depth 1),  
* creates wrappers at `/usr/local/bin/linstresscpu*` and a desktop entry,  
* logs actions to `/var/log/linstresscpu/linstresscpu.log`.  

### Manual Installation  
```bash
git clone https://github.com/Vordenby/LinStressCPU.git /opt/LinStressCPU
cat > /usr/local/bin/linstresscpu <<EOF; exec python3 /opt/LinStressCPU/src/LinStress.py "$@"; EOF
cat > /usr/local/bin/linstresscpu-gui <<EOF; exec python3 /opt/LinStressCPU/src/LinStressGUI.py "$@"; EOF
chmod +x /usr/local/bin/linstresscpu*
# Desktop entry created automatically
```
### Uninstall  
```bash
sudo rm /usr/local/bin/linstresscpu*
sudo rm -rf /opt/LinStressCPU
sudo rm -rf /var/log/linstresscpu/*
rm /root/Desktop/LinStressCPU.desktop   # or ~/.local/share/applications/LinStressCPU.desktop if manual install
```

## Usage  

### Command‑Line (CLI)  
```bash
linstresscpu -t 8 -l Medium --duration 300 --priority High   # start 8 threads, level Medium, 5 min run, nice priority –5
```
* `-t` / `--threads`: number of workers (1‑64 or `all`).  
* `-l` : load level (`Low`, `Medium`, `Busy`, `Maximum`).  
* `--duration`: seconds; `0` = infinite.  
* `-p` : nice priority (`Realtime`, `High`, `Normal`).  

### Graphical Interface (GUI)  
A tiny Tkinter window lets you set the same parameters: number of threads, load level, duration, and default priority for each worker row.

## Quick Start Checklist  

| Step | Command / Action |
|------|-------------------|
| Install | Run `sudo /tmp/install.sh` |
| Verify CLI | `which linstresscpu` → `/usr/local/bin/linstresscpu` |
| Verify GUI | `which linstresscpu-gui` → `/usr/local/bin/linstresscpu-gui` |
| Test logs | `touch /var/log/linstresscpu/test.log` (should succeed) |