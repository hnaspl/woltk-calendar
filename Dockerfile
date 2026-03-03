# Stage 1: Build frontend with Node.js
FROM node:20-slim AS frontend-builder

WORKDIR /build

COPY package*.json ./
RUN npm ci

COPY index.html vite.config.js postcss.config.js ./
COPY src/ src/
COPY translations/ translations/

RUN npm run build

# Stage 2: Python runtime
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application source
COPY . .

# Copy built frontend from stage 1
COPY --from=frontend-builder /build/dist /app/dist

ENV FLASK_APP=wsgi.py

# Create instance directory for SQLite database
RUN mkdir -p /app/instance

EXPOSE 5000

CMD ["sh", "-c", "flask create-db && flask seed && gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 --bind 0.0.0.0:5000 --access-logfile - --log-level info wsgi:app"]
