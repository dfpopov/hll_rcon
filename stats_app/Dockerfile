# Stage 1: build React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package.json
RUN cd frontend && npm install --no-audit --no-fund
COPY frontend/. frontend/.
RUN cd frontend && npm run build

# Stage 2: runtime with nginx + uvicorn via supervisord
FROM python:3.12-slim AS runtime
WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# backend deps
COPY backend/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

# backend code
COPY backend/ /code/

# frontend dist → nginx web root
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html

# nginx + supervisord configs
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisord.conf

# nginx wants its own user; ensure /var/log/nginx exists
RUN mkdir -p /var/log/nginx /var/run/nginx

EXPOSE 80
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
