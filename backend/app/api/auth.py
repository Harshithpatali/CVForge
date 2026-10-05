from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import hash_password, verify_password, create_token
from app.core.auth import current_user
from app.models.entities import User

router=APIRouter(prefix="/api/v1/auth",tags=["auth"])
class AuthIn(BaseModel): email: EmailStr; password:str; name:str=""
class LoginIn(BaseModel): email: EmailStr; password:str
@router.post("/register")
def register(x:AuthIn,db:Session=Depends(get_db)):
    if len(x.password)<8: raise HTTPException(400,"Password must be at least 8 characters")
    if db.query(User).filter(User.email==x.email.lower()).first(): raise HTTPException(409,"Email already registered")
    u=User(email=x.email.lower(),password_hash=hash_password(x.password),name=x.name); db.add(u); db.commit(); db.refresh(u)
    return {"token":create_token(u.id),"user":{"id":u.id,"email":u.email,"name":u.name}}
@router.post("/login")
def login(x:LoginIn,db:Session=Depends(get_db)):
    u=db.query(User).filter(User.email==x.email.lower()).first()
    if not u or not verify_password(x.password,u.password_hash): raise HTTPException(401,"Invalid email or password")
    return {"token":create_token(u.id),"user":{"id":u.id,"email":u.email,"name":u.name}}
@router.get("/me")
def me(u:User=Depends(current_user)): return {"id":u.id,"email":u.email,"name":u.name}
