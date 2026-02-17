#!/usr/bin/env bash
set -euo pipefail

MODEL_NAME="${1:-qwen2.5:14b-instruct}"
INTERVAL_SEC="${2:-60}"
LOG_FILE="${3:-/tmp/ollama_watchdog.log}"
PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
OLLAMA_BIN="${OLLAMA_BIN:-$(command -v ollama || true)}"
OLLAMA_API_URL="${OLLAMA_API_URL:-http://127.0.0.1:11434/api/tags}"

if [[ -z "${OLLAMA_BIN}" ]]; then
  echo "ollama binary not found in PATH" >&2
  exit 1
fi

log() {
  printf '%s %s\n' "[$(date '+%Y-%m-%d %H:%M:%S')]" "$1" | tee -a "$LOG_FILE"
}

log "watchdog started for model: $MODEL_NAME"

while true; do
  tags_json="$(curl -sf "$OLLAMA_API_URL" || true)"
  if [[ -n "$tags_json" ]] && printf '%s' "$tags_json" | grep -Fq "\"name\":\"$MODEL_NAME\""; then
    log "model downloaded: $MODEL_NAME"

    if pgrep -f "^caffeinate( |$)" >/dev/null 2>&1; then
      pkill -f "^caffeinate( |$)" || true
      log "caffeinate process terminated"
    else
      log "no caffeinate process found"
    fi

    if pgrep -f "pipes\\.sh" >/dev/null 2>&1; then
      pkill -f "pipes\\.sh" || true
      log "pipes.sh process terminated"
    else
      log "no pipes.sh process found"
    fi

    log "watchdog finished"
    exit 0
  fi

  if pgrep -f "ollama pull $MODEL_NAME" >/dev/null 2>&1; then
    log "model not ready yet (pull in progress); next check in ${INTERVAL_SEC}s"
  else
    log "model not ready yet (pull process not found); waiting and re-checking in ${INTERVAL_SEC}s"
  fi
  sleep "$INTERVAL_SEC"
done
