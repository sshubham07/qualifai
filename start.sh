#!/usr/bin/env bash
# Start the whole local stack: infra (Docker), database migrations, API, worker and web app.
# Ctrl+C stops the API, worker and web app; the Docker services keep running (`make down` stops them).
set -euo pipefail
cd "$(dirname "$0")"

API_PORT=8000
WEB_PORT=3000

say() { printf '\033[36m▸ %s\033[0m\n' "$*"; }
die() { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

for tool in docker uv npm; do
  command -v "$tool" >/dev/null || die "'$tool' is not installed or not on PATH"
done
docker info >/dev/null 2>&1 || die "Docker is not running — start Docker Desktop and try again"
for port in $API_PORT $WEB_PORT; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    die "Port $port is already in use — stop whatever is listening there first"
  fi
done

if [ ! -f .env ]; then
  cp .env.example .env
  say "Created .env from .env.example — add QUALIFAI_GROQ_API_KEY there for real model calls"
fi

say "Starting Postgres, Redis, MinIO and Mailpit"
docker compose up -d --wait postgres redis minio mailpit

[ -d .venv ] || { say "Installing Python dependencies"; uv sync --all-extras; }
[ -d frontend/node_modules ] || { say "Installing web dependencies"; (cd frontend && npm install); }

# PYTHONPATH=src: don't depend on the editable-install path file (macOS can hide it from Python).
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"

say "Applying database migrations"
.venv/bin/alembic upgrade head

pids=()
run() { # run <label> <colour> <dir> <command...> — prefix each output line with the label
  local label=$1 colour=$2 dir=$3
  shift 3
  (cd "$dir" && exec "$@") > >(awk -v p="$(printf '\033[%sm%-7s\033[0m ' "$colour" "$label")" '{ print p $0; fflush() }') 2>&1 &
  pids+=($!)
}

stop() {
  trap - INT TERM EXIT
  printf '\n'
  say "Stopping API, worker and web app (Docker services stay up; 'make down' stops them)"
  kill "${pids[@]}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap stop EXIT
trap 'stop; exit 0' INT TERM

say "Starting API, worker and web app"
run api 34 . .venv/bin/uvicorn qualifai.api.main:app --reload --reload-dir src --port "$API_PORT"
run worker 35 . .venv/bin/arq qualifai.workers.worker.WorkerSettings
run web 32 frontend node_modules/.bin/vite --port "$WEB_PORT"

cat <<EOF

  Web app   http://localhost:$WEB_PORT
  API docs  http://localhost:$API_PORT/docs
  Emails    http://localhost:8025

  Ctrl+C to stop.

EOF

# Exit (and stop the rest) as soon as any one of the three processes dies.
while true; do
  for pid in "${pids[@]}"; do
    kill -0 "$pid" 2>/dev/null || die "A process exited — see the output above"
  done
  sleep 1
done
