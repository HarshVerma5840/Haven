from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database.models import User
from app.dependencies import get_db
from app.security.password import verify_password, get_password_hash
from app.security.jwt import create_access_token
from app.schemas.auth import Token, UserCreate, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    
    access_token = create_access_token(data={"username": user.username, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    if user_in.role.value != "EMPLOYEE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is restricted to the EMPLOYEE role."
        )

    user = db.query(User).filter(User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    password_hash = get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username,
        password_hash=password_hash,
        role=user_in.role.value,
        employee_hash=user_in.employee_hash,
        department=user_in.department,
        is_active=user_in.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

from app.security.dependencies import require_hr_admin

@router.post("/users", response_model=UserResponse)
def create_admin_user(
    user_in: UserCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr_admin)
):
    user = db.query(User).filter(User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    password_hash = get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username,
        password_hash=password_hash,
        role=user_in.role.value,
        employee_hash=user_in.employee_hash,
        department=user_in.department,
        is_active=user_in.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
