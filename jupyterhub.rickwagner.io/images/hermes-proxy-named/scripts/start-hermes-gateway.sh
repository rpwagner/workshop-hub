#!/usr/bin/env bash
set -euo pipefail

export HERMES_HOME="${HERMES_HOME:-/home/jovyan/work/.hermes}"
export HERMES_API_KEY=$(grep API_SERVER_KEY /home/jovyan/work/.hermes/.env | sed 's/API_SERVER_KEY=//')
export API_SERVER_PORT=${grep API_SERVER_PORT /home/jovyan/work/.hermes/.env | sed 's/API_SERVER_PORT=//'}

if curl -fsS "http://127.0.0.1:${API_SERVER_PORT}/health" >/dev/null 2>&1; then
    echo "Hermes gateway is already running on 127.0.0.1:${API_SERVER_PORT}"
    exit 0
fi

echo "Starting Hermes gateway on 127.0.0.1:${API_SERVER_PORT}"
nohup hermes gateway > "${HERMES_HOME}/logs/gateway.log" 2>&1 &
echo $! > "${HERMES_HOME}/gateway.pid"
