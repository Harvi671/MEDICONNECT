"""
Security demonstration: JWT + RBAC on PHI endpoints.
Run with: pytest tests/test_security.py -v -s
"""
import sys
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

BOOKING_URL = "http://127.0.0.1:8000"
PATIENT_URL = "http://127.0.0.1:8001"


def get_token(username: str, password: str) -> str:
    r = httpx.post(f"{BOOKING_URL}/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def clinician_token():
    return get_token("dr.smith", "clinician1")


@pytest.fixture(scope="module")
def patient_token():
    return get_token("alice.p", "patient1")


def test_clinician_can_access_phi(clinician_token):
    """Clinician role should read full PHI record."""
    r = httpx.get(
        f"{PATIENT_URL}/patients/P001",
        headers={"Authorization": f"Bearer {clinician_token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "medicare_number" in data
    print(f"\n[PASS] Clinician accessed PHI: {data['full_name']}, Medicare: {data['medicare_number']}")


def test_patient_denied_full_phi(patient_token):
    """Patient role must be blocked from full PHI endpoint."""
    r = httpx.get(
        f"{PATIENT_URL}/patients/P001",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert r.status_code == 403
    print(f"\n[PASS] Patient blocked from PHI: {r.json()['detail']}")


def test_patient_can_view_own_summary(patient_token):
    """Patient may view their own limited summary."""
    r = httpx.get(
        f"{PATIENT_URL}/patients/P001/summary",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert r.status_code == 200
    assert "medicare_number" not in r.json()
    print(f"\n[PASS] Patient summary (no Medicare): {r.json()}")


def test_unauthenticated_denied():
    """Requests without a token must return 401."""
    r = httpx.get(f"{PATIENT_URL}/patients/P001")
    assert r.status_code == 403  # HTTPBearer returns 403 when header missing
    print(f"\n[PASS] Unauthenticated request rejected")
