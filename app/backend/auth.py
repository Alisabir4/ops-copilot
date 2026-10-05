from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.backend.config import settings
from app.backend.database import get_db
from app.backend.models import User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_password(password: str) -> str: return pwd.hash(password)
def verify_password(password: str, hashed: str) -> bool: return pwd.verify(password, hashed)

def token_for(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, settings.jwt_secret, algorithm="HS256")

def current_user(token: str = Depends(oauth), db: Session = Depends(get_db)) -> User:
    try:
        uid = int(jwt.decode(token, settings.jwt_secret, algorithms=["HS256"]).get("sub", ""))
    except (JWTError, ValueError):
        raise HTTPException(401, "Invalid or expired login token", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, uid)
    if not user or not user.active: raise HTTPException(401, "Account is unavailable")
    return user

def roles(*allowed: str):
    def check(user: User = Depends(current_user)) -> User:
        if user.role not in allowed: raise HTTPException(403, "Your role cannot perform this action")
        return user
    return check
