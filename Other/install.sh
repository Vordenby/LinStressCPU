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
            ;;
        dnf|yum)
            deps=(python3.11 python3-tkinter xdg-utils)
            ;;
        pacman)
            deps=(python python-tk xdg-utils)
            ;;
        zypper)
            deps=(python311 python311-tk xdg-utils)
            ;;
    esac

    if [[ "$PMGR" == "apt" ]]; then
        log_message "INFO" "Refreshing apt package metadata."
        if [[ "${ID:-}" == "astra" || "${ID:-}" == "astra-linux" ]]; then
            local astra_repository_file="/etc/apt/sources.list.d/linstresscpu-astra.list"
            local -a astra_repository_lines=(
                "deb https://dl.astralinux.ru/astra/stable/1.8_x86-64/main-repository/ 1.8_x86-64 main contrib non-free non-free-firmware"
                "deb https://dl.astralinux.ru/astra/stable/1.8_x86-64/extended-repository/ 1.8_x86-64 main contrib non-free non-free-firmware"
            )
            local repository_line

            mkdir -p "$(dirname "$astra_repository_file")"
            touch "$astra_repository_file"
            for repository_line in "${astra_repository_lines[@]}"; do
                if ! grep -Fqx "$repository_line" "$astra_repository_file"; then
                    printf '%s\n' "$repository_line" >> "$astra_repository_file"
                    log_message "INFO" "Added Astra APT repository: $repository_line"
                fi
            done
        fi

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

        local python_pkg=""
        local tkinter_pkg=""
        local python_version
        local candidate
        for python_version in 3.14 3.13 3.12 3.11; do
            candidate="python$python_version"
            if command -v "$candidate" >/dev/null 2>&1 || \
                apt-cache show "$candidate" >/dev/null 2>&1; then
                python_pkg="$candidate"
                PYTHON_BIN="$(command -v "$candidate" 2>/dev/null || printf '%s' "$candidate")"
                break
            fi
        done

        if [[ -z "$python_pkg" ]]; then
            log_message "ERROR" "Python 3.11 or newer is unavailable in the configured apt repositories."
            echo -e "${RED}Python 3.11 or newer is unavailable in the configured apt repositories.${NC}"
            exit 1
        fi

        candidate="${python_pkg}-tk"
        if apt-cache show "$candidate" >/dev/null 2>&1; then
            tkinter_pkg="$candidate"
        fi

        if [[ -z "$tkinter_pkg" ]]; then
            log_message "ERROR" "No Tkinter package is available for $python_pkg in the configured apt repositories."
            echo -e "${RED}No Tkinter package is available in the configured apt repositories.${NC}"
            echo "Enable the Astra Linux repository containing ${python_pkg}-tk, then run the installer again."
            exit 1
        fi

        deps=("$python_pkg" "$tkinter_pkg" xdg-utils)
        log_message "INFO" "Using Python package: $python_pkg"
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
                    if [[ "$PMGR" == "dnf" ]]; then
                        dnf install -y --skip-broken "$pkg"
                    else
                        yum install -y --skip-broken "$pkg"
                    fi
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

    if [[ -z "${PYTHON_BIN:-}" ]]; then
        PYTHON_BIN="$(command -v python3.14 2>/dev/null || command -v python3.13 2>/dev/null || command -v python3.12 2>/dev/null || command -v python3.11 2>/dev/null || true)"
    fi

    if [[ -z "$PYTHON_BIN" ]] || ! "$PYTHON_BIN" -c 'import sys, tkinter; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
        log_message "ERROR" "Python Tkinter is still unavailable after dependency installation."
        echo -e "${RED}Python 3.11+ with Tkinter is unavailable after dependency installation.${NC}"
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

SOURCE_DIR=""
if [[ -f ./src/LinStress.py && -f ./src/LinStressGUI.py && \
    -f ./src/stress.py && -f ./src/logging_utils.py ]]; then
    SOURCE_DIR="./src"
elif [[ -f ./LinStress.py && -f ./LinStressGUI.py && \
    -f ./stress.py && -f ./logging_utils.py ]]; then
    SOURCE_DIR="."
else
    log_message "ERROR" "The cloned repository does not contain the required LinStressCPU source files."
    echo -e "${RED}The cloned repository does not contain the required source files.${NC}"
    exit 1
fi

mkdir -p "$INSTALL_DIR/src"
cp "$SOURCE_DIR/LinStress.py"       "$INSTALL_DIR/src/"
cp "$SOURCE_DIR/LinStressGUI.py"    "$INSTALL_DIR/src/"
cp "$SOURCE_DIR/stress.py"          "$INSTALL_DIR/src/"
cp "$SOURCE_DIR/logging_utils.py"   "$INSTALL_DIR/src/"

install_deps

