#!/usr/bin/env bash
# One command to build and start the Moon Exchange HRMS demo on a laptop.
#   ./start.sh          build (first time) + start + wait until ready
#   ./start.sh logs     follow the setup / seeding logs
#   ./start.sh stop     stop everything (data is kept)
#   ./start.sh reset    stop and DELETE all data (fresh demo on next start)
set -euo pipefail
cd "$(dirname "$0")"
COMPOSE=(docker compose -p moon -f docker/docker-compose.yml)
PORT="${HTTP_PORT:-8080}"
if [ -f docker/.env ]; then COMPOSE+=(--env-file docker/.env); fi

case "${1:-up}" in
  logs)  exec "${COMPOSE[@]}" logs -f create-site ;;
  stop)  exec "${COMPOSE[@]}" down ;;
  reset) exec "${COMPOSE[@]}" down -v ;;
  up)
    command -v docker >/dev/null || { echo "Docker is required: https://docs.docker.com/get-docker/"; exit 1; }
    echo ">> Building the image and starting the stack (first run: about 10-20 minutes)..."
    "${COMPOSE[@]}" up -d --build
    echo ">> Waiting for the site to answer on http://localhost:${PORT} ..."
    until curl -sf -o /dev/null "http://localhost:${PORT}/api/method/ping"; do sleep 5; printf "."; done
    cat <<MSG

  Moon Exchange HRMS is ready:  http://localhost:${PORT}

  Administrator ............ Administrator / admin
  HR Manager ............... swati@demo.moon.exchange / MoonDemo@2026
  Engineering Manager ...... arjun@demo.moon.exchange / MoonDemo@2026
  Employee (mobile app) .... kavya@demo.moon.exchange / MoonDemo@2026   -> http://localhost:${PORT}/hrms
  CRM user ................. aisha@demo.moon.exchange / MoonDemo@2026

  Public pages: http://localhost:${PORT}/about   http://localhost:${PORT}/jobs
MSG
    ;;
  *) echo "usage: $0 [up|logs|stop|reset]"; exit 1 ;;
esac
