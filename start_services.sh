#!/bin/bash
# Start both MediConnect services (Linux/macOS)
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "Starting patient-service on port 8001..."
cd "$ROOT/patient-service"
python -m uvicorn main:app --host 127.0.0.1 --port 8001 &
PID1=$!

sleep 2

echo "Starting booking-service on port 8000..."
cd "$ROOT/booking-service"
PATIENT_SERVICE_URL=http://127.0.0.1:8001 python -m uvicorn main:app --host 127.0.0.1 --port 8000 &
PID2=$!

echo "Services started (PIDs: $PID1, $PID2)"
echo "Booking API: http://127.0.0.1:8000/docs"
wait
