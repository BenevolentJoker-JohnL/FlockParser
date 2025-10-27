#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VE_DIR="${ROOT_DIR}/.venv"
PYTHON="${VE_DIR}/bin/python"
PIP="${VE_DIR}/bin/pip"

echo "INSTALL_SOLLOL: idempotent installer (no destructive changes)."

usage() {
  cat <<EOF
Usage: $0 [--mode docker|python|system]
Modes:
  docker  - Build and run docker-compose demo (default)
  python  - Create virtualenv and pip install requirements
  system  - Attempt system-level pip install (requires sudo)
EOF
  exit 1
}

MODE="${1:-docker}"

if [[ "$MODE" == "--help" || "$MODE" == "-h" ]]; then usage; fi

case "$MODE" in
  docker)
    if ! command -v docker >/dev/null 2>&1 || ! command -v docker-compose >/dev/null 2>&1; then
      echo "docker/docker-compose not found. Install docker and docker-compose first."
      exit 1
    fi
    echo "Bringing up docker-compose demo..."
    docker-compose pull || true
    docker-compose build --pull
    docker-compose up -d
    echo "Docker demo started. Use 'docker-compose ps' to check containers."
    ;;

  python)
    if [[ ! -d "$VE_DIR" ]]; then
      python3 -m venv "$VE_DIR"
    fi
    # shellcheck disable=SC1091
    source "${VE_DIR}/bin/activate"
    if [[ -f "requirements.txt" ]]; then
      "$PIP" install --upgrade pip
      "$PIP" install -r requirements.txt
      echo "Dependencies installed into ${VE_DIR}."
    else
      echo "requirements.txt not found. Exiting."
      exit 1
    fi
    echo "To run: source ${VE_DIR}/bin/activate && python flock_webui.py"
    ;;

  system)
    echo "Performing system-wide pip install (requires sudo privileges)."
    sudo python3 -m pip install --upgrade pip
    sudo python3 -m pip install -r requirements.txt
    echo "System install complete."
    ;;

  *)
    usage
    ;;
esac

echo "INSTALL_SOLLOL finished. Check README Quick Start for next steps."
