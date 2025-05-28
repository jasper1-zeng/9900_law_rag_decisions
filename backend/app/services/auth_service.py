from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import secrets
import string

from app.config import settings
from app.db.models import User
from app.db.database import get_db
from app.api.schemas.users import UserCreate, TokenData

# encryption context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 password Bearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")

# password hash function
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# verify password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# create user
def create_user(db: Session, user_data: UserCreate) -> User:
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# get user
def get_user(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

# user authentication
def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

# create access token
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# get current user
async def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="can't verify credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = get_user(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

# get current active user
async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="user doesn't exist")
    return current_user

# generate reset password token
def generate_reset_password_token() -> str:
    """
    Generate a secure random password reset token
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(64))

# create reset password token for user
def create_reset_password_token(db: Session, email: str) -> Optional[str]:
    """
    Create a password reset token for a user and set expiration time
    """
    user = get_user(db, email)
    if not user:
        return None
    
    # Generate token
    token = generate_reset_password_token()
    # Set expiration time (24 hours)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    # Update user record
    user.reset_password_token = token
    user.reset_token_expires_at = expires_at
    
    db.commit()
    db.refresh(user)
    
    return token

# verify reset password token
def verify_reset_password_token(db: Session, token: str) -> Optional[User]:
    """
    Verify the validity of a password reset token
    """
    user = db.query(User).filter(User.reset_password_token == token).first()
    
    if not user:
        return None
    
    # Check if token is expired
    if not user.reset_token_expires_at or user.reset_token_expires_at < datetime.utcnow():
        return None
    
    return user

# reset password with token
def reset_password_with_token(db: Session, token: str, new_password: str) -> Optional[User]:
    """
    Reset user password using token
    """
    user = verify_reset_password_token(db, token)
    
    if not user:
        return None
    
    # Update password
    user.hashed_password = get_password_hash(new_password)
    
    # Clear reset token and expiration time
    user.reset_password_token = None
    user.reset_token_expires_at = None
    
    db.commit()
    db.refresh(user)
    
    return user 