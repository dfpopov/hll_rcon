# Build context is the REPO ROOT (see compose.yaml `build.context: .`) so we
# can pull in rcongui_public alongside stats_app/frontend. Paths below are
# relative to the repo root.

# ----------------------------------------------------------------------------
# Stage 1: build stats_app's own React frontend (the all-time stats UI).
# ----------------------------------------------------------------------------
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY stats_app/frontend/package.json frontend/package.json
RUN cd frontend && npm install --no-audit --no-fund
COPY stats_app/frontend/. frontend/.
RUN cd frontend && npm run build

# ----------------------------------------------------------------------------
# Stage 2: build rcongui_public a SECOND time with base=/live/ so we can
# mount it under stats_app's nginx at /live/. The original 7010 build is
# unaffected — its container still builds with base=/ via Dockerfile-frontend.
# Asset paths, React Router basename, and the API client all read from the
# build-time env vars below. Mirrors Dockerfile-frontend's publicbuild stage
# (npm ci + assets copy) but on alpine and with the /live/ env overrides.
# ----------------------------------------------------------------------------
FROM node:20-bookworm-slim AS rcongui-build
WORKDIR /code_public
COPY rcongui_public/ .
RUN npm ci
# Shared assets that rcongui_public's vite build expects in /public.
COPY assets/images/ /code_public/public
COPY assets/rcongui_public/ /code_public/public
# Build-time overrides for the embedded variant:
ENV VITE_BASE_URL=/live/
# API client uses VITE_CRCON_API_URL when not in dev mode (see src/lib/api.ts).
# We proxy /live/api/* → backend:8000/api/* in stats_app/nginx.conf.
ENV VITE_CRCON_API_URL=/live/api
# External nav link back to the host stats_app root.
ENV VITE_STATS_APP_URL=/
RUN npm run build

# ----------------------------------------------------------------------------
# Stage 3: runtime with nginx + uvicorn (FastAPI) via supervisord.
# ----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime
WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# backend deps
COPY stats_app/backend/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

# backend code
COPY stats_app/backend/ /code/

# Mount stats_app frontend at root and rcongui_public at /live/.
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html
COPY --from=rcongui-build /code_public/dist /usr/share/nginx/html/live

# nginx + supervisord configs
COPY stats_app/nginx.conf /etc/nginx/nginx.conf
COPY stats_app/supervisord.conf /etc/supervisord.conf

# nginx wants its own user; ensure /var/log/nginx exists
RUN mkdir -p /var/log/nginx /var/run/nginx

EXPOSE 80
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
