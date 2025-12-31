import os
import traceback  # Added for error logging
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.models import User  # Direct import from models (avoids crud cycle)
from app.database import get_db  # For session

# Load .env
from dotenv import load_dotenv
load_dotenv()

# JWT Settings
SECRET_KEY = os.getenv("SECRET_KEY", "uPwNWjBbMEhQ1NICKAdzgVxaFaij--9d1gdEPOwt4WU")  # Secure default (43 chars)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours for 2025 clock compatibility

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Fernet for PII (secure default)
FERNET_KEY = os.getenv("FERNET_KEY", "PVTWj3uGfiocR_xZRb1DsW2msUhO2_1RlPYph-FHuuI=")
cipher_suite = Fernet(FERNET_KEY.encode())

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Password utils
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# JWT utils
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# User helpers (direct DB query to avoid crud import)
def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    try:
        print(f"Auth attempt for username: {username}")  # Debug log
        user = get_user(db, username)
        print(f"User  query result: {'Found' if user else 'Not found'}")  # Debug
        if not user:
            print("Auth failed: User not found")
            return False
        if not verify_password(password, user.hashed_password):
            print("Auth failed: Password mismatch")
            return False
        print(f"Auth success for: {user.username}")
        return user
    except Exception as e:
        print(f"AUTH ERROR (full traceback): {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Authentication service error: {str(e)}")

# Token verification
def verify_token(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user  # Return user object for role checks

# Encryption utils (for crud)
def encrypt_data(data: str) -> bytes:
    return cipher_suite.encrypt(data.encode('utf-8'))

def decrypt_data(encrypted_data: bytes) -> bytes:
    return cipher_suite.decrypt(encrypted_data)