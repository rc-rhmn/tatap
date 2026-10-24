#!/bin/bash
# Tatap - service manager (lokal)
DIR="$(cd "$(dirname "$0")" && pwd)"
PIDF="$DIR/server.pid"

# Jalur log aman multi-user: gunakan XDG_STATE_HOME atau direktori privat lokal user
LOG_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/tatap"
if ! mkdir -p "$LOG_DIR" 2>/dev/null; then
  LOG_DIR="$DIR/cache"
  mkdir -p "$LOG_DIR" 2>/dev/null || LOG_DIR="/tmp/tatap-${UID:-$USER}"
  mkdir -p "$LOG_DIR" 2>/dev/null || true
fi
LOG="$LOG_DIR/tatap.log"

case "$1" in
  start)
    if [ -f "$PIDF" ]; then
      existing_pid=$(cat "$PIDF" 2>/dev/null || true)
      if [ -n "$existing_pid" ] && kill -0 "$existing_pid" 2>/dev/null; then
        cmd_args=$(ps -u "$UID" -p "$existing_pid" -o args= 2>/dev/null || ps -p "$existing_pid" -o args= 2>/dev/null || true)
        if echo "$cmd_args" | grep -Eq "python.*backend/main\.py|run\.sh"; then
          echo "sudah jalan ($existing_pid)"
          exit 0
        fi
      fi
    fi
    cd "$DIR" && setsid ./run.sh > "$LOG" 2>&1 < /dev/null & echo $! > "$PIDF"
    sleep 3; curl -s --max-time 8 http://127.0.0.1:8767/api/health | head -c 120; echo;;
  stop)
    if [ -f "$PIDF" ]; then
      pid=$(cat "$PIDF" 2>/dev/null || true)
      if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        cmd_args=$(ps -u "$UID" -p "$pid" -o args= 2>/dev/null || ps -p "$pid" -o args= 2>/dev/null || true)
        if echo "$cmd_args" | grep -Eq "python.*backend/main\.py|run\.sh"; then
          kill "$pid" 2>/dev/null || true
          pkill -u "$UID" -P "$pid" 2>/dev/null || true
        fi
      fi
      rm -f "$PIDF"
    fi
    pkill -u "$UID" -f "python.*backend/main\.py" 2>/dev/null || true
    echo stopped;;
  status)
    if [ -f "$PIDF" ]; then
      pid=$(cat "$PIDF" 2>/dev/null || true)
      if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        cmd_args=$(ps -u "$UID" -p "$pid" -o args= 2>/dev/null || ps -p "$pid" -o args= 2>/dev/null || true)
        if echo "$cmd_args" | grep -Eq "python.*backend/main\.py|run\.sh"; then
          echo "jalan ($pid)"
          exit 0
        fi
      fi
    fi
    user_pid=$(pgrep -u "$UID" -f "python.*backend/main\.py" 2>/dev/null | head -n1 || true)
    if [ -n "$user_pid" ]; then
      echo "jalan ($user_pid)"
    else
      echo berhenti
    fi;;
  logs)
    if [ -f "$LOG" ]; then
      tail -30 "$LOG"
    else
      echo "Berkas log belum ada ($LOG)"
    fi;;
  *) echo "pakai: $0 {start|stop|status|logs}";;
esac
