from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.auth_service import get_current_user, get_current_active_user

# get current user dependency
def get_current_user_dependency(db: Session = Depends(get_db)):
    """
    dependency: get current user
    """
    return Depends(get_current_user)

# get current active user dependency
def get_current_active_user_dependency():
    """
    dependency: get current active user
    """
    return Depends(get_current_active_user) 