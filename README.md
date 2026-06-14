# MediConnect — ICT513 Assessment 4 Prototype

Appointment booking subsystem for MediConnect Health Services. Two independent FastAPI microservices with JWT + RBAC security on PHI endpoints.

## Architecture

```
Client  -->  booking-service :8000  -->  patient-service :8001
                    |                           |
              bookings.db                  patients.db
```

| Component | Port | Responsibility |
|-----------|------|----------------|
| booking-service | 8000 | Login, slot listing, appointment booking |
| patient-service | 8001 | PHI storage with role-based access control |

## Quick Start

### 1. Install dependencies

```powershell
cd mediConnect
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Start services

**Windows:**
```powershell
.\start_services.ps1
```

**Manual (two terminals):**
```powershell
# Terminal 1
cd patient-service
python -m uvicorn main:app --host 127.0.0.1 --port 8001

# Terminal 2
cd booking-service
$env:PATIENT_SERVICE_URL="http://127.0.0.1:8001"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs

### 3. Test login

```powershell
curl -X POST http://127.0.0.1:8000/auth/login `
  -H "Content-Type: application/json" `
  -d '{"username":"dr.smith","password":"clinician1"}'
```

### 4. Run security tests

```powershell
pytest tests/test_security.py -v -s
```

### 5. Run load test (generates charts)

```powershell
python load-tests/run_load_test.py
```

Charts saved to `load-tests/results/`.

## Demo Accounts

| Username | Password | Role |
|----------|----------|------|
| dr.smith | clinician1 | clinician |
| admin | admin1 | admin |
| alice.p | patient1 | patient (linked to P001) |

## Docker 

```powershell
docker compose up --build
```


## Project Structure

```
mediConnect/
├── booking-service/     # Booking API
├── patient-service/     # PHI API with RBAC
├── shared/auth.py       # JWT utilities
├── load-tests/          # Scalability experiment
├── tests/               # Security demonstration
├── REPORT.md            # Main submission report
└── requirements.txt
```
