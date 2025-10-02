#!/bin/bash

set -e -u
set -o pipefail

# Test if file exists, if so, source .env
if [[ -f "$PWD"/.env ]]; then
    source "$PWD"/.env
fi

ROOT="$PWD"

# Kill any existing processes on port 3000
echo "Checking for existing processes on port 3000..." >> logs/yarn_run.log
if lsof -ti :3000 > /dev/null 2>&1; then
    echo "Killing existing processes on port 3000..." >> logs/yarn_run.log
    kill $(lsof -ti :3000) 2>/dev/null || true
    sleep 2
fi

cd modal-login

yarn dev >> "$ROOT/logs/yarn.log" 2>&1