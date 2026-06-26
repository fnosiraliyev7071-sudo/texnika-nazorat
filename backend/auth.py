"""
JWT Authentication
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import User, UserRole
import os

SECRET_KEY = os.getenv("SECRET_KEY", "texnika_nazorat_super_secret_key_2024")
ALGORITHM  = "HS256"
TOKEN_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security    = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(days=TOKEN_DAYS)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ── Dependency: joriy foydalanuvchini olish ──
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token noto'g'ri yoki muddati o'tgan")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token noto'g'ri")

    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Foydalanuvchi topilmadi")
    return user


# ── Role tekshiruvchi dependency ──
def require_roles(*roles: UserRole):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Ruxsat yo'q")
        return user
    return checker


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Faqat admin uchun")
    return user


def can_assign(user: User = Depends(get_current_user)) -> User:
    """Texnika biriktira olish tekshiruvi"""
    if user.role == UserRole.admin:
        return user
    if user.role == UserRole.mexanik and user.can_assign_equipment:
        return user
    if user.can_assign_equipment:
        return user
    raise HTTPException(status_code=403, detail="Texnika biriktirish uchun ruxsat yo'q")


# ── O'z resursini tekshirish ──
def check_own_resource(user: User, resource_user_id: int):
    """Master faqat o'z resursi bilan ishlaydi"""
    if user.role == UserRole.admin:
        return  # admin hamma narsani ko'radi
    if user.id != resource_user_id:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q — bu boshqa foydalanuvchi resursi")
