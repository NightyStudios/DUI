#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

MODE="studio"
BOOTSTRAP="${BOOTSTRAP:-0}"
DUI_LLM_LOG_INPUT="${DUI_LLM_LOG_INPUT:-0}"
RELOAD="${RELOAD:-1}"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
VITE_API_BASE="${VITE_API_BASE:-http://$BACKEND_HOST:$BACKEND_PORT}"

backend_pid=""
frontend_pid=""

usage() {
  cat <<'EOF'
Usage: ./run.sh [studio|api] [options]

Modes:
  studio              Start backend + frontend. Default mode.
  api                 Start backend only.

Options:
  --bootstrap         Install backend/frontend dependencies when missing.
  --llm-debug-input   Print full LLM request payloads in backend logs.
  --no-reload         Start backend without uvicorn autoreload.
  -h, --help          Show this help.

Examples:
  ./run.sh --bootstrap
  ./run.sh studio --bootstrap
  ./run.sh api
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

ensure_backend() {
  if [[ -x "$BACKEND_DIR/.venv/bin/uvicorn" ]]; then
    return
  fi
  if [[ "$BOOTSTRAP" == "1" ]]; then
    bootstrap_backend
  else
    echo "Backend venv not found: $BACKEND_DIR/.venv/bin/uvicorn"
    echo "Run:"
    echo "  cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    echo "Or run: ./run.sh --bootstrap"
    exit 1
  fi
}

ensure_frontend() {
  if [[ -d "$FRONTEND_DIR/node_modules" ]]; then
    return
  fi
  if [[ "$BOOTSTRAP" == "1" ]]; then
    bootstrap_frontend
  else
    echo "Frontend dependencies are not installed: $FRONTEND_DIR/node_modules"
    echo "Run:"
    echo "  cd frontend && npm install"
    echo "Or run: ./run.sh --bootstrap"
    exit 1
  fi
}

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

wait_for_children() {
  local exit_code=0
  while true; do
    if [[ -n "$backend_pid" ]] && ! kill -0 "$backend_pid" 2>/dev/null; then
      wait "$backend_pid" || exit_code=$?
      break
    fi
    if [[ -n "$frontend_pid" ]] && ! kill -0 "$frontend_pid" 2>/dev/null; then
      wait "$frontend_pid" || exit_code=$?
      break
    fi
    sleep 1
  done
  return "$exit_code"
}

if [[ $# -gt 0 ]]; then
  case "$1" in
    studio|api)
      MODE="$1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      ;;
    *)
      echo "Unknown mode: $1"
      usage
      exit 1
      ;;
  esac
fi

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
    --no-reload)
      RELOAD=0
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

ensure_backend
if [[ "$MODE" == "studio" ]]; then
  ensure_frontend
fi

trap cleanup INT TERM EXIT

backend_args=(
  app.main:app
  --host "$BACKEND_HOST"
  --port "$BACKEND_PORT"
)
if [[ "$RELOAD" == "1" ]]; then
  backend_args+=(--reload)
fi

(
  cd "$BACKEND_DIR"
  source .venv/bin/activate
  DUI_LLM_LOG_INPUT="$DUI_LLM_LOG_INPUT" exec uvicorn "${backend_args[@]}"
) &
backend_pid=$!

if [[ "$MODE" == "studio" ]]; then
  (
    cd "$FRONTEND_DIR"
    VITE_API_BASE="$VITE_API_BASE" exec npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
  ) &
  frontend_pid=$!
fi

echo "Mode:     $MODE"
echo "Backend:  http://$BACKEND_HOST:$BACKEND_PORT"
if [[ "$MODE" == "studio" ]]; then
  echo "Frontend: http://localhost:$FRONTEND_PORT"
fi
if [[ "$DUI_LLM_LOG_INPUT" == "1" ]]; then
  echo "LLM input debug: enabled (DUI_LLM_LOG_INPUT=1)"
fi
echo "Press Ctrl+C to stop."

wait_for_children
