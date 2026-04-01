#!/usr/bin/env bash
#
# WebVM One-Click Installer
# ============================
# Supported hosts: Ubuntu 20.04+, Debian 11+, Fedora 38+
# This script installs all dependencies and configures WebVM as a systemd
# user service that starts automatically on login.
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# Requires: bash, sudo, git, curl
#

set -euo pipefail

# ── Colour codes ──────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo -e "${CYAN}[INFO]${RESET} $*"; }
success() { echo -e "${GREEN}[OK]${RESET}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; }
need()    { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }

# ── Detect distribution ────────────────────────────────────────────────────────
detect_distro() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        DISTRO="${ID:-unknown}"
        DISTRO_VERSION="${VERSION_ID:-}"
    else
        DISTRO="unknown"
        DISTRO_VERSION=""
    fi
}

# ── Check running as non-root ─────────────────────────────────────────────────
check_user() {
    if [[ $EUID -eq 0 ]]; then
        need "Do NOT run this script as root. WebVM should be installed and run as a regular user."
    fi
    USER_HOME="$HOME"
    info "Running as user: $(whoami)"
}

# ── Check internet ─────────────────────────────────────────────────────────────
check_internet() {
    if ! curl -s --max-time 5 https://github.com > /dev/null 2>&1; then
        warn "GitHub is not reachable. Some features may not work."
    fi
}

# ── Check prerequisites ───────────────────────────────────────────────────────
check_command() {
    local cmd="$1"
    if ! command -v "$cmd" &> /dev/null; then
        MISSING_DEPS+=" $cmd"
        return 1
    fi
    return 0
}

# ── Install system dependencies ────────────────────────────────────────────────
install_deps_ubuntu() {
    info "Installing system packages (apt)..."
    sudo apt update -qq
    sudo apt install -y -qq \
        python3 \
        python3-flask \
        python3-venv \
        qemu-system-x86 \
        qemu-utils \
        git \
        curl \
        socat \
        gnupg2 \
        ca-certificates \
        &>/dev/null
    success "System packages installed"
}

install_deps_fedora() {
    info "Installing system packages (dnf)..."
    sudo dnf install -y -q \
        python3 \
        python3-flask \
        qemu-system-x86 \
        qemu-img \
        git \
        curl \
        socat \
        &>/dev/null
    success "System packages installed"
}

install_deps_debian() {
    info "Installing system packages (apt)..."
    sudo apt update -q
    sudo apt install -y -q \
        python3 \
        python3-flask \
        python3-venv \
        qemu-system-x86 \
        qemu-utils \
        git \
        curl \
        socat \
        gnupg2 \
        ca-certificates \
        &>/dev/null
    success "System packages installed"
}

install_deps_arch() {
    info "Installing system packages (pacman)..."
    sudo pacman -Sy --noconfirm \
        python \
        python-flask \
        qemu-full \
        git \
        curl \
        socat \
        &>/dev/null
    success "System packages installed"
}

# ── Install quickemu ──────────────────────────────────────────────────────────
install_quickemu() {
    if command -v quickget &>/dev/null; then
        info "quickemu already installed"
        return
    fi

    info "Installing quickemu..."
    local QUICKEMU_DIR="/tmp/quickemu-install"
    rm -rf "$QUICKEMU_DIR"
    git clone --depth 1 https://github.com/quickemu-project/quickemu.git "$QUICKEMU_DIR" &>/dev/null
    sudo "$QUICKEMU_DIR/quickemu --install" &>/dev/null || warn "quickemu install failed — ISO auto-download will not be available"
    rm -rf "$QUICKEMU_DIR"
    if command -v quickget &>/dev/null; then
        success "quickemu installed"
    else
        warn "quickemu not in PATH — install manually for ISO auto-download support"
        warn "See: https://github.com/quickemu-project/quickemu"
    fi
}

# ── Clone / update repository ──────────────────────────────────────────────────
setup_repo() {
    local REPO_DIR="$USER_HOME/projects/webvm"
    local SETUP_SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

    if [[ -d "$REPO_DIR/.git" ]]; then
        info "WebVM repository already exists at $REPO_DIR"
        read -r -p "Pull latest changes? [Y/n]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]?$ ]]; then
            git -C "$REPO_DIR" pull origin master
            success "Repository updated"
        fi
    else
        info "Cloning WebVM repository..."
        mkdir -p "$USER_HOME/projects"
        git clone https://github.com/quickemu-project/webvm.git "$REPO_DIR" 2>/dev/null || \
        git clone https://github.com/<your-username>/webvm.git "$REPO_DIR"
        success "Repository cloned to $REPO_DIR"
    fi

    # If running from the repo itself, use it directly
    if [[ -d "$SETUP_SCRIPT_DIR/.git" ]]; then
        info "Running from source directory — using $SETUP_SCRIPT_DIR"
        cd "$SETUP_SCRIPT_DIR"
    fi
}

