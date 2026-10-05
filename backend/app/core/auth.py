from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import user_id_from_token
from app.models.entities import User

def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Authentication required")
    user = db.get(User, user_id_from_token(authorization.split(" ",1)[1]))
    if not user:
        raise HTTPException(401, "User not found")
    return user
