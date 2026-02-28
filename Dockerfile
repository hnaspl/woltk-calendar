FROM python:3.11-slim AS base

# Install system deps for MySQL client + Node.js
RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    gcc \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# ---------- Backend ----------
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# ---------- Frontend ----------
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .

# ---------- Startup script ----------
WORKDIR /app
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 5000 5173

CMD ["/app/docker-entrypoint.sh"]
