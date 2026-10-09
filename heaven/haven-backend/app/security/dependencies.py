from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database.models import User, RoleEnum
from app.dependencies import get_db
from app.security.jwt import decode_access_token
from jose import JWTError, ExpiredSignatureError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str = payload.get("username")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
        
    return user

def require_authenticated_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user

def require_hr_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != RoleEnum.HR_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires HR_ADMIN role"
        )
    return current_user

def require_manager_or_hr_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [RoleEnum.MANAGER, RoleEnum.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires MANAGER or HR_ADMIN role"
        )
    return current_user

def require_employee_or_above(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [RoleEnum.EMPLOYEE, RoleEnum.MANAGER, RoleEnum.HR_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires EMPLOYEE or above role"
        )
    return current_user
