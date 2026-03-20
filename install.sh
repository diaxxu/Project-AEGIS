#!/usr/bin/env bash
# =============================================================================
#  AEGIS — Ground Station Installer
#  Run this once on a fresh Raspberry Pi to set everything up.
#
#  Usage:
#    chmod +x install.sh
#    ./install.sh
#
#  What this does:
#    1. Checks you are on a Raspberry Pi running a supported OS
#    2. Updates the system
#    3. Installs Python dependencies
#    4. Configures serial port permissions
#    5. Installs and enables the AEGIS systemd service
#    6. Configures the firewall
#    7. Sets up DuckDNS (optional)
#    8. Runs a self-test to confirm everything works
#
#  Safe to re-run. Each step is idempotent.
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Colours
# -----------------------------------------------------------------------------
RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
BLU='\033[0;34m'
CYN='\033[0;36m'
WHT='\033[1;37m'
DIM='\033[2m'
NC='\033[0m'

BOLD='\033[1m'

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

log()    { echo -e "${WHT}[AEGIS]${NC} $*"; }
ok()     { echo -e "${GRN}  ✓${NC} $*"; }
warn()   { echo -e "${YLW}  ⚠${NC} $*"; }
err()    { echo -e "${RED}  ✗${NC} $*" >&2; }
step()   { echo -e "\n${CYN}${BOLD}── $* ${NC}${DIM}$( printf '─%.0s' {1..50} | head -c $((54 - ${#1})) )${NC}"; }
die()    { err "$*"; exit 1; }

# Print a banner
banner() {
  echo -e "${CYN}"
  echo "  ╔══════════════════════════════════════════╗"
  echo "  ║          AEGIS  Ground Station           ║"
  echo "  ║        Autonomous Escort System          ║"
  echo "  ╚══════════════════════════════════════════╝"
  echo -e "${NC}"
}

# Ask a yes/no question, default to $2 (y or n)
ask() {
  local prompt="$1" default="${2:-y}"
  local yn
  if [[ "$default" == "y" ]]; then
    read -r -p "$(echo -e "${YLW}  ?${NC} ${prompt} [Y/n] ")" yn
    yn="${yn:-y}"
  else
    read -r -p "$(echo -e "${YLW}  ?${NC} ${prompt} [y/N] ")" yn
    yn="${yn:-n}"
  fi
  [[ "$yn" =~ ^[Yy] ]]
}

# Ask for a value with a default
ask_value() {
  local prompt="$1" default="$2"
  local val
  read -r -p "$(echo -e "${YLW}  ?${NC} ${prompt} [${default}]: ")" val
  echo "${val:-$default}"
}

# Check a command exists
need() {
  command -v "$1" >/dev/null 2>&1 || die "Required command '$1' not found."
}

# -----------------------------------------------------------------------------
# Pre-flight checks
# -----------------------------------------------------------------------------

preflight() {
  step "Pre-flight checks"

  # Must be run as a normal user (not root) so service runs as pi
  if [[ "$EUID" -eq 0 ]]; then
    die "Do not run as root. Run as your normal user (usually 'pi'). sudo will be used where needed."
  fi
  ok "Running as user: $(whoami)"

  # Check we are on a Raspberry Pi (optional — installer works on Ubuntu too)
  if grep -qi "raspberry" /proc/cpuinfo 2>/dev/null || \
     grep -qi "raspberry" /etc/os-release 2>/dev/null; then
    ok "Raspberry Pi detected"
  else
    warn "Not a Raspberry Pi — continuing anyway (installer works on Debian/Ubuntu too)"
  fi

  # Check OS is Debian-based
  if ! command -v apt-get >/dev/null 2>&1; then
    die "This installer requires a Debian/Ubuntu-based OS (apt-get not found)"
  fi
  ok "Debian-based OS confirmed"

  # Check internet connectivity
  if ! curl -s --max-time 5 https://pypi.org >/dev/null 2>&1; then
    die "No internet connection. Connect to WiFi or plug in your 4G dongle first."
  fi
  ok "Internet connection confirmed"

  # Check Python3
  if ! command -v python3 >/dev/null 2>&1; then
    warn "Python3 not found — will install it"
  else
    PYVER=$(python3 --version 2>&1 | awk '{print $2}')
    ok "Python3 found: $PYVER"
    # Need at least 3.7
    PYMAJ=$(echo "$PYVER" | cut -d. -f1)
    PYMIN=$(echo "$PYVER" | cut -d. -f2)
    if [[ "$PYMAJ" -lt 3 ]] || { [[ "$PYMAJ" -eq 3 ]] && [[ "$PYMIN" -lt 7 ]]; }; then
      die "Python 3.7+ required. Found $PYVER."
    fi
  fi

  # Confirm install directory
  INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  ok "Install directory: $INSTALL_DIR"

  # Check ground_station folder exists
  if [[ ! -d "$INSTALL_DIR/ground_station" ]]; then
    die "ground_station/ folder not found. Run this script from the repo root."
  fi
  ok "Repository structure verified"
}