cat > /usr/local/bin/linstresscpu <<EOF
#!/bin/bash
export LINSTRESS_LOG_DIR="\${XDG_STATE_HOME:-\$HOME/.local/state}/linstresscpu/logs"
exec "$PYTHON_BIN" "$INSTALL_DIR/src/LinStress.py" "\$@"
EOF
chmod +x /usr/local/bin/linstresscpu

cat > /usr/local/bin/linstresscpu-gui <<EOF
#!/bin/bash
export LINSTRESS_CONFIG="/etc/linstresscpu/linstresscpu.conf"
export LINSTRESS_LOG_DIR="\${XDG_STATE_HOME:-\$HOME/.local/state}/linstresscpu/logs"
exec "$PYTHON_BIN" "$INSTALL_DIR/src/LinStressGUI.py" "\$@"
EOF
chmod +x /usr/local/bin/linstresscpu-gui

TARGET_USER="${SUDO_USER:-root}"
if ! id "$TARGET_USER" >/dev/null 2>&1; then
    log_message "ERROR" "Target user does not exist: $TARGET_USER"
    exit 1
fi

HOME_DIR="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
if [[ -z "$HOME_DIR" ]]; then
    log_message "ERROR" "Could not determine the home directory for $TARGET_USER"
    exit 1
fi

TARGET_GROUP="$(id -gn "$TARGET_USER")"
DESKTOP_DIR="$HOME_DIR/Desktop"
APPLICATIONS_DIR="$HOME_DIR/.local/share/applications"

write_desktop_entry() {
    local entry_path="$1"
    local name="$2"
    local comment="$3"
    local executable="$4"
    local terminal="$5"
    local try_exec="${6:-$executable}"

    mkdir -p "$(dirname "$entry_path")"
    cat > "$entry_path" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$name
Comment=$comment
Exec=$executable
Path=$INSTALL_DIR/src
Terminal=$terminal
Categories=Utility;System;
StartupNotify=true
TryExec=$try_exec
EOF
    chmod 755 "$entry_path"
    chown "$TARGET_USER:$TARGET_GROUP" "$entry_path"
}

validate_desktop_entry() {
    local entry_path="$1"
    local expected_name="$2"
    local expected_exec="$3"
    local expected_try_exec="$4"

    [[ -s "$entry_path" ]] || return 1
    grep -Fxq "Type=Application" "$entry_path" || return 1
    grep -Fxq "Name=$expected_name" "$entry_path" || return 1
    grep -Fxq "Exec=$expected_exec" "$entry_path" || return 1
    grep -Fxq "TryExec=$expected_try_exec" "$entry_path" || return 1
    [[ -x "$expected_try_exec" ]] || return 1
}

GUI_ENTRY_NAME="LinStressCPU"
FOLDER_ENTRY_NAME="LinStressCPU folder"
GUI_EXECUTABLE="/usr/local/bin/linstresscpu-gui"
FOLDER_EXECUTABLE="$(command -v xdg-open || true)"
if [[ -z "$FOLDER_EXECUTABLE" ]]; then
    log_message "ERROR" "xdg-open is required to create the folder shortcut."
    exit 1
fi

for entry_dir in "$APPLICATIONS_DIR" "$DESKTOP_DIR"; do
    write_desktop_entry "$entry_dir/LinStressCPU.desktop" "$GUI_ENTRY_NAME" "LinStressCPU graphical interface" "$GUI_EXECUTABLE" false "$GUI_EXECUTABLE"
    write_desktop_entry "$entry_dir/LinStressCPU-folder.desktop" "$FOLDER_ENTRY_NAME" "LinStressCPU installation folder" "$FOLDER_EXECUTABLE $INSTALL_DIR" false "$FOLDER_EXECUTABLE"
done

for entry_path in \
    "$APPLICATIONS_DIR/LinStressCPU.desktop" \
    "$APPLICATIONS_DIR/LinStressCPU-folder.desktop" \
    "$DESKTOP_DIR/LinStressCPU.desktop" \
    "$DESKTOP_DIR/LinStressCPU-folder.desktop"; do
    if [[ "$entry_path" == *-folder.desktop ]]; then
        expected_name="$FOLDER_ENTRY_NAME"
        expected_exec="$FOLDER_EXECUTABLE $INSTALL_DIR"
        expected_try_exec="$FOLDER_EXECUTABLE"
    else
        expected_name="$GUI_ENTRY_NAME"
        expected_exec="$GUI_EXECUTABLE"
        expected_try_exec="$GUI_EXECUTABLE"
    fi
    if ! validate_desktop_entry "$entry_path" "$expected_name" "$expected_exec" "$expected_try_exec"; then
        log_message "ERROR" "Desktop entry validation failed: $entry_path"
        exit 1
    fi
done

log_message "INFO" "Created and validated CLI and GUI desktop entries for $TARGET_USER."

trap 'rm -rf "$TMP_DIR"' EXIT
