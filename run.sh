#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5174}"
BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"
FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}"

backend_pid=""
frontend_pid=""

cleanup() {
  trap - EXIT INT TERM
  for pid in "$frontend_pid" "$backend_pid"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  for pid in "$frontend_pid" "$backend_pid"; do
    if [[ -n "$pid" ]]; then
      wait "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT INT TERM

if [[ ! -x "$ROOT_DIR/backend/.venv/bin/uvicorn" ]] && ! command -v uv >/dev/null 2>&1; then
  echo "Error: backend environment not found. Install uv and run 'cd backend && uv sync --all-extras'." >&2
  exit 1
fi
if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  echo "Error: frontend dependencies not found. Run 'cd frontend && npm ci'." >&2
  exit 1
fi

(
  cd "$ROOT_DIR/backend"
  if command -v uv >/dev/null 2>&1; then
    exec uv run uvicorn invoice_assistant.api.main:app --app-dir src --host 127.0.0.1 --port "$BACKEND_PORT"
  fi
  exec .venv/bin/uvicorn invoice_assistant.api.main:app --app-dir src --host 127.0.0.1 --port "$BACKEND_PORT"
) &
backend_pid=$!

(
  cd "$ROOT_DIR/frontend"
  exec env VITE_API_PROXY_TARGET="$BACKEND_URL" npx vite --host 127.0.0.1 --port "$FRONTEND_PORT" --strictPort
) &
frontend_pid=$!

ready=false
for _ in {1..60}; do
  if ! kill -0 "$frontend_pid" 2>/dev/null; then
    echo "Error: frontend server exited before becoming ready." >&2
    exit 1
  fi
  if curl --silent --fail "$FRONTEND_URL/" >/dev/null; then
    ready=true
    break
  fi
  sleep 1
done

if [[ "$ready" != true ]]; then
  echo "Error: frontend did not become ready at $FRONTEND_URL within 60 seconds." >&2
  exit 1
fi

echo "Frontend ready at $FRONTEND_URL"
if command -v google-chrome >/dev/null 2>&1; then
  google-chrome "$FRONTEND_URL" >/dev/null 2>&1 &
elif command -v google-chrome-stable >/dev/null 2>&1; then
  google-chrome-stable "$FRONTEND_URL" >/dev/null 2>&1 &
elif command -v chromium >/dev/null 2>&1; then
  chromium "$FRONTEND_URL" >/dev/null 2>&1 &
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$FRONTEND_URL" >/dev/null 2>&1 &
else
  echo "Warning: Google Chrome was not found; open $FRONTEND_URL manually." >&2
fi

wait -n "$backend_pid" "$frontend_pid"