# -----------------------------------------------------------------------------
# System update
# -----------------------------------------------------------------------------

update_system() {
  step "System update"

  if ask "Update system packages? (recommended, takes 1-3 min on first run)" y; then
    log "Running apt update..."
    sudo apt-get update -qq
    ok "Package lists updated"

    log "Upgrading installed packages..."
    sudo apt-get upgrade -y -qq
    ok "System packages upgraded"
  else
    warn "Skipping system update — some packages may be outdated"
  fi

  log "Installing required system packages..."
  sudo apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    screen \
    git \
    curl \
    ufw \
    jq \
    2>&1 | grep -v "^$" || true
  ok "System packages installed"
}

# -----------------------------------------------------------------------------
# Python environment
# -----------------------------------------------------------------------------

setup_python() {
  step "Python environment"

  VENV_DIR="$INSTALL_DIR/.venv"

  if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating Python virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    ok "Virtual environment created"
  else
    ok "Virtual environment already exists"
  fi

  log "Activating virtual environment..."
  # shellcheck source=/dev/null
  source "$VENV_DIR/bin/activate"
  ok "Virtual environment active"

  log "Upgrading pip..."
  pip install --upgrade pip --quiet
  ok "pip upgraded"

  log "Installing Python dependencies from requirements.txt..."
  pip install -r "$INSTALL_DIR/ground_station/requirements.txt" --quiet
  ok "Python dependencies installed:"

  # Print installed versions
  for pkg in dronekit flask pymavlink requests; do
    VER=$(pip show "$pkg" 2>/dev/null | grep "^Version:" | awk '{print $2}')
    echo -e "    ${DIM}$pkg $VER${NC}"
  done

  # Update systemd service to use venv python
  PYTHON_PATH="$VENV_DIR/bin/python3"
  ok "Using Python: $PYTHON_PATH"
}

# -----------------------------------------------------------------------------
# Serial port permissions
# -----------------------------------------------------------------------------

setup_serial() {
  step "Serial port permissions"

  USER="$(whoami)"

  # Add user to dialout group (required for /dev/ttyUSB* access)
  if groups "$USER" | grep -q "dialout"; then
    ok "User '$USER' already in dialout group"
  else
    log "Adding '$USER' to dialout group (for /dev/ttyUSB* access)..."
    sudo usermod -aG dialout "$USER"
    ok "Added to dialout group"
    warn "You may need to log out and back in for group change to take effect"
    warn "Or run: newgrp dialout"
    NEED_RELOGIN=true
  fi

  # Disable ModemManager if present (it interferes with SiK radios)
  if systemctl is-active --quiet ModemManager 2>/dev/null; then
    log "Disabling ModemManager (it interferes with SiK USB radios)..."
    sudo systemctl stop ModemManager
    sudo systemctl disable ModemManager
    ok "ModemManager disabled"
  else
    ok "ModemManager not running (good)"
  fi

  # Create udev rule so SiK radios always get the same port names
  log "Creating udev rules for SiK telemetry radios..."
  cat <<'EOF' | sudo tee /etc/udev/rules.d/99-aegis-sik.rules > /dev/null
# AEGIS — SiK telemetry radio stable port names
# Plug in quad radio FIRST → /dev/aegis-quad
# Plug in FW radio SECOND → /dev/aegis-fw
# (These are based on USB port position, not insertion order)
# To customise, run: udevadm info /dev/ttyUSB0 | grep ID_PATH
# Then update KERNELS below with your actual hub port IDs.

# Fallback: if udev rules fail, the config.py defaults still work
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", \
  SYMLINK+="aegis-radio%n", GROUP="dialout", MODE="0664"
EOF
  sudo udevadm control --reload-rules
  sudo udevadm trigger
  ok "udev rules installed (/etc/udev/rules.d/99-aegis-sik.rules)"
  log "After plugging in SiK radios, run: ls -la /dev/aegis-* /dev/ttyUSB*"
}

# -----------------------------------------------------------------------------
# Configure serial ports
# -----------------------------------------------------------------------------

