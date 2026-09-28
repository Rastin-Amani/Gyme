#!/usr/bin/env bash
# Runs both services in one container and keeps the container honest:
# if either process exits, the other is stopped and this PID 1 exits too, so
# the orchestrator restarts the whole app instead of showing a healthy
# container with only one half running.
set -eu

# The SvelteKit BFF reaches uvicorn over loopback, so Starlette's
# TrustedHostMiddleware must accept host 127.0.0.1 alongside the public hosts.
if [ -n "${ALLOWED_HOSTS:-}" ]; then
  export ALLOWED_HOSTS="${ALLOWED_HOSTS},127.0.0.1"
fi

backend_pid=""
frontend_pid=""

shutdown() {
  if [ -n "$frontend_pid" ]; then kill "$frontend_pid" 2>/dev/null || true; fi
  if [ -n "$backend_pid" ]; then kill "$backend_pid" 2>/dev/null || true; fi
}
trap 'shutdown' TERM INT

# FastAPI: loopback only, trusted proxy headers only from the local BFF.
( cd /code && exec uvicorn app.main:app --host 127.0.0.1 --port 8000 \
    --proxy-headers --forwarded-allow-ips 127.0.0.1 ) &
backend_pid=$!

# SvelteKit SSR: the only public listener (:3000).
( cd /app && exec node build ) &
frontend_pid=$!

# Wait for the first service to exit, then take the other one down with it.
status=0
wait -n "$backend_pid" "$frontend_pid" || status=$?
shutdown
wait "$backend_pid" 2>/dev/null || true
wait "$frontend_pid" 2>/dev/null || true
# A service exiting at all is a failure (the app is only half-running), even if
# it exited 0 — exit nonzero so restart policies and status logs see it.
if [ "$status" -eq 0 ]; then status=1; fi
exit "$status"
