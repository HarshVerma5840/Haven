import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database.models import User, UsedExchangeToken, RoleEnum
from app.dependencies import get_db
from app.security.password import verify_password, get_password_hash
from app.security.jwt import create_access_token
from app.schemas.auth import Token, UserCreate, UserResponse, ExchangeTokenRequest
from app.config import get_settings

settings = get_settings()

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

@router.post("/exchange", response_model=Token)
def exchange_token_for_session(request_data: ExchangeTokenRequest, db: Session = Depends(get_db)):
    secret = settings.sso_secret if settings.sso_secret else settings.jwt_secret

    try:
        payload = jwt.decode(
            request_data.exchange_token,
            secret,
            algorithms=["HS256"],
            audience="haven",
            issuer="hrms"
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Exchange token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed exchange token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_type = payload.get("type")
    if token_type != "sso_exchange":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: expected sso_exchange",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub") or payload.get("username")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing username",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing jti",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role_str = payload.get("role")
    if role_str not in ["HR_ADMIN", "MANAGER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unauthorized role: '{role_str}' is not an approved HR role",
        )
    role_enum = RoleEnum[role_str]

    # Anti-replay check
    existing_used = db.query(UsedExchangeToken).filter(UsedExchangeToken.jti == jti).first()
    if existing_used:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Exchange token has already been used",
            headers={"WWW-Authenticate": "Bearer"},
        )

    exp_timestamp = payload.get("exp")
    if exp_timestamp:
        expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc).replace(tzinfo=None)
    else:
        expires_at = datetime.utcnow() + timedelta(minutes=5)

    used_record = UsedExchangeToken(
        jti=jti,
        username=username,
        expires_at=expires_at
    )
    db.add(used_record)

    # Locate or auto-provision user in Haven
    user = db.query(User).filter(User.username == username).first()
    if not user:
        random_pwd = secrets.token_urlsafe(32)
        user = User(
            username=username,
            password_hash=get_password_hash(random_pwd),
            role=role_enum,
            is_active=True
        )
        db.add(user)
    else:
        if not user.is_active:
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user account"
            )
        if user.role != role_enum:
            user.role = role_enum

    db.commit()
    db.refresh(user)

    access_token = create_access_token(data={"username": user.username, "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer"}
