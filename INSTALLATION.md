# Installation

## 1. System‑wide installation (Ubuntu, Debian, Fedora, CentOS, RHEL, Arch)

If you are on any of the following distributions, run **install.sh** with root privileges:

```bash
sudo bash /install.sh
```

The script will create a `bin/` directory, place both `LinStress.py` and `LinStressGUI.py` there, make them executable, and set up basic permissions.

---

## 2. Manual installation (any other OS)

For systems **not** covered by the script above you have to:

1. **Download the source files**  
   - The project is distributed as a archive here https://github.com/Vordenby/LinStressCPU/releases, or it can be extracted from GitHub by terminal:  

     ```bash
     git clone https://github.com/Vordenby/LinStress.git
     cd LinStress
     ```

2. **Run the programs** with Python 3:

   ```bash
   python3 ./LinStress.py          # command‑line version
   python3 ./LinStressGUI.py       # graphical version
   ```

   *If `python3` is not in your PATH, use `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.*

---