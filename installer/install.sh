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

log_message "INFO" "Создана временная директория: $TMP_DIR"

cd "$TMP_DIR" || exit 1

check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_message "INFO" "Запуск как root."
    else
        log_message "ERROR" "Скрипт должен запускаться от root."
        echo -e "${RED}Скрипт должен запускаться от root.${NC}"
        sleep 3
        exit 1
    fi
}

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        case "$ID" in
            ubuntu|debian) PMGR="apt_get" ;; 
            fedora)       PMGR="dnf" ;;
            centos|rhel)  PMGR="yum" ;;
            arch)         PMGR="pacman" ;;
            *) 
                log_message "ERROR" "Неподдерживаемая ОС: $ID"
                echo -e "${RED}Неподдерживаемая ОС: $ID${NC}. Попробуйте использовать исходники напрямую."
                sleep 3
                exit 1
        esac
        log_message "INFO" "Определена ОС: $ID, менеджер пакетов: $PMGR"
    else
        log_message "ERROR" "Не найдена /etc/os-release"
        echo -e "${RED}Не найдена /etc/os-release.${NC}. Попробуйте использовать исходники напрямую."
        sleep 3
        exit 1
    fi
}

install_deps() {
    log_message "INFO" "Устанавливаются зависимости."

    case "$PMGR" in
        apt_get)
            DEPS=(git python3 python3-pip python3-venv python3-tk)
            for pkg in "${DEPS[@]}"; do
                if ! dpkg -s "$pkg" >/dev/null 2>&1; then
                    log_message "INFO" "Устанавливаю $pkg..."
                    apt-get install -y "$pkg"
                else
                    log_message "INFO" "$pkg уже установлен."
                fi
            done
            ;;

        yum)
            DEPS=(git python3 python3-pip python3-virtualenv python3-tkinter)
            for pkg in "${DEPS[@]}"; do
                if ! rpm -q "$pkg" >/dev/null 2>&1; then
                    log_message "INFO" "Устанавливаю $pkg..."
                    yum install -y "$pkg"
                else
                    log_message "INFO" "$pkg уже установлен."
                fi
            done
            ;;
        dnf)
            DEPS=(git python3 python3-pip python3-virtualenv python3-tkinter)
            for pkg in "${DEPS[@]}"; do
                if ! dnf query "$pkg" >/dev/null 2>&1; then
                    log_message "INFO" "Устанавливаю $pkg..."
                    dnf install -y "$pkg"
                else
                    log_message "INFO" "$pkg уже установлен."
                fi
            done
            ;;

        pacman)
            DEPS=(git python python-pip python-virtualenv tk)
            for pkg in "${DEPS[@]}"; do
                if ! pacman -Qi "$pkg" >/dev/null 2>&1; then
                    log_message "INFO" "Устанавливаю $pkg..."
                    pacman -S --noconfirm "$pkg"
                else
                    log_message "INFO" "$pkg уже установлен."
                fi
            done
            ;;

        *)
            log_message "ERROR" "Неподдерживаемый менеджер пакетов: $PMGR"
            echo -e "${RED}Неподдерживаемый менеджер пакетов: $PMGR${NC}. Попробуйте использовать исходники напрямую."
            sleep 3
            exit 1
            ;;
    esac
}

resolve_source_file() {
    local target_name="$1"
    local candidates=("$target_name")

    case "$target_name" in
        LinStress.py)      candidates=(LinStress.py linstress.py);;
        LinStressGUI.py)   candidates=(LinStressGUI.py linstressgui.py);;
        stress.py)         candidates=(stress.py Stress.py);;
    esac

    local candidate
    for candidate in "${candidates[@]}"; do
        if [ -f "./$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

check_root() {
    if [ "$EUID" -eq 0 ]; then
        log_message "INFO" "Запуск как root."
    else
        log_message "ERROR" "Скрипт должен запускаться от root."
        echo -e "${RED}Скрипт должен запускаться от root.${NC}"
        sleep 3
        exit 1
    fi
}

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        case "$ID" in
            ubuntu|debian) PMGR="apt_get" ;; 
            fedora)       PMGR="dnf" ;;
            centos|rhel)  PMGR="yum" ;;
            arch)         PMGR="pacman" ;;
            *) 
                log_message "ERROR" "Неподдерживаемая ОС: $ID"
                echo -e "${RED}Неподдерживаемая ОС: $ID${NC}. Попробуйте использовать исходники напрямую."
                sleep 3
                exit 1
        esac
        log_message "INFO" "Определена ОС: $ID, менеджер пакетов: $PMGR"
    else
        log_message "ERROR" "Не найдена /etc/os-release"
        echo -e "${RED}Не найдена /etc/os-release.${NC}. Попробуйте использовать исходники напрямую."
        sleep 3
        exit 1
    fi
}

log_message "INFO" "Запуск основной установки."

check_root || exit 1
detect_os || exit 1

mkdir -p /etc/linstresscpu /var/log/linstresscpu
touch /etc/linstresscpu/linstresscpu.conf

INSTALL_DIR="/opt/LinStressCPU"

if ! git clone --depth 1 "$REPO_URL" .; then
    log_message "ERROR" "Не удалось клонировать $REPO_URL"
    echo
    exit 1
fi

log_message "INFO" "Клонирование завершено."

mkdir -p "$INSTALL_DIR/src"
cp ./LinStress.py           "$INSTALL_DIR/src/"
cp ./LinStressGUI.py        "$INSTALL_DIR/src/"
cp ./stress.py              "$INSTALL_DIR/src/"
cp ./logging_utils.py       "$INSTALL_DIR/src/"

if ! install_deps; then
    log_message "ERROR" "Ошибка при установке зависимостей."
    echo
    exit 1
fi

cat > /usr/local/bin/linstresscpu <<EOF2
#!/bin/bash
exec python3 "$INSTALL_DIR/src/LinStress.py" "\$@"
EOF2
chmod +x /usr/local/bin/linstresscpu

cat > /usr/local/bin/linstresscpu-gui <<EOF3
#!/bin/bash
export LINSTRESS_CONFIG="/etc/linstresscpu/linstresscpu.conf"
exec python3 "$INSTALL_DIR/src/LinStressGUI.py" "\$@"
EOF3
chmod +x /usr/local/bin/linstresscpu-gui

DESKTOP_DIR="/root/Desktop"
if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
    if id "$SUDO_USER" >/dev/null 2>&1; then
        HOME_DIR="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
        DESKTOP_DIR="${HOME_DIR}/Desktop"
    fi
fi

mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/LinStressCPU.desktop" <<EOF4
[Desktop Entry]
Version=1.0
Type=Application
Name=LinStressCPU
Comment=Vordenby's CPU Stress Test Tool
Exec=/usr/local/bin/linstresscpu-gui %i
Path=$INSTALL_DIR/src
Terminal=false
Categories=Utility;System;
StartupNotify=true
TryExec=/usr/local/bin/linstresscpu-gui
EOF4
chmod +x "$DESKTOP_DIR/LinStressCPU.desktop"

log_message "INFO" "Установка завершена."

trap 'rm -rf "$TMP_DIR"' EXIT

echo
log_message "INFO" "Все временные файлы удалены."
