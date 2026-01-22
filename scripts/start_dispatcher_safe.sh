#!/usr/bin/env bash
# Safe dispatcher starter: prevents concurrent starts using flock and PID guard.
# Usage: ./scripts/start_dispatcher_safe.sh

LOCKFILE=/tmp/titan_dispatcher.lock
PIDFILE=brain/dispatcher.pid
LOGFILE=brain/logs/overlord.log
UVICORN_CMD=(python3 -m uvicorn brain.dispatcher:app --host 0.0.0.0 --port 8000 --workers 4)

# Acquire exclusive lock (non-blocking) on $LOCKFILE using file descriptor 200
exec 200>"$LOCKFILE"
flock -n 200 || { echo "Another start in progress or lock held; exiting."; exit 0; }

# Ensure log dir exists
mkdir -p "$(dirname "$LOGFILE")"
mkdir -p "$(dirname "$PIDFILE")"

# If uvicorn already running, exit
if pgrep -f "uvicorn brain.dispatcher:app" >/dev/null 2>&1; then
  echo "Dispatcher already running (pid: $(pgrep -f "uvicorn brain.dispatcher:app" | head -n1))."; exec 200>&-; exit 0
fi

# If PID file exists, check whether it's stale. If process is alive and looks like uvicorn, exit.
if [ -f "$PIDFILE" ]; then
  OLD_PID=$(cat "$PIDFILE" 2>/dev/null || echo "")
  if [ -n "$OLD_PID" ]; then
    if kill -0 "$OLD_PID" >/dev/null 2>&1; then
      # process exists; verify its command line contains our uvicorn invocation
      CMDLINE=$(ps -p "$OLD_PID" -o args= 2>/dev/null || true)
      if echo "$CMDLINE" | grep -q "uvicorn brain.dispatcher:app"; then
        echo "Dispatcher already running (pid: $OLD_PID)."; exec 200>&-; exit 0
      else
        echo "Stale PIDfile found (pid: $OLD_PID) but process is not uvicorn; removing PIDfile.";
        rm -f "$PIDFILE"
      fi
    else
      echo "Stale PIDfile found (pid: $OLD_PID) but process not running; removing PIDfile.";
      rm -f "$PIDFILE"
    fi
  else
    rm -f "$PIDFILE"
  fi
fi

# Start uvicorn in background, capture PID
nohup "${UVICORN_CMD[@]}" > "$LOGFILE" 2>&1 &
UVICORN_PID=$!

# Persist PID
echo "$UVICORN_PID" > "$PIDFILE"

# Release lock (closing fd 200)
exec 200>&-

echo "Started dispatcher (pid=$UVICORN_PID). Logs: $LOGFILE"

exit 0
