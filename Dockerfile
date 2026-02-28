FROM python:3.11-slim

# Install system deps for MySQL client + Node.js
RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    gcc \
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

EXPOSE 5000

CMD ["sh", "-c", "flask create-db && flask seed && flask run --host=0.0.0.0 --port=5000"]