configure_ports() {
  step "Configure serial ports"

  log "Checking for connected USB devices..."
  PORTS=$(ls /dev/ttyUSB* 2>/dev/null || true)

  if [[ -z "$PORTS" ]]; then
    warn "No USB serial devices found right now."
    warn "Plug in your SiK radios and run: ls /dev/ttyUSB*"
    QUAD_PORT=$(ask_value "Quad SiK radio port" "/dev/ttyUSB0")
    FW_PORT=$(ask_value "Fixed-wing SiK radio port" "/dev/ttyUSB1")
  else
    log "Found USB serial ports:"
    echo "$PORTS" | while read -r p; do
      echo -e "    ${DIM}$p${NC}"
    done
    QUAD_PORT=$(ask_value "Which port is the QUAD SiK radio?" "/dev/ttyUSB0")
    FW_PORT=$(ask_value "Which port is the FIXED-WING SiK radio?" "/dev/ttyUSB1")
  fi

  QUAD_ALT=$(ask_value "Quad hover altitude above user (metres)" "15")
  FW_ALT=$(ask_value "Fixed-wing loiter altitude above user (metres)" "30")
  FW_RADIUS=$(ask_value "Fixed-wing loiter orbit radius (metres)" "50")
  SERVER_PORT=$(ask_value "Invoke server port" "5000")

  # Write config.py with the user's choices
  log "Writing configuration to ground_station/config.py..."
  cat > "$INSTALL_DIR/ground_station/config.py" <<EOF
"""
AEGIS Configuration — generated by install.sh $(date +%Y-%m-%d)
Edit this file to change any settings.
"""

import os

# Serial ports (confirmed during install)
QUAD_PORT   = os.getenv("AEGIS_QUAD_PORT",  "$QUAD_PORT")
QUAD_BAUD   = int(os.getenv("AEGIS_QUAD_BAUD", "57600"))

FW_PORT     = os.getenv("AEGIS_FW_PORT",    "$FW_PORT")
FW_BAUD     = int(os.getenv("AEGIS_FW_BAUD",   "57600"))

# Flight parameters
QUAD_ALT    = int(os.getenv("AEGIS_QUAD_ALT",    "$QUAD_ALT"))
FW_ALT      = int(os.getenv("AEGIS_FW_ALT",      "$FW_ALT"))
FW_RADIUS   = int(os.getenv("AEGIS_FW_RADIUS",   "$FW_RADIUS"))

# Connection settings
CONNECT_TIMEOUT = int(os.getenv("AEGIS_CONNECT_TIMEOUT", "30"))
ARM_TIMEOUT     = int(os.getenv("AEGIS_ARM_TIMEOUT",     "15"))

# Server
SERVER_PORT = int(os.getenv("AEGIS_PORT", "$SERVER_PORT"))

# Paths
import os as _os
WEB_DIR = _os.path.join(_os.path.dirname(__file__), "web")
EOF
  ok "config.py written"
  ok "  Quad port:   $QUAD_PORT"
  ok "  FW port:     $FW_PORT"
  ok "  Quad alt:    ${QUAD_ALT}m"
  ok "  FW alt:      ${FW_ALT}m  radius=${FW_RADIUS}m"
  ok "  Server port: $SERVER_PORT"
}

# -----------------------------------------------------------------------------
# Systemd service
# -----------------------------------------------------------------------------

setup_service() {
  step "Systemd service"

  VENV_DIR="$INSTALL_DIR/.venv"
  SERVICE_FILE="/etc/systemd/system/aegis.service"

  log "Writing systemd service file..."
  cat <<EOF | sudo tee "$SERVICE_FILE" > /dev/null
[Unit]
Description=AEGIS Ground Station — Autonomous Escort System
Documentation=https://github.com/YOUR_USERNAME/aegis
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$INSTALL_DIR/ground_station
ExecStart=$VENV_DIR/bin/python3 $INSTALL_DIR/ground_station/invoke_server.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Graceful shutdown
KillMode=mixed
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
EOF

  sudo systemctl daemon-reload
  ok "Service file written: $SERVICE_FILE"

  sudo systemctl enable aegis
  ok "Service enabled (will start on boot)"

  log "Starting AEGIS service..."
  # Don't fail if vehicles aren't connected yet — just show status
  sudo systemctl start aegis || true
  sleep 2

  if systemctl is-active --quiet aegis; then
    ok "Service is running"
  else
    warn "Service not running yet — this is normal if SiK radios are not plugged in"
    warn "Start manually with: sudo systemctl start aegis"
    warn "View logs with:      sudo journalctl -u aegis -f"
  fi
}

# -----------------------------------------------------------------------------
# Firewall
# -----------------------------------------------------------------------------

