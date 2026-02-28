#!/bin/sh
set -e

echo "==> Starting WotLK Calendar (unified container)"

# --- Backend ---
cd /app/backend
echo "==> Initialising database..."
flask create-db
flask seed

echo "==> Starting Flask backend on :5000..."
flask run --host=0.0.0.0 --port=5000 &
BACKEND_PID=$!

# --- Frontend ---
cd /app/frontend
echo "==> Starting Vite dev server on :5173..."
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

echo "==> Both services running (backend=$BACKEND_PID, frontend=$FRONTEND_PID)"

# Wait for either to exit
wait -n $BACKEND_PID $FRONTEND_PID
EXIT_CODE=$?

# If one dies, kill the other
kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
exit $EXIT_CODE
