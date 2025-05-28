from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any, Dict

from app.api.schemas.users import UserCreate, UserResponse, Token, ForgotPassword, ResetPassword
from app.services.auth_service import (
    authenticate_user, create_access_token, get_password_hash, create_user,
    create_reset_password_token, reset_password_with_token
)
from app.db.database import get_db

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    register new user
    """
    from app.db.models import User
    db_user = db.query(User).filter(User.email == user_data.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email already exists"
        )
    
    # create new user
    user = create_user(db, user_data)
    return user

@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    get access token
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(user_data: ForgotPassword, db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Send a password reset token to the user
    """
    token = create_reset_password_token(db, user_data.email)
    if not token:
        # Return success even if user doesn't exist
        # This prevents user enumeration attacks
        return {"message": "If the email exists, a password reset link has been sent"}
    
    # In a real environment, an email with the reset link should be sent here
    # Example: http://frontend-url/reset-password?token={token}
    # For simplicity, we're just returning a success message
    return {"message": "If the email exists, a password reset link has been sent"}

@router.post("/reset-password", status_code=status.HTTP_200_OK)
def reset_password(reset_data: ResetPassword, db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Reset user password using reset token
    """
    if len(reset_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    user = reset_password_with_token(db, reset_data.token, reset_data.new_password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    return {"message": "Password has been successfully reset"} 