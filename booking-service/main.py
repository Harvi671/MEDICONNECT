"""
MediConnect Booking Service — appointment booking and auth gateway.
Calls patient-service for PHI when a clinician views patient details.
"""
import os
import sys
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.auth import Role, create_access_token, validate_token, verify_password
from database import get_connection, init_db

PATIENT_SERVICE_URL = os.getenv("PATIENT_SERVICE_URL", "http://localhost:8001")

app = FastAPI(title="MediConnect Booking Service", version="1.0.0")
security = HTTPBearer()


class LoginRequest(BaseModel):
    username: str
    password: str


class BookRequest(BaseModel):
    patient_id: str
    clinic_id: str
    slot_time: str


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = validate_token(credentials.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return payload


def require_roles(*allowed: Role):
    allowed_values = {r.value for r in allowed}

    def checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in allowed_values:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return checker


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "healthy", "service": "booking-service"}


@app.post("/auth/login")
def login(body: LoginRequest):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (body.username,)
        ).fetchone()
    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    token = create_access_token(
        username=row["username"],
        role=Role(row["role"]),
        patient_id=row["patient_id"],
    )
    return {"access_token": token, "token_type": "bearer", "role": row["role"]}


@app.get("/slots/available")
def list_available_slots(clinic_id: str = None, user: dict = Depends(get_current_user)):
    """Primary load-test target — lists bookable appointment slots."""
    query = "SELECT clinic_id, slot_time FROM clinic_slots WHERE available = 1"
    params = []
    if clinic_id:
        query += " AND clinic_id = ?"
        params.append(clinic_id)
    query += " LIMIT 50"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return {"slots": [dict(r) for r in rows], "count": len(rows)}


@app.post("/appointments/book")
def book_appointment(
    body: BookRequest,
    user: dict = Depends(require_roles(Role.CLINICIAN, Role.ADMIN, Role.PATIENT)),
):
    if user["role"] == Role.PATIENT.value and user.get("patient_id") != body.patient_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Patients may only book for themselves")

    with get_connection() as conn:
        slot = conn.execute(
            """SELECT id FROM clinic_slots
               WHERE clinic_id = ? AND slot_time = ? AND available = 1""",
            (body.clinic_id, body.slot_time),
        ).fetchone()
        if not slot:
            raise HTTPException(status.HTTP_409_CONFLICT, "Slot no longer available")

        conn.execute(
            "UPDATE clinic_slots SET available = 0 WHERE id = ?",
            (slot["id"],),
        )
        cursor = conn.execute(
            """INSERT INTO appointments (patient_id, clinic_id, clinician, slot_time)
               VALUES (?, ?, ?, ?)""",
            (body.patient_id, body.clinic_id, user["sub"], body.slot_time),
        )
        conn.commit()
        booking_id = cursor.lastrowid

    return {"booking_id": booking_id, "status": "confirmed", "slot_time": body.slot_time}


@app.get("/appointments/{booking_id}/patient-details")
def get_patient_for_booking(
    booking_id: int,
    user: dict = Depends(require_roles(Role.CLINICIAN, Role.ADMIN)),
):
    """Cross-service call: booking-service fetches PHI from patient-service."""
    with get_connection() as conn:
        appt = conn.execute(
            "SELECT patient_id FROM appointments WHERE id = ?", (booking_id,)
        ).fetchone()
    if not appt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")

    token = create_access_token(user["sub"], Role(user["role"]))
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(
                f"{PATIENT_SERVICE_URL}/patients/{appt['patient_id']}",
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Patient service unavailable: {exc}")
