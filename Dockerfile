FROM python:3.11-slim

# Install system deps for Node.js
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Node dependencies
COPY package*.json ./
RUN npm ci

# Copy all source
COPY . .

# Build frontend
RUN npm run build

ENV FLASK_APP=wsgi.py

# Create instance directory for SQLite database
RUN mkdir -p /app/instance

EXPOSE 5000

CMD ["sh", "-c", "flask create-db && flask seed && gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 --bind 0.0.0.0:5000 wsgi:app"]