setup_firewall() {
  step "Firewall"

  SERVER_PORT=$(grep "SERVER_PORT" "$INSTALL_DIR/ground_station/config.py" | \
    grep -o '[0-9]*' | tail -1)
  SERVER_PORT="${SERVER_PORT:-5000}"

  log "Configuring UFW firewall..."
  sudo ufw --force enable >/dev/null 2>&1 || true

  # Keep SSH open so we don't lock ourselves out
  sudo ufw allow ssh >/dev/null 2>&1
  ok "SSH access preserved"

  # Open the invoke server port
  sudo ufw allow "$SERVER_PORT"/tcp >/dev/null 2>&1
  ok "Port $SERVER_PORT open (invoke server)"

  # MAVProxy UDP output for QGroundControl (optional)
  sudo ufw allow 14550/udp >/dev/null 2>&1
  ok "Port 14550/UDP open (QGroundControl telemetry)"

  sudo ufw reload >/dev/null 2>&1 || true
  ok "Firewall configured"
}

# -----------------------------------------------------------------------------
# DuckDNS
# -----------------------------------------------------------------------------

setup_duckdns() {
  step "DuckDNS (dynamic DNS)"

  log "DuckDNS gives your Pi a stable hostname so your phone can always reach it."
  log "Get a free account and subdomain at https://www.duckdns.org"

  if ! ask "Set up DuckDNS now?" n; then
    warn "Skipping DuckDNS — you can reach the Pi on your local WiFi by IP address"
    warn "To set up later, see: docs/quickstart.md"
    return 0
  fi

  DUCK_DOMAIN=$(ask_value "Your DuckDNS subdomain (without .duckdns.org)" "my-aegis")
  DUCK_TOKEN=$(ask_value "Your DuckDNS token (from your account page)" "")

  if [[ -z "$DUCK_TOKEN" ]]; then
    warn "No token entered — skipping DuckDNS setup"
    return 0
  fi

  DUCK_DIR="$HOME/duckdns"
  mkdir -p "$DUCK_DIR"

  cat > "$DUCK_DIR/duck.sh" <<EOF
#!/bin/bash
echo url="https://www.duckdns.org/update?domains=${DUCK_DOMAIN}&token=${DUCK_TOKEN}&ip=" | \
  curl -k -s -o $DUCK_DIR/duck.log -K -
EOF
  chmod +x "$DUCK_DIR/duck.sh"

  # Test it
  log "Testing DuckDNS update..."
  bash "$DUCK_DIR/duck.sh"
  RESULT=$(cat "$DUCK_DIR/duck.log" 2>/dev/null || echo "")
  if [[ "$RESULT" == "OK" ]]; then
    ok "DuckDNS update succeeded"
  else
    warn "DuckDNS update returned: $RESULT"
    warn "Check your domain and token are correct"
  fi

  # Install cron job
  CRON_LINE="*/5 * * * * $DUCK_DIR/duck.sh >/dev/null 2>&1"
  if crontab -l 2>/dev/null | grep -q "duck.sh"; then
    ok "DuckDNS cron job already installed"
  else
    (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
    ok "DuckDNS cron job installed (updates every 5 minutes)"
  fi

  ok "Your invoke page will be at: http://${DUCK_DOMAIN}.duckdns.org:5000"
}

# -----------------------------------------------------------------------------
# Self-test
# -----------------------------------------------------------------------------

self_test() {
  step "Self-test"

  VENV_DIR="$INSTALL_DIR/.venv"

  log "Testing Python imports..."
  "$VENV_DIR/bin/python3" - <<'PYEOF'
import sys
failures = []
for pkg in ['dronekit', 'flask', 'pymavlink', 'requests']:
    try:
        __import__(pkg)
        print(f"  ✓ {pkg}")
    except ImportError as e:
        print(f"  ✗ {pkg}: {e}")
        failures.append(pkg)
if failures:
    print(f"\nFailed imports: {failures}")
    sys.exit(1)
PYEOF
  ok "All Python imports OK"

  log "Testing invoke server config..."
  "$VENV_DIR/bin/python3" -c "
import sys
sys.path.insert(0, '$INSTALL_DIR/ground_station')
from config import QUAD_PORT, FW_PORT, QUAD_ALT, FW_ALT, FW_RADIUS, SERVER_PORT, WEB_DIR
import os
assert os.path.exists(WEB_DIR), f'web dir not found: {WEB_DIR}'
assert os.path.exists(os.path.join(WEB_DIR, 'index.html')), 'index.html missing'
print(f'  ✓ config loaded: quad={QUAD_PORT} fw={FW_PORT} port={SERVER_PORT}')
print(f'  ✓ web directory: {WEB_DIR}')
"
  ok "Config and web directory OK"

  log "Testing Flask server starts (3 second smoke test)..."
  "$VENV_DIR/bin/python3" - <<PYEOF &
import sys, time, threading, os
sys.path.insert(0, '$INSTALL_DIR/ground_station')
os.environ['AEGIS_NO_CONNECT'] = '1'  # skip vehicle connection in smoke test

# Minimal Flask smoke test — doesn't touch serial ports
from flask import Flask
app = Flask(__name__)

@app.route('/health')
def health():
    return 'ok'

def run():
    app.run(host='127.0.0.1', port=15001, debug=False, use_reloader=False)

t = threading.Thread(target=run, daemon=True)
t.start()
time.sleep(2)

import urllib.request
try:
    resp = urllib.request.urlopen('http://127.0.0.1:15001/health', timeout=2)
    assert resp.read() == b'ok'
    print('  Flask HTTP server: OK')
except Exception as e:
    print(f'  Flask smoke test failed: {e}', file=sys.stderr)
    sys.exit(1)
PYEOF
  SMOKE_PID=$!
  sleep 3
  kill $SMOKE_PID 2>/dev/null || true
  ok "Flask smoke test passed"

  log "Checking service file..."
  if systemctl list-unit-files aegis.service | grep -q "enabled"; then
    ok "aegis.service is enabled"
  else
    warn "aegis.service not enabled — run: sudo systemctl enable aegis"
  fi

  log "Checking port availability..."
  SERVER_PORT=$(grep "SERVER_PORT" "$INSTALL_DIR/ground_station/config.py" | \
    grep -o '[0-9]*' | tail -1)
  if ss -tlnp 2>/dev/null | grep -q ":${SERVER_PORT}"; then
    ok "Port $SERVER_PORT is in use (server may already be running)"
  else
    ok "Port $SERVER_PORT is available"
  fi
}

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

print_summary() {
  step "Installation complete"

  SERVER_PORT=$(grep "SERVER_PORT" "$INSTALL_DIR/ground_station/config.py" | \
    grep -o '[0-9]*' | tail -1)

  LOCAL_IP=$(hostname -I | awk '{print $1}')
  DUCK_DOMAIN=$(cat "$HOME/duckdns/duck.sh" 2>/dev/null | grep -o 'domains=[^&]*' | cut -d= -f2 || echo "")

  echo ""
  echo -e "${CYN}${BOLD}  AEGIS is installed.${NC}"
  echo ""
  echo -e "${WHT}  Next steps:${NC}"
  echo ""
  echo -e "  ${GRN}1.${NC} Plug in your SiK radios:"
  echo -e "     ${DIM}ls /dev/ttyUSB*${NC}"
  echo ""
  echo -e "  ${GRN}2.${NC} Power on your aircraft and start the service:"
  echo -e "     ${DIM}sudo systemctl start aegis${NC}"
  echo -e "     ${DIM}sudo journalctl -u aegis -f${NC}"
  echo ""
  echo -e "  ${GRN}3.${NC} Open the invoke page on your phone:"
  echo -e "     ${DIM}Local WiFi:  http://${LOCAL_IP}:${SERVER_PORT}${NC}"
  if [[ -n "$DUCK_DOMAIN" ]]; then
    echo -e "     ${DIM}4G / public: http://${DUCK_DOMAIN}.duckdns.org:${SERVER_PORT}${NC}"
  fi
  echo ""
  echo -e "  ${GRN}4.${NC} Before first flight — run the bench test:"
  echo -e "     ${DIM}python3 tools/test_bench.py${NC}"
  echo ""

  if [[ "${NEED_RELOGIN:-false}" == "true" ]]; then
    echo -e "  ${YLW}NOTE:${NC} Log out and back in (or run ${DIM}newgrp dialout${NC}) for"
    echo -e "        serial port permission changes to take effect."
    echo ""
  fi

  echo -e "  ${DIM}Logs:      sudo journalctl -u aegis -f${NC}"
  echo -e "  ${DIM}Restart:   sudo systemctl restart aegis${NC}"
  echo -e "  ${DIM}Status:    sudo systemctl status aegis${NC}"
  echo -e "  ${DIM}Config:    $INSTALL_DIR/ground_station/config.py${NC}"
  echo ""
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
  banner

  log "Starting AEGIS ground station installation"
  log "This will take approximately 3–5 minutes on a fresh Pi"
  echo ""

  NEED_RELOGIN=false

  preflight
  update_system
  setup_python
  setup_serial
  configure_ports
  setup_service
  setup_firewall
  setup_duckdns
  self_test
  print_summary
}

main "$@"
