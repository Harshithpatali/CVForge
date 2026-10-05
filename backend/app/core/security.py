from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.core.config import settings

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must be 72 bytes or fewer.")
    return pwd.hash(value)


def verify_password(value: str, hashed: str) -> bool:
    if len(value.encode("utf-8")) > 72:
        return False
    return pwd.verify(value, hashed)


def create_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.jwt_secret, algorithm="HS256")


def user_id_from_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
