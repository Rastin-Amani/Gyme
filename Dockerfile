# syntax=docker/dockerfile:1
# Single production container: SvelteKit SSR (public :3000) + FastAPI
# (loopback-only :8000). Built directly by Dokploy's Git/Docker deployment;
# no Compose file involved.

############################
# Stage 1: build the SvelteKit frontend
############################
FROM node:22-bookworm-slim AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build && npm prune --omit=dev

############################
# Stage 2: runtime (Node + Python 3.11)
############################
FROM node:22-bookworm-slim

# Debian bookworm ships Python 3.11, matching app/requirements.txt.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Python deps live in a venv so the system interpreter stays untouched.
ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH
COPY app/requirements.txt /tmp/requirements.txt
RUN python3 -m venv "$VIRTUAL_ENV" \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

ENV ENV=production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BACKEND_URL=http://127.0.0.1:8000 \
    HOST=0.0.0.0 \
    PORT=3000 \
    PROTOCOL_HEADER=x-forwarded-proto \
    HOST_HEADER=x-forwarded-host \
    ADDRESS_HEADER=x-forwarded-for

# FastAPI runs from /code (static + CSV datasets are path-relative).
WORKDIR /code
COPY app ./app
COPY data ./data

# adapter-node output; the Node process runs from /app, as before.
COPY --from=frontend /app/package.json /app/package.json
COPY --from=frontend /app/node_modules /app/node_modules
COPY --from=frontend /app/build /app/build

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh

USER node

# Only the SvelteKit server is public; uvicorn binds 127.0.0.1 inside the
# container, so port 8000 is unreachable from outside even if it were mapped.
EXPOSE 3000

# Probes both processes: a static-asset request for Node (no backend/tenant/PB
# involved) and FastAPI's PB-independent liveness endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python3 -c "import urllib.request as r; [r.urlopen(u, timeout=4) for u in ('http://127.0.0.1:3000/service-worker.js', 'http://127.0.0.1:8000/healthz')]"

ENTRYPOINT ["docker-entrypoint.sh"]
