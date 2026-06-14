"""
Shared JWT utilities for MediConnect services.
Uses HS256 with a common secret so tokens issued by booking-service
are accepted by patient-service.
"""
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import bcrypt
from jose import JWTError, jwt

SECRET_KEY = "mediConnect-dev-secret-change-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60


class Role(str, Enum):
    PATIENT = "patient"
    CLINICIAN = "clinician"
    ADMIN = "admin"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(username: str, role: Role, patient_id: Optional[str] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": username,
        "role": role.value,
        "patient_id": patient_id,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def validate_token(token: str) -> Optional[dict]:
    try:
        return decode_token(token)
    except JWTError:
        return None
