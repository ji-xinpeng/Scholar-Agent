#!/bin/bash

set -e

echo "Starting Scholar Agent..."

cd /app/backend
python server.py &
BACKEND_PID=$!

cd /app/frontend
npm start &
FRONTEND_PID=$!

service nginx start

echo "Services started successfully!"
echo "Frontend: http://localhost:80"
echo "Backend: http://localhost:8088"

wait $BACKEND_PID $FRONTEND_PID