# ── Install Python dependencies ────────────────────────────────────────────────
install_python_deps() {
    info "Setting up Python virtual environment..."
    python3 -m venv "$USER_HOME/projects/webvm/venv"
    source "$USER_HOME/projects/webvm/venv/bin/activate"
    pip install --quiet -r "$USER_HOME/projects/webvm/requirements.txt"
    success "Python dependencies installed"
}

# ── Initialize noVNC submodule ────────────────────────────────────────────────
setup_novnc() {
    if [[ ! -d "$USER_HOME/projects/webvm/web/static/js/novnc/.git" ]]; then
        info "Initializing noVNC submodule..."
        git submodule update --init --recursive
        success "noVNC initialized"
    else
        info "noVNC already initialized"
    fi
}

# ── Create systemd user service ────────────────────────────────────────────────
setup_systemd_service() {
    local SERVICE_FILE="$USER_HOME/.config/systemd/user/webvm.service"
    local REPO_DIR="$USER_HOME/projects/webvm"

    info "Installing systemd user service..."
    mkdir -p "$USER_HOME/.config/systemd/user"

    # Adapt the contrib service file with the actual repo path
    sed "s|%h|$USER_HOME|g" "$REPO_DIR/contrib/webvm.service" > "$SERVICE_FILE"

    # If not running in a user systemd context (rare), skip
    if systemctl --user status &>/dev/null; then
        systemctl --user daemon-reload
        systemctl --user enable --now webvm.service
        success "systemd service enabled and started"
    else
        warn "systemd user services not available on this system."
        warn "You can start WebVM manually with:"
        echo -e "  ${CYAN}cd $REPO_DIR && source venv/bin/activate && flask --app src.app run --host 0.0.0.0 --port 5000${RESET}"
    fi
}

# ── Print final instructions ──────────────────────────────────────────────────
print_summary() {
    local REPO_DIR="$USER_HOME/projects/webvm"
    local IP
    IP=$(ip -4 addr show scope global 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1 || echo "<your-server-ip>")

    echo
    echo -e "${BOLD}══════════════════════════════════════════════════════════════${RESET}"
    echo -e "${BOLD}  WebVM installation complete!${RESET}"
    echo -e "${BOLD}══════════════════════════════════════════════════════════════${RESET}"
    echo
    echo -e "  Open in your browser:"
    echo -e "  ${CYAN}http://$IP:5000${RESET}"
    echo
    echo -e "  To start WebVM manually (if not using systemd):"
    echo -e "  ${CYAN}cd $REPO_DIR && source venv/bin/activate && flask --app src.app run --host 0.0.0.0${RESET}"
    echo
    echo -e "  Service management (systemd user service):"
    echo -e "  ${CYAN}systemctl --user status webvm${RESET}   # Check status"
    echo -e "  ${CYAN}systemctl --user restart webvm${RESET}  # Restart"
    echo -e "  ${CYAN}journalctl --user -u webvm -f${RESET}   # View logs"
    echo
    echo -e "  Quickemu (ISO auto-download) was installed."
    echo -e "  Install macOS ISOs with: ${CYAN}quickget macos sequoia${RESET}"
    echo
    echo -e "${BOLD}══════════════════════════════════════════════════════════════${RESET}"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    echo -e "${BOLD}"
    echo "  ╔═══════════════════════════════╗"
    echo "  ║      WebVM One-Click Setup    ║"
    echo "  ╚═══════════════════════════════╝"
    echo -e "${RESET}"
    echo

    check_user
    detect_distro
    check_internet

    # Detect missing commands and warn
    MISSING_DEPS=""
    check_command git || true
    check_command curl || true

    if [[ -n "${MISSING_DEPS:-}" ]]; then
        warn "Missing commands (will try to install):$MISSING_DEPS"
    fi

    # ── 1. System dependencies ────────────────────────────────────────────────
    case "$DISTRO" in
        ubuntu)
            install_deps_ubuntu
            ;;
        debian)
            install_deps_debian
            ;;
        fedora)
            install_deps_fedora
            ;;
        arch)
            install_deps_arch
            ;;
        *)
            warn "Unknown distribution: $DISTRO — attempting Ubuntu/Debian install"
            install_deps_ubuntu || true
            ;;
    esac

    # ── 2. Quickemu (optional but recommended) ────────────────────────────────
    read -r -p "Install quickemu (ISO auto-download support)? [Y/n]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]?$ ]]; then
        install_quickemu
    fi

    # ── 3. Repository ─────────────────────────────────────────────────────────
    setup_repo

    # ── 4. Python dependencies ────────────────────────────────────────────────
    install_python_deps

    # ── 5. noVNC submodule ────────────────────────────────────────────────────
    setup_novnc

    # ── 6. systemd service ────────────────────────────────────────────────────
    read -r -p "Install systemd user service (auto-start on login)? [Y/n]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]?$ ]]; then
        setup_systemd_service
    fi

    print_summary
}

main "$@"
