#!/usr/bin/env bash

set -euo pipefail

APP_NAME="LinStressCPU"
REPO_URL="https://github.com/Vordenby/LinStressCPU.git"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0;m'

LOG_FILE="/var/log/linstresscpu/linstresscpu.log"
TMP_DIR=$(mktemp -d)

log_message() {
    local level="$1"; shift
    local message="$*"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    mkdir -p "$(dirname "$LOG_FILE")"
    echo "$timestamp [$level] $message" >> "$LOG_FILE"

    if [[ "$level" == "ERROR" ]]; then
        echo -e "\e[31mERROR:\e[0m $message" >&2
    fi
}

log_message "INFO" "Created temporary directory: $TMP_DIR"

cd "$TMP_DIR" || exit 1

check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_message "INFO" "Running as root."
    else
        log_message "ERROR" "The script must be run as root."
        echo -e "${RED}The script must be run as root.${NC}"
        sleep 3
        exit 1
    fi
}

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        PMGR=""

        if command -v apt-get >/dev/null 2>&1 && [ -d /etc/apt ]; then
            PMGR="apt"
            log_message "INFO" "Detected a Debian-like system (apt)."
            return 0
        fi

        if [ -f /etc/dnf.conf ]; then
            PMGR="dnf"
            log_message "INFO" "Detected a dnf-based system (Fedora, RHEL, or CentOS)."
            return 0
        fi

        if [ -f /etc/pacman.conf ]; then
            PMGR="pacman"
            log_message "INFO" "Detected a pacman-based system (Arch or Manjaro)."
            return 0
        fi

        if [ -f /etc/zypper.conf ]; then
            PMGR="zypper"
            log_message "INFO" "Detected a zypper-based system (openSUSE or SUSE)."
            return 0
        fi

        case "$ID" in
            ubuntu|debian|kali|raspbian|ubuntu-kylin|astra|astra-linux)
                PMGR="apt"
                ;;
            fedora|centos|rhel|redhat|amazon)
                PMGR="dnf"
                ;;
            arch|manjaro)
                PMGR="pacman"
                ;;
            openSUSE|suse)
                PMGR="zypper"
                ;;
        esac

        if [[ "$PMGR" != "apt" && "$PMGR" != "dnf" && "$PMGR" != "pacman" && "$PMGR" != "zypper" ]]; then
            echo -e "${GREEN}Could not detect the distribution automatically.${NC}"
            echo "Please select your distribution:"
            echo "1) Debian-like (Ubuntu, Debian, Kali, Astra Linux)"
            echo "2) RHEL/CentOS/Fedora"
            echo "3) Arch/Manjaro"
            echo "4) openSUSE/SUSE"

            read -p "Select your distribution (1-4): " choice

            case "$choice" in
                1)
                    PMGR="apt"
                    ;;
                2)
                    PMGR="dnf"
                    ;;
                3)
                    PMGR="pacman"
                    ;;
                4)
                    PMGR="zypper"
                    ;;
                *)
                    log_message "ERROR" "Invalid distribution selection."
                    echo -e "${RED}Invalid selection.${NC}"
                    sleep 3
                    exit 1
                    ;;
            esac

            log_message "INFO" "User selected package manager: $PMGR"
        fi
    else
        log_message "ERROR" "/etc/os-release was not found."
        echo -e "${RED}/etc/os-release was not found.${NC} Try installing from source instead."
        sleep 3
        exit 1
    fi
}

