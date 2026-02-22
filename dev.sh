#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# Load project-level .env if present.
if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
DUI_LLM_LOG_INPUT="${DUI_LLM_LOG_INPUT:-0}"
BOOTSTRAP="${BOOTSTRAP:-0}"

usage() {
  cat <<'EOF'
Usage: ./dev.sh [options]

Options:
  --bootstrap         Install backend/frontend dependencies automatically when missing.
  --llm-debug-input   Print all LLM input payloads (system/user prompts) to backend console.
  -h, --help          Show this help.
EOF
}

bootstrap_backend() {
  local python_bin
  if command -v python3 >/dev/null 2>&1; then
    python_bin="python3"
  elif command -v python >/dev/null 2>&1; then
    python_bin="python"
  else
    echo "Python is required for backend bootstrap, but no python executable was found."
    exit 1
  fi

  echo "Bootstrapping backend dependencies..."
  (
    cd "$BACKEND_DIR"
    if [[ ! -d ".venv" ]]; then
      "$python_bin" -m venv .venv
    fi
    source .venv/bin/activate
    pip install -r requirements.txt
  )
}

bootstrap_frontend() {
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm is required for frontend bootstrap, but it was not found."
    exit 1
  fi

  echo "Bootstrapping frontend dependencies..."
  (
    cd "$FRONTEND_DIR"
    npm install
  )
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bootstrap)
      BOOTSTRAP=1
      shift
      ;;
    --llm-debug-input)
      DUI_LLM_LOG_INPUT=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ ! -x "$BACKEND_DIR/.venv/bin/uvicorn" ]]; then
  if [[ "$BOOTSTRAP" == "1" ]]; then
    bootstrap_backend
  else
    echo "Backend venv not found: $BACKEND_DIR/.venv/bin/uvicorn"
    echo "Run:"
    echo "  cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    echo "Or run: ./dev.sh --bootstrap"
    exit 1
  fi
fi

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  if [[ "$BOOTSTRAP" == "1" ]]; then
    bootstrap_frontend
  else
    echo "Frontend dependencies are not installed: $FRONTEND_DIR/node_modules"
    echo "Run:"
    echo "  cd frontend && npm install"
    echo "Or run: ./dev.sh --bootstrap"
    exit 1
  fi
fi

if [[ ! -x "$BACKEND_DIR/.venv/bin/uvicorn" ]]; then
  echo "Backend bootstrap did not produce $BACKEND_DIR/.venv/bin/uvicorn"
  exit 1
fi

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "Frontend bootstrap did not produce $FRONTEND_DIR/node_modules"
  exit 1
fi

backend_pid=""
frontend_pid=""

cleanup() {
  trap - INT TERM EXIT
  if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" 2>/dev/null; then
    kill "$backend_pid" 2>/dev/null || true
  fi
  if [[ -n "$frontend_pid" ]] && kill -0 "$frontend_pid" 2>/dev/null; then
    kill "$frontend_pid" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}

trap cleanup INT TERM EXIT

(
  cd "$BACKEND_DIR"
  source .venv/bin/activate
  DUI_LLM_LOG_INPUT="$DUI_LLM_LOG_INPUT" exec uvicorn app.main:app --reload --host "$BACKEND_HOST" --port "$BACKEND_PORT"
) &
backend_pid=$!

(
  cd "$FRONTEND_DIR"
  VITE_API_BASE="http://$BACKEND_HOST:$BACKEND_PORT" exec npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
) &
frontend_pid=$!

echo "Backend:  http://$BACKEND_HOST:$BACKEND_PORT"
echo "Frontend: http://localhost:$FRONTEND_PORT"
if [[ "$DUI_LLM_LOG_INPUT" == "1" ]]; then
  echo "LLM input debug: enabled (DUI_LLM_LOG_INPUT=1)"
fi
echo "Press Ctrl+C to stop both."

wait -n "$backend_pid" "$frontend_pid"
