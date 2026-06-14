"""
MediConnect Patient Service — stores and serves Protected Health Information (PHI).
Independent deployable component; booking-service calls this over HTTP.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from shared.auth import Role, validate_token
from database import get_connection, init_db

app = FastAPI(title="MediConnect Patient Service", version="1.0.0")
security = HTTPBearer()


class PatientRecord(BaseModel):
    id: str
    full_name: str
    date_of_birth: str
    medicare_number: str
    conditions: str
    clinic_id: str


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = validate_token(credentials.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return payload


def require_roles(*allowed: Role):
    """RBAC: only listed roles may access the endpoint."""
    allowed_values = {r.value for r in allowed}

    def checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in allowed_values:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Role '{user.get('role')}' cannot access this PHI resource",
            )
        return user

    return checker


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "healthy", "service": "patient-service"}


@app.get("/patients/{patient_id}", response_model=PatientRecord)
def get_patient(
    patient_id: str,
    user: dict = Depends(require_roles(Role.CLINICIAN, Role.ADMIN)),
):
    """PHI endpoint — clinicians and admins only."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return dict(row)


@app.get("/patients/{patient_id}/summary")
def get_patient_summary(
    patient_id: str,
    user: dict = Depends(require_roles(Role.PATIENT, Role.CLINICIAN, Role.ADMIN)),
):
    """Limited view: patients see only their own record."""
    if user["role"] == Role.PATIENT.value and user.get("patient_id") != patient_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Patients may only view their own record")

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, full_name, clinic_id FROM patients WHERE id = ?",
            (patient_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return dict(row)