install_deps() {
    local -a deps=()

    case "$PMGR" in
        apt)
            deps=(python3 python3-pip python3-venv)
            ;;
        dnf|yum)
            deps=(python3 python3-pip python3-virtualenv python3-tkinter)
            ;;
        pacman)
            deps=(python3 python3-pip python3-virtualenv python3-tk)
            ;;
        zypper)
            deps=(python3 python3-pip python3-venv python3-tk)
            ;;
    esac

    if [[ "$PMGR" == "apt" ]]; then
        log_message "INFO" "Refreshing apt package metadata."
        local -a apt_source_files=(/etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources)
        local source_file
        local has_active_sources=0
        local has_commented_sources=0

        for source_file in "${apt_source_files[@]}"; do
            [[ -f "$source_file" ]] || continue
            if grep -Eq '^[[:space:]]*deb([[:space:]]|\[)' "$source_file" || \
                { [[ "$source_file" == *.sources ]] && grep -Eq '^[[:space:]]*Types:[[:space:]].*deb' "$source_file"; }; then
                has_active_sources=1
            fi
            if [[ "$source_file" == *.list ]] && grep -Eq '^[[:space:]]*#[[:space:]]*deb([[:space:]]|\[)' "$source_file"; then
                has_commented_sources=1
            fi
        done

        if [[ "$has_active_sources" -eq 0 && "$has_commented_sources" -eq 1 ]]; then
            local source_backup_dir="/var/backups/linstresscpu/apt-sources-$(date +%Y%m%d%H%M%S)"
            mkdir -p "$source_backup_dir"
            log_message "INFO" "No active apt sources found. Backing up and enabling commented deb entries."

            for source_file in "${apt_source_files[@]}"; do
                [[ -f "$source_file" ]] || continue
                if grep -Eq '^[[:space:]]*#[[:space:]]*deb([[:space:]]|\[)' "$source_file"; then
                    cp -p "$source_file" "$source_backup_dir/"
                    sed -i -E 's/^([[:space:]]*)#[[:space:]]*(deb([[:space:]]|\[).*)$/\1\2/' "$source_file"
                fi
            done
        fi

        if [[ "$has_active_sources" -eq 0 && "$has_commented_sources" -eq 0 ]]; then
            log_message "ERROR" "No apt sources were found. Add the official Astra Linux repository to /etc/apt/sources.list or /etc/apt/sources.list.d, then run the installer again."
            echo -e "${RED}No apt sources were found.${NC} Add the official Astra Linux repository to /etc/apt/sources.list or /etc/apt/sources.list.d, then run the installer again."
            exit 1
        fi

        if ! apt-get -o Acquire::Retries=3 update; then
            log_message "WARNING" "apt update failed. Removing incomplete package indexes and retrying."
            rm -rf /var/lib/apt/lists/partial
            if ! apt-get -o Acquire::Retries=3 update; then
                log_message "ERROR" "apt package metadata could not be refreshed. Check repository URLs, signing keys, and network access."
                echo -e "${RED}Could not refresh apt package metadata.${NC} Check repository URLs, signing keys, and network access."
                exit 1
            fi
        fi

        local tkinter_pkg=""
        local candidate
        for candidate in python3-tk python3-tkinter; do
            if apt-cache show "$candidate" >/dev/null 2>&1; then
                tkinter_pkg="$candidate"
                break
            fi
        done

        if [[ -z "$tkinter_pkg" ]]; then
            log_message "ERROR" "No Tkinter package is available in the configured apt repositories. Tkinter cannot be installed with pip; enable the Astra Linux repository that contains python3-tk or python3-tkinter."
            echo -e "${RED}No Tkinter package is available in the configured apt repositories.${NC}"
            echo "Enable an Astra Linux repository containing python3-tk or python3-tkinter, then run the installer again."
            exit 1
        fi

        deps+=("$tkinter_pkg")
        log_message "INFO" "Using Tkinter package: $tkinter_pkg"
    fi

    for pkg in "${deps[@]}"; do
        case "$PMGR" in
            apt)
                if ! dpkg -s "$pkg" >/dev/null 2>&1; then
                    log_message "INFO" "Installing $pkg..."
                    apt-get install -y --no-install-recommends "$pkg"
                fi
                ;;
            yum|dnf)
                if ! rpm -q "$pkg" >/dev/null 2>&1; then
                    log_message "INFO" "Installing $pkg..."
                    yum install -y --skip-broken "$pkg"
                fi
                ;;
            pacman)
                if ! pacman -Qi "$pkg" >/dev/null 2>&1; then
                    log_message "INFO" "Installing $pkg..."
                    pacman -S --noconfirm "$pkg"
                fi
                ;;
            zypper)
                if ! zypper se -x "$pkg" >/dev/null 2>&1; then
                    log_message "INFO" "Installing $pkg..."
                    zypper install -y --no-confirm "$pkg"
                fi
                ;;
        esac
    done

    if ! python3 -c 'import tkinter' >/dev/null 2>&1; then
        log_message "ERROR" "Python Tkinter is still unavailable after dependency installation."
        echo -e "${RED}Python Tkinter is unavailable after dependency installation.${NC}"
        exit 1
    fi
}

check_root || exit 1
detect_os || exit 1

mkdir -p /etc/linstresscpu /var/log/linstresscpu
touch /etc/linstresscpu/linstresscpu.conf

INSTALL_DIR="/opt/LinStressCPU"

if ! git clone --depth 1 "$REPO_URL" .; then
    log_message "ERROR" "Failed to clone $REPO_URL"
    exit 1
fi

mkdir -p "$INSTALL_DIR/src"
cp ./src/LinStress.py       "$INSTALL_DIR/src/"
cp ./src/LinStressGUI.py    "$INSTALL_DIR/src/"
cp ./src/stress.py          "$INSTALL_DIR/src/"
cp ./src/logging_utils.py   "$INSTALL_DIR/src/"

install_deps

cat > /usr/local/bin/linstresscpu <<EOF
#!/bin/bash
exec python3 "$INSTALL_DIR/src/LinStress.py" "\$@"
EOF
chmod +x /usr/local/bin/linstresscpu

cat > /usr/local/bin/linstresscpu-gui <<EOF
#!/bin/bash
export LINSTRESS_CONFIG="/etc/linstresscpu/linstresscpu.conf"
exec python3 "$INSTALL_DIR/src/LinStressGUI.py" "\$@"
EOF
chmod +x /usr/local/bin/linstresscpu-gui

DESKTOP_DIR="/root/Desktop"
if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
    if id "$SUDO_USER" >/dev/null 2>&1; then
        HOME_DIR="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
        DESKTOP_DIR="${HOME_DIR}/Desktop"
    fi
fi

mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/LinStressCPU.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=LinStressCPU
Comment=Vordenby's CPU Stress Test Tool with Tkinter support
Exec=/usr/local/bin/linstresscpu-gui %U
Path=$INSTALL_DIR/src
Terminal=false
Categories=Utility;System;
StartupNotify=true
TryExec=/usr/local/bin/linstresscpu-gui
EOF
chmod +644 "$DESKTOP_DIR/LinStressCPU.desktop"

trap 'rm -rf "$TMP_DIR"' EXIT
